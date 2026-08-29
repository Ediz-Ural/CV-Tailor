from html.parser import HTMLParser
from typing import Protocol

import httpx

from app.schemas.job import JobRequirementExtraction
from app.services.embeddings import Language, detect_language
from app.services.llm import LLMService


class JobParserError(RuntimeError):
    pass


class JobFetchError(JobParserError):
    pass


class StructuredLLM(Protocol):
    async def structured(
        self,
        prompt: str,
        response_model: type[JobRequirementExtraction],
        *,
        system_prompt: str | None = None,
    ) -> JobRequirementExtraction: ...


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            clean = " ".join(data.split())
            if clean:
                self.parts.append(clean)

    def text(self) -> str:
        return "\n".join(self.parts)


def html_to_text(content: str) -> str:
    parser = _TextHTMLParser()
    parser.feed(content)
    return parser.text().strip()


def dominant_job_language(text: str) -> Language:
    detected = detect_language(text)
    if detected != "mixed":
        return detected

    normalized = text.casefold()
    tr_markers = sum(normalized.count(marker) for marker in (" için", " ve ", " ile ", " aranan", " deneyim"))
    en_markers = sum(normalized.count(marker) for marker in (" for ", " and ", " with ", " required", " experience"))
    return "tr" if tr_markers >= en_markers else "en"


class JobParser:
    def __init__(self, llm_service: StructuredLLM | LLMService) -> None:
        self.llm_service = llm_service

    async def parse(self, raw_text: str) -> tuple[Language, JobRequirementExtraction]:
        language = dominant_job_language(raw_text)
        prompt = (
            "Extract structured job requirements from the posting below. "
            "Support Turkish, English, and mixed-language postings. "
            "Keep technical terms exactly as written when possible. "
            "Also write a concise summary of what the role is, what it expects, and the most important signals for the candidate. "
            "Return only fields that are supported by the posting.\n\n"
            f"Job posting:\n{raw_text}"
        )
        system_prompt = (
            "You are JobParser for CV-Tailor. Extract required skills, preferred skills, "
            "years of experience, key terms, and a concise job summary as JSON matching the schema. Do not invent requirements."
        )
        requirements = await self.llm_service.structured(
            prompt,
            JobRequirementExtraction,
            system_prompt=system_prompt,
        )
        return language, requirements


async def fetch_single_job_page(url: str, client: httpx.AsyncClient) -> str:
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise JobFetchError("URL fetch failed") from exc

    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        text = html_to_text(response.text)
    elif content_type.startswith("text/") or not content_type:
        text = response.text.strip()
    else:
        raise JobFetchError("URL must return a text or HTML page")

    if not text:
        raise JobFetchError("URL returned an empty page")
    return text
