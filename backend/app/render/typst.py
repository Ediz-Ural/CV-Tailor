from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.graphs.nodes.cvtailor import TailoredCVContent, TailoredCVItem

TEMPLATE_PATH = Path(__file__).parent / "templates" / "jakes_resume.typ"


class TypstRenderError(RuntimeError):
    pass


class TypstRenderTimeout(TypstRenderError):
    pass


def _typst_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _typst_value(value: Any) -> str:
    if isinstance(value, str):
        return _typst_string(value)
    if isinstance(value, list):
        items = ", ".join(_typst_value(item) for item in value)
        if len(value) == 1:
            items += ","
        return "(" + items + ")"
    if isinstance(value, dict):
        fields = ", ".join(f"{key}: {_typst_value(item)}" for key, item in value.items())
        return f"({fields})"
    if value is None:
        return '""'
    return _typst_string(str(value))


def _item_payload(item: TailoredCVItem) -> dict[str, Any]:
    return {
        "title": item.title or "",
        "content": item.content,
        "technologies": item.technologies,
    }


def build_typst_source(
    *,
    tailored_cv: TailoredCVContent,
    name: str,
    contact: list[str] | None = None,
    education: list[dict[str, str]] | None = None,
    template_path: Path = TEMPLATE_PATH,
) -> str:
    education_items = [
        {
            "title": item.get("title") or item.get("school") or "",
            "content": item.get("content") or item.get("degree") or "",
            "technologies": [],
        }
        for item in (education or [])
    ]
    cv_payload = {
        "name": name,
        "contact": contact or [],
        "output_language": tailored_cv.output_language.value,
        "summary": tailored_cv.summary,
        "experience": [_item_payload(item) for item in tailored_cv.experience],
        "projects": [_item_payload(item) for item in tailored_cv.projects],
        "skills": [_item_payload(item) for item in tailored_cv.skills],
        "education": education_items,
    }
    template = template_path.read_text(encoding="utf-8")
    return f"#let cv = {_typst_value(cv_payload)}\n\n{template}"


class TypstRenderer:
    def __init__(
        self,
        *,
        typst_binary: str | None = None,
        timeout_seconds: float | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.typst_binary = typst_binary or settings.typst_binary
        self.timeout_seconds = timeout_seconds or settings.typst_render_timeout_seconds
        self.output_dir = Path(output_dir or settings.render_output_dir)

    def render_pdf(self, *, typst_source: str, generated_cv_id: UUID) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        final_path = self.output_dir / f"{generated_cv_id}.pdf"
        with tempfile.TemporaryDirectory(prefix="cv-tailor-typst-") as tmp:
            tmp_dir = Path(tmp)
            source_path = tmp_dir / "cv.typ"
            temp_pdf_path = tmp_dir / "cv.pdf"
            source_path.write_text(typst_source, encoding="utf-8")
            command = [self.typst_binary, "compile", str(source_path.name), str(temp_pdf_path.name)]
            try:
                result = subprocess.run(
                    command,
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise TypstRenderTimeout(f"Typst render timed out after {self.timeout_seconds}s") from exc
            except OSError as exc:
                raise TypstRenderError(f"Typst CLI could not be started: {exc}") from exc

            if result.returncode != 0:
                stderr = result.stderr.strip() or result.stdout.strip()
                raise TypstRenderError(f"Typst render failed: {stderr}")
            if not temp_pdf_path.exists():
                raise TypstRenderError("Typst finished without producing a PDF")

            shutil.copyfile(temp_pdf_path, final_path)
        return final_path
