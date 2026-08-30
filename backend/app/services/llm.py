import asyncio
import copy
import json
from collections.abc import Mapping
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, settings

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class LLMError(RuntimeError):
    """Base error for provider and structured-output failures."""


class LLMConfigurationError(LLMError):
    pass


class LLMProviderError(LLMError):
    pass


class LLMStructuredOutputError(LLMError):
    pass


def _provider_error_message(provider: str, exc: Exception, timeout_seconds: float) -> str:
    """Say enough for the user to act on it.

    A bare "openai request failed" reaches the UI with no hint that the cause is
    usually an unset or wrong API key.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code in (401, 403):
            return (
            f"{provider} rejected the API key (HTTP {status_code}). "
            "Check the API key saved on your account."
        )
        if status_code == 429:
            return f"{provider} rate limit reached (HTTP 429). Try again shortly."
        return f"{provider} request failed with HTTP {status_code}"
    if isinstance(exc, httpx.TimeoutException):
        return f"{provider} request timed out after {timeout_seconds:g}s"
    return f"{provider} could not be reached"


class LLMService:
    def __init__(
        self,
        config: Settings = settings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self._client = client

    async def structured(
        self,
        prompt: str,
        response_model: type[StructuredModel],
        *,
        system_prompt: str | None = None,
    ) -> StructuredModel:
        provider = self.config.llm_provider.lower().strip()
        if provider == "mock":
            return self._mock_structured(prompt, response_model)

        if not self.config.llm_api_key:
            raise LLMConfigurationError("LLM_API_KEY is not configured")

        schema = response_model.model_json_schema()
        payload = self._build_payload(provider, prompt, system_prompt, response_model.__name__, schema)
        response_data = await self._post_with_retry(provider, payload)

        try:
            content = self._extract_content(provider, response_data)
            return response_model.model_validate_json(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise LLMStructuredOutputError("Provider returned invalid structured output") from exc

    def _build_payload(
        self,
        provider: str,
        prompt: str,
        system_prompt: str | None,
        schema_name: str,
        schema: Mapping[str, Any],
    ) -> dict[str, Any]:
        if provider == "openai":
            schema = _openai_strict_json_schema(schema)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            return {
                "model": self.config.llm_model,
                "messages": messages,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": schema_name, "strict": True, "schema": schema},
                },
            }

        if provider == "anthropic":
            payload: dict[str, Any] = {
                "model": self.config.llm_model,
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
                "tools": [
                    {
                        "name": "structured_output",
                        "description": "Return the requested structured result.",
                        "input_schema": schema,
                    }
                ],
                "tool_choice": {"type": "tool", "name": "structured_output"},
            }
            if system_prompt:
                payload["system"] = system_prompt
            return payload

        raise LLMConfigurationError(f"Unsupported LLM provider: {provider}")

    async def _post_with_retry(self, provider: str, payload: dict[str, Any]) -> dict[str, Any]:
        url, headers = self._provider_request(provider)
        retry_statuses = {408, 409, 429, 500, 502, 503, 504}
        client = self._client or httpx.AsyncClient(timeout=self.config.llm_timeout_seconds)
        should_close = self._client is None

        try:
            for attempt in range(self.config.llm_max_retries + 1):
                try:
                    response = await client.post(url, headers=headers, json=payload)
                    if response.status_code not in retry_statuses:
                        response.raise_for_status()
                        return response.json()
                    if attempt == self.config.llm_max_retries:
                        response.raise_for_status()
                except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                    retryable = not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code in retry_statuses
                    if not retryable or attempt == self.config.llm_max_retries:
                        raise LLMProviderError(
                            _provider_error_message(provider, exc, self.config.llm_timeout_seconds)
                        ) from exc
                await asyncio.sleep(min(2**attempt, 4))
        finally:
            if should_close:
                await client.aclose()

        raise LLMProviderError(f"{provider} request failed")

    async def verify_credentials(self) -> None:
        """Check the configured key against the provider.

        Saving a key that turns out to be wrong is only discovered several
        minutes later, at the first pipeline step, so the credential endpoint
        makes the cheapest possible call up front.
        """
        provider = self.config.llm_provider.lower().strip()
        if provider == "mock":
            return
        if not self.config.llm_api_key:
            raise LLMConfigurationError("LLM API key is not configured")

        url, headers = self._verification_request(provider)
        client = self._client or httpx.AsyncClient(timeout=self.config.llm_timeout_seconds)
        should_close = self._client is None
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(
                _provider_error_message(provider, exc, self.config.llm_timeout_seconds)
            ) from exc
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise LLMProviderError(
                _provider_error_message(provider, exc, self.config.llm_timeout_seconds)
            ) from exc
        finally:
            if should_close:
                await client.aclose()

    def _verification_request(self, provider: str) -> tuple[str, dict[str, str]]:
        if provider == "openai":
            return (
                "https://api.openai.com/v1/models",
                {"Authorization": f"Bearer {self.config.llm_api_key}"},
            )
        if provider == "anthropic":
            return (
                "https://api.anthropic.com/v1/models",
                {
                    "x-api-key": self.config.llm_api_key or "",
                    "anthropic-version": "2023-06-01",
                },
            )
        raise LLMConfigurationError(f"Unsupported LLM provider: {provider}")

    def _provider_request(self, provider: str) -> tuple[str, dict[str, str]]:
        if provider == "openai":
            return (
                "https://api.openai.com/v1/chat/completions",
                {"Authorization": f"Bearer {self.config.llm_api_key}"},
            )
        if provider == "anthropic":
            return (
                "https://api.anthropic.com/v1/messages",
                {
                    "x-api-key": self.config.llm_api_key or "",
                    "anthropic-version": "2023-06-01",
                },
            )
        raise LLMConfigurationError(f"Unsupported LLM provider: {provider}")

    def _mock_structured(self, prompt: str, response_model: type[StructuredModel]) -> StructuredModel:
        if response_model.__name__ == "JobRequirementExtraction":
            return response_model.model_validate(
                {
                    "summary": "Backend role requiring FastAPI and PostgreSQL experience.",
                    "required_skills": ["FastAPI", "PostgreSQL"],
                    "preferred_skills": ["Docker"],
                    "years_experience": 3,
                    "key_terms": ["REST API"],
                }
            )
        raise LLMProviderError(f"Mock provider does not implement {response_model.__name__}")

    @staticmethod
    def _extract_content(provider: str, data: Mapping[str, Any]) -> str:
        if provider == "openai":
            return data["choices"][0]["message"]["content"]
        if provider == "anthropic":
            for block in data["content"]:
                if block.get("type") == "tool_use" and block.get("name") == "structured_output":
                    return json.dumps(block["input"])
            raise KeyError("structured_output tool result missing")
        raise LLMConfigurationError(f"Unsupported LLM provider: {provider}")


def _openai_strict_json_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    strict_schema = copy.deepcopy(dict(schema))

    def normalize(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" or "properties" in node:
                properties = node.get("properties")
                if isinstance(properties, dict):
                    node["required"] = list(properties.keys())
                    node["additionalProperties"] = False
            for value in node.values():
                normalize(value)
        elif isinstance(node, list):
            for item in node:
                normalize(item)

    normalize(strict_schema)
    return strict_schema
