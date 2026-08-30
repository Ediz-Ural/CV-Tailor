import json

import httpx
import pytest
from pydantic import BaseModel

from app.core.config import EMBEDDING_DIMENSION, Settings
from app.schemas.job import JobRequirementExtraction
from app.services.embeddings import EmbeddingError, EmbeddingService, detect_language
from app.services.llm import LLMProviderError, LLMService, _openai_strict_json_schema


class FakeEncoder:
    def encode(self, text: str, *, normalize_embeddings: bool) -> list[float]:
        assert text == "merhaba dunya / hello world"
        assert normalize_embeddings is True
        return [0.25] * EMBEDDING_DIMENSION


class Summary(BaseModel):
    language: str
    keywords: list[str]


def test_embed_returns_vector_matching_database_dimension() -> None:
    service = EmbeddingService(encoder=FakeEncoder())

    vector = service.embed("merhaba dunya / hello world")

    assert len(vector) == EMBEDDING_DIMENSION == 1024
    assert vector[0] == 0.25


def test_mock_embedding_returns_vector_matching_database_dimension() -> None:
    service = EmbeddingService(Settings(embedding_model="mock"))

    vector = service.embed("FastAPI PostgreSQL")

    assert len(vector) == EMBEDDING_DIMENSION == 1024
    assert vector[0] == 1.0


def test_openai_embedding_encoder_uses_1024_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[dict] = []

    def fake_post(url: str, *, headers: dict[str, str], json: dict, timeout: float) -> httpx.Response:
        requests.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"data": [{"embedding": [0.125] * EMBEDDING_DIMENSION}]}, request=request)

    monkeypatch.setattr("app.services.embeddings.httpx.post", fake_post)
    service = EmbeddingService(
        Settings(
            embedding_model="openai/text-embedding-3-small",
            llm_api_key="test-key",
            llm_timeout_seconds=12,
        )
    )

    vector = service.embed("FastAPI PostgreSQL")

    assert len(vector) == EMBEDDING_DIMENSION
    assert vector[0] == 0.125
    assert requests[0]["url"] == "https://api.openai.com/v1/embeddings"
    assert requests[0]["headers"]["Authorization"] == "Bearer test-key"
    assert requests[0]["json"]["model"] == "text-embedding-3-small"
    assert requests[0]["json"]["dimensions"] == EMBEDDING_DIMENSION


def test_openai_strict_schema_requires_all_object_properties() -> None:
    schema = _openai_strict_json_schema(JobRequirementExtraction.model_json_schema())

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"summary", "required_skills", "preferred_skills", "years_experience", "key_terms"}


def test_embed_rejects_a_model_with_the_wrong_dimension() -> None:
    # Padding a short vector satisfies the column and silently ruins the
    # geometry the selector ranks on, so a misconfigured model must fail loudly.
    class ShortEncoder:
        def encode(self, text: str, *, normalize_embeddings: bool) -> list[float]:
            return [0.5, 0.25]

    with pytest.raises(EmbeddingError) as caught:
        EmbeddingService(encoder=ShortEncoder()).embed("hello")

    assert "2 dimensions" in str(caught.value)
    assert str(EMBEDDING_DIMENSION) in str(caught.value)
    assert "EMBEDDING_MODEL" in str(caught.value)


def test_embed_rejects_empty_vector() -> None:
    class EmptyEncoder:
        def encode(self, text: str, *, normalize_embeddings: bool) -> list[float]:
            return []

    with pytest.raises(EmbeddingError, match="must not be empty"):
        EmbeddingService(encoder=EmptyEncoder()).embed("hello")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Merhaba, bu bir yazilim gelistirme projesidir.", "tr"),
        ("Hello, this is a software development project.", "en"),
        ("Bu project icin FastAPI experience ve yazilim gelistirme bilgisi gerekli.", "mixed"),
    ],
)
def test_detect_language(text: str, expected: str) -> None:
    assert detect_language(text) == expected


@pytest.mark.asyncio
async def test_openai_structured_output_parses_pydantic_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["response_format"]["type"] == "json_schema"
        assert payload["response_format"]["json_schema"]["strict"] is True
        schema = payload["response_format"]["json_schema"]["schema"]
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == {"language", "keywords"}
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"language":"mixed","keywords":["FastAPI"]}'}}
                ]
            },
        )

    config = Settings(
        llm_api_key="test-key",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await LLMService(config, client).structured("Parse this", Summary)

    assert result == Summary(language="mixed", keywords=["FastAPI"])


@pytest.mark.asyncio
async def test_mock_llm_extracts_job_requirements() -> None:
    service = LLMService(Settings(llm_provider="mock", llm_api_key=None))

    result = await service.structured("FastAPI PostgreSQL role", JobRequirementExtraction)

    assert result.required_skills == ["FastAPI", "PostgreSQL"]


@pytest.mark.asyncio
async def test_anthropic_structured_output_parses_pydantic_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["tool_choice"]["name"] == "structured_output"
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "tool_use",
                        "name": "structured_output",
                        "input": {"language": "tr", "keywords": ["Python"]},
                    }
                ]
            },
        )

    config = Settings(
        llm_api_key="test-key",
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-5",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await LLMService(config, client).structured("Parse this", Summary)

    assert result == Summary(language="tr", keywords=["Python"])


@pytest.mark.asyncio
async def test_llm_retries_transient_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"language":"en","keywords":[]}'}}]},
        )

    async def no_sleep(delay: float) -> None:
        assert delay == 1

    monkeypatch.setattr("app.services.llm.asyncio.sleep", no_sleep)
    config = Settings(llm_api_key="test-key", llm_max_retries=1)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await LLMService(config, client).structured("Parse this", Summary)

    assert attempts == 2
    assert result.language == "en"


@pytest.mark.asyncio
async def test_rejected_api_key_error_names_the_setting_to_fix() -> None:
    # "openai request failed" reaches the pipeline UI verbatim, so it has to say
    # what the user should actually change.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_api_key"})

    config = Settings(llm_api_key="wrong-key", llm_max_retries=0)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LLMProviderError) as caught:
            await LLMService(config, client).structured("Parse this", Summary)

    assert "401" in str(caught.value)
    assert "API key saved on your account" in str(caught.value)
