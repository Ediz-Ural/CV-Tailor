import re
from collections.abc import Sequence
from functools import lru_cache
from typing import Literal, Protocol

import httpx

from app.core.config import EMBEDDING_DIMENSION, Settings, settings

Language = Literal["tr", "en", "mixed"]

_TR_WORDS = {
    "bir", "bu", "icin", "ile", "ve", "veya", "ama", "olarak", "olan", "deneyim",
    "gelistirme", "merhaba", "dunya", "proje", "yazilim", "muhendis", "takim",
}
_EN_WORDS = {
    "a", "an", "and", "are", "as", "for", "hello", "in", "is", "of", "or", "project",
    "software", "team", "the", "to", "with", "world", "experience", "engineer",
}


class Encoder(Protocol):
    def encode(self, text: str, *, normalize_embeddings: bool) -> Sequence[float]: ...


class EmbeddingError(RuntimeError):
    pass


@lru_cache(maxsize=4)
def _load_text_embedding(model_name: str):
    """Load a fastembed model once per process.

    Building TextEmbedding reads a multi-gigabyte model into memory. A fresh
    EmbeddingService is constructed per request, so without this every single
    call that needs an embedding paid the load cost again - roughly half a
    minute for one pool item, and over two minutes inside the selector.
    """
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model_name)


class FastEmbedEncoder:
    def __init__(self, model_name: str) -> None:
        self._model = _load_text_embedding(model_name)

    def encode(self, text: str, *, normalize_embeddings: bool) -> Sequence[float]:
        # FastEmbed's supported retrieval models return normalized embeddings.
        return next(iter(self._model.embed([text])))


class OpenAIEmbeddingEncoder:
    def __init__(self, model_name: str, api_key: str, timeout_seconds: float) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def encode(self, text: str, *, normalize_embeddings: bool) -> Sequence[float]:
        response = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model_name, "input": text, "dimensions": EMBEDDING_DIMENSION},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]


class MockEncoder:
    def encode(self, text: str, *, normalize_embeddings: bool) -> Sequence[float]:
        values = [0.0] * EMBEDDING_DIMENSION
        values[0] = 1.0
        return values


class EmbeddingService:
    def __init__(self, config: Settings = settings, encoder: Encoder | None = None) -> None:
        self.config = config
        self._encoder = encoder

    def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Text must not be empty")

        try:
            vector = [float(value) for value in self._get_encoder().encode(text, normalize_embeddings=True)]
        except Exception as exc:
            if isinstance(exc, (ValueError, EmbeddingError)):
                raise
            raise EmbeddingError("Embedding generation failed") from exc

        return _fit_embedding_dimension(vector)

    def _get_encoder(self) -> Encoder:
        if self._encoder is None:
            model_name = self.config.embedding_model.strip()
            normalized_model_name = model_name.lower()
            if normalized_model_name == "mock":
                self._encoder = MockEncoder()
                return self._encoder
            if normalized_model_name.startswith("openai/"):
                if not self.config.llm_api_key:
                    raise EmbeddingError("LLM_API_KEY is required for OpenAI embeddings")
                self._encoder = OpenAIEmbeddingEncoder(
                    model_name=model_name.split("/", 1)[1],
                    api_key=self.config.llm_api_key,
                    timeout_seconds=self.config.llm_timeout_seconds,
                )
                return self._encoder
            try:
                self._encoder = FastEmbedEncoder(model_name)
            except Exception as exc:
                raise EmbeddingError(f"Could not load embedding model {model_name}") from exc
        return self._encoder


def embed(text: str) -> list[float]:
    return EmbeddingService().embed(text)


def _fit_embedding_dimension(vector: list[float]) -> list[float]:
    if not vector:
        raise EmbeddingError("Embedding vector must not be empty")
    if len(vector) == EMBEDDING_DIMENSION:
        return vector

    # Truncating drops real signal, and padding only looks harmless: it keeps
    # cosine distance intact between two vectors from the same model, so the
    # mismatch stays invisible until the model is changed and old rows are
    # silently compared against new ones. Refuse the write instead.
    raise EmbeddingError(
        f"Embedding model produced {len(vector)} dimensions but the pool_items "
        f"column stores {EMBEDDING_DIMENSION}. Set EMBEDDING_MODEL to a model with "
        f"{EMBEDDING_DIMENSION} dimensions; changing it means re-embedding existing pool items."
    )


def detect_language(text: str) -> Language:
    normalized = text.casefold().translate(
        str.maketrans("\u00e7\u011f\u0131\u00f6\u015f\u00fc", "cgiosu")
    )
    words = re.findall(r"[a-z]+", normalized)
    if not words:
        return "mixed"

    tr_score = sum(word in _TR_WORDS for word in words)
    en_score = sum(word in _EN_WORDS for word in words)

    if tr_score and en_score:
        smaller, larger = sorted((tr_score, en_score))
        if smaller / larger >= 0.35:
            return "mixed"
    if tr_score > en_score:
        return "tr"
    if en_score > tr_score:
        return "en"

    # Turkish-specific letters are a useful fallback when stop words are absent.
    if re.search(r"[\u00e7\u011f\u0131\u00f6\u015f\u00fc]", text.casefold()):
        return "tr"
    return "mixed"


assert EMBEDDING_DIMENSION == 1024
