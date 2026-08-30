import logging
import operator
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decrypt_github_token
from app.db.session import SessionLocal
from app.models.github_connection import GitHubConnection
from app.models.enums import PoolItemSource
from app.services.embeddings import EmbeddingService
from app.services.github import GitHubAPIClient, extract_repository_pool_candidates
from app.services.item_extractor import ExtractedPoolItem, create_unverified_pool_items
from app.services.llm import LLMService
from app.services.llm_credentials import LLMCredentialMissing, load_llm_service
from app.services.pdf_parser import extract_pdf_text


class PoolGraphState(TypedDict, total=False):
    user_id: UUID
    db: Session
    llm_service: LLMService
    embedding_service: EmbeddingService
    include_github: bool
    pdf_bytes: bytes | None
    github_client_factory: Callable[[str], GitHubAPIClient]
    pdf_candidates: list[ExtractedPoolItem]
    github_candidates: list[ExtractedPoolItem]
    pending_item_ids: list[UUID]
    pending_count: int
    parallel_steps: Annotated[list[str], operator.add]


def _github_client_factory(token: str) -> GitHubAPIClient:
    return GitHubAPIClient(token=token)


async def pdf_parser_node(state: PoolGraphState) -> dict[str, object]:
    pdf_bytes = state.get("pdf_bytes")
    if not pdf_bytes:
        return {"pdf_candidates": [], "parallel_steps": ["pdf_parser"]}

    text = extract_pdf_text(pdf_bytes)
    from app.api.pdf_import import build_pdf_extraction_prompt, pool_type_for_pdf_item, tags_for_pdf_item
    from app.schemas.pdf_import import PDFExtraction

    extraction = await state["llm_service"].structured(
        build_pdf_extraction_prompt(text),
        PDFExtraction,
        system_prompt="You extract structured, factual CV pool items from PDF CV text.",
    )
    return {
        "pdf_candidates": [
            ExtractedPoolItem(
                source=PoolItemSource.PDF,
                type=pool_type_for_pdf_item(item),
                title=item.title,
                raw_content=item.raw_content,
                tags=tags_for_pdf_item(item),
                technologies=item.technologies,
            )
            for item in extraction.items
        ],
        "parallel_steps": ["pdf_parser"],
    }


async def github_analyzer_node(state: PoolGraphState) -> dict[str, object]:
    if not state["include_github"]:
        return {"github_candidates": [], "parallel_steps": ["github_analyzer"]}

    connection = state["db"].scalar(select(GitHubConnection).where(GitHubConnection.user_id == state["user_id"]))
    if connection is None:
        return {"github_candidates": [], "parallel_steps": ["github_analyzer"]}

    token = decrypt_github_token(connection.access_token_encrypted)
    github_client = state.get("github_client_factory", _github_client_factory)(token)
    candidates = await extract_repository_pool_candidates(github_client, state["llm_service"])
    return {"github_candidates": candidates, "parallel_steps": ["github_analyzer"]}


async def item_extractor_node(state: PoolGraphState) -> dict[str, object]:
    candidates = [*state.get("pdf_candidates", []), *state.get("github_candidates", [])]
    pool_items = create_unverified_pool_items(state["user_id"], candidates, state["embedding_service"])
    if pool_items:
        state["db"].add_all(pool_items)
        state["db"].flush()

    if state.get("github_candidates"):
        connection = state["db"].scalar(select(GitHubConnection).where(GitHubConnection.user_id == state["user_id"]))
        if connection is not None:
            connection.last_synced = datetime.now(UTC)

    state["db"].commit()
    for item in pool_items:
        state["db"].refresh(item)
    return {
        "pending_item_ids": [item.id for item in pool_items],
        "pending_count": len(pool_items),
    }


def build_pool_graph():
    graph = StateGraph(PoolGraphState)
    graph.add_node("pdf_parser", pdf_parser_node)
    graph.add_node("github_analyzer", github_analyzer_node)
    graph.add_node("item_extractor", item_extractor_node)
    graph.add_edge(START, "pdf_parser")
    graph.add_edge(START, "github_analyzer")
    graph.add_edge("pdf_parser", "item_extractor")
    graph.add_edge("github_analyzer", "item_extractor")
    graph.add_edge("item_extractor", END)
    return graph.compile()


logger = logging.getLogger(__name__)

pool_graph = build_pool_graph()


async def run_pool_graph_for_user(
    user_id: UUID,
    pdf_bytes: bytes | None = None,
    include_github: bool = True,
) -> dict[str, object]:
    with SessionLocal() as db:
        try:
            llm_service = load_llm_service(db, user_id)
        except LLMCredentialMissing:
            # Both callers schedule this as a background task, so raising here
            # would only ever reach the logs. Extraction needs the user's own
            # provider key; without one there is nothing to do.
            logger.info(
                "pool_graph_skipped_without_llm_key",
                extra={"event": "pool_graph_skipped_without_llm_key", "user_id": str(user_id)},
            )
            return {"user_id": user_id, "created_items": []}

        return await pool_graph.ainvoke(
            {
                "user_id": user_id,
                "db": db,
                "llm_service": llm_service,
                "embedding_service": EmbeddingService(),
                "include_github": include_github,
                "pdf_bytes": pdf_bytes,
            }
        )
