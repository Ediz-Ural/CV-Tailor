from dataclasses import dataclass
from uuid import UUID

import httpx
from sqlalchemy import select

from app.core.config import Settings, settings
from app.core.security import decrypt_github_token
from app.db.session import SessionLocal
from app.models.enums import PoolItemSource, PoolItemType
from app.models.github_connection import GitHubConnection
from app.models.pool_item import PoolItem
from app.schemas.github import GitHubRepoAnalysis
from app.services.embeddings import EmbeddingService
from app.services.item_extractor import ExtractedPoolItem, normalize_extracted_item
from app.services.llm import LLMService


class GitHubConfigurationError(RuntimeError):
    pass


class GitHubAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubRepositorySignal:
    name: str
    full_name: str
    html_url: str
    description: str | None
    fork: bool
    topics: list[str]
    languages: dict[str, int]
    commit_count: int
    readme: str


class GitHubAPIClient:
    def __init__(
        self,
        token: str | None = None,
        config: Settings = settings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.token = token
        self.config = config
        self._client = client

    async def exchange_code_for_token(self, code: str) -> str:
        if not self.config.github_oauth_client_id or not self.config.github_oauth_client_secret:
            raise GitHubConfigurationError("GitHub OAuth client is not configured")
        data = await self._request(
            "POST",
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": self.config.github_oauth_client_id,
                "client_secret": self.config.github_oauth_client_secret,
                "code": code,
                "redirect_uri": self.config.github_oauth_redirect_uri,
            },
            authenticated=False,
        )
        access_token = data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise GitHubAPIError("GitHub OAuth token response is invalid")
        return access_token

    async def get_authenticated_username(self) -> str:
        user = await self._request("GET", "https://api.github.com/user")
        login = user.get("login")
        if not isinstance(login, str) or not login:
            raise GitHubAPIError("GitHub user response is invalid")
        return login

    async def collect_repository_signals(self) -> list[GitHubRepositorySignal]:
        repos = await self._paginate(
            "https://api.github.com/user/repos",
            params={"per_page": "100", "affiliation": "owner", "sort": "updated"},
        )
        signals: list[GitHubRepositorySignal] = []
        for repo in repos:
            signal = await self._build_signal(repo)
            if signal is not None and is_eligible_repository(signal):
                signals.append(signal)
        return signals

    async def _build_signal(self, repo: dict) -> GitHubRepositorySignal | None:
        if bool(repo.get("fork")):
            return None
        owner = repo.get("owner", {}).get("login")
        name = repo.get("name")
        full_name = repo.get("full_name")
        if not all(isinstance(value, str) and value for value in [owner, name, full_name]):
            return None

        commit_count = await self._commit_count(owner, name)
        if commit_count <= 0:
            return None
        readme = await self._readme(owner, name)
        if readme is None:
            return None
        languages = await self._languages(owner, name)
        topics = repo.get("topics") if isinstance(repo.get("topics"), list) else []

        return GitHubRepositorySignal(
            name=name,
            full_name=full_name,
            html_url=str(repo.get("html_url") or ""),
            description=repo.get("description") if isinstance(repo.get("description"), str) else None,
            fork=False,
            topics=[str(topic) for topic in topics],
            languages={str(language): int(bytes_count) for language, bytes_count in languages.items()},
            commit_count=commit_count,
            readme=readme,
        )

    async def _commit_count(self, owner: str, repo: str) -> int:
        response = await self._raw_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/commits",
            params={"per_page": "1"},
        )
        if response.status_code == 409:
            return 0
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list) or not data:
            return 0
        link = response.headers.get("link", "")
        marker = 'rel="last"'
        if marker in link:
            for part in link.split(","):
                if marker in part:
                    url_part = part.split(";")[0].strip(" <>")
                    parsed = httpx.URL(url_part)
                    page = parsed.params.get("page")
                    if page and page.isdigit():
                        return int(page)
        return 1

    async def _readme(self, owner: str, repo: str) -> str | None:
        response = await self._raw_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/readme",
            headers={"Accept": "application/vnd.github.raw"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        text = response.text.strip()
        return text or None

    async def _languages(self, owner: str, repo: str) -> dict[str, int]:
        data = await self._request("GET", f"https://api.github.com/repos/{owner}/{repo}/languages")
        return data if isinstance(data, dict) else {}

    async def _paginate(self, url: str, *, params: dict[str, str]) -> list[dict]:
        results: list[dict] = []
        next_url: str | None = url
        next_params: dict[str, str] | None = params
        while next_url:
            response = await self._raw_request("GET", next_url, params=next_params)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise GitHubAPIError("GitHub paginated response is invalid")
            results.extend(item for item in data if isinstance(item, dict))
            next_url = response.links.get("next", {}).get("url")
            next_params = None
        return results

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        response = await self._raw_request(method, url, **kwargs)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise GitHubAPIError("GitHub response is invalid")
        return data

    async def _raw_request(
        self,
        method: str,
        url: str,
        *,
        authenticated: bool = True,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        request_headers = {"Accept": "application/vnd.github+json", **(headers or {})}
        if authenticated:
            if not self.token:
                raise GitHubConfigurationError("GitHub token is missing")
            request_headers["Authorization"] = f"Bearer {self.token}"

        client = self._client or httpx.AsyncClient(timeout=self.config.github_api_timeout_seconds)
        should_close = self._client is None
        try:
            return await client.request(method, url, headers=request_headers, **kwargs)
        finally:
            if should_close:
                await client.aclose()


def is_eligible_repository(signal: GitHubRepositorySignal) -> bool:
    if signal.fork or signal.commit_count <= 0 or not signal.readme.strip():
        return False
    tutorial_terms = ("tutorial", "course", "lesson", "learn-", "learning-", "sample", "template")
    haystack = " ".join([signal.name, signal.description or "", *signal.topics]).lower()
    return not any(term in haystack for term in tutorial_terms)


def build_github_analysis_prompt(signal: GitHubRepositorySignal) -> str:
    return (
        "Analyze this GitHub repository as a factual CV pool candidate. "
        "Use README content, language distribution, topics, commit count, and fork/original status together. "
        "Do not invent facts. Return area, technologies, and short_description only.\n\n"
        f"Repository: {signal.full_name}\n"
        f"URL: {signal.html_url}\n"
        f"Description: {signal.description or ''}\n"
        f"Fork: {signal.fork}\n"
        f"Commit count: {signal.commit_count}\n"
        f"Topics: {', '.join(signal.topics)}\n"
        f"Languages: {signal.languages}\n\n"
        f"README:\n{signal.readme[:12000]}"
    )


async def analyze_repositories_to_pool_items(
    user_id: UUID,
    db,
    github_client: GitHubAPIClient,
    llm_service: LLMService,
    embedding_service: EmbeddingService,
) -> list[PoolItem]:
    candidates = await extract_repository_pool_candidates(github_client, llm_service)
    pool_items: list[PoolItem] = []
    for candidate in candidates:
        item = normalize_extracted_item(
            user_id,
            candidate,
            embedding_service,
        )
        db.add(item)
        pool_items.append(item)
    return pool_items


async def extract_repository_pool_candidates(
    github_client: GitHubAPIClient,
    llm_service: LLMService,
) -> list[ExtractedPoolItem]:
    signals = await github_client.collect_repository_signals()
    candidates: list[ExtractedPoolItem] = []
    for signal in signals:
        analysis = await llm_service.structured(
            build_github_analysis_prompt(signal),
            GitHubRepoAnalysis,
            system_prompt="You extract factual GitHub repository signals for CV pool candidates.",
        )
        raw_content = f"{analysis.short_description}\nRepository: {signal.full_name}\nArea: {analysis.area}"
        candidates.append(
            ExtractedPoolItem(
                source=PoolItemSource.GITHUB,
                type=PoolItemType.PROJECT,
                title=signal.name,
                raw_content=raw_content,
                tags=[analysis.area, *signal.topics],
                technologies=analysis.technologies,
            )
        )
    return candidates


async def sync_github_repositories_for_user(user_id: UUID) -> None:
    with SessionLocal() as db:
        connection = db.scalar(select(GitHubConnection).where(GitHubConnection.user_id == user_id))
        if connection is None:
            return
        token = decrypt_github_token(connection.access_token_encrypted)
        items = await analyze_repositories_to_pool_items(
            user_id,
            db,
            GitHubAPIClient(token=token),
            LLMService(),
            EmbeddingService(),
        )
        if items:
            db.flush()
        from datetime import UTC, datetime

        connection.last_synced = datetime.now(UTC)
        db.commit()
