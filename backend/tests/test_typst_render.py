from __future__ import annotations

import subprocess
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api import generated_cvs as generated_cvs_api
from app.db.session import SessionLocal
from app.graphs.nodes.cvtailor import TailoredCVContent, TailoredCVItem
from app.main import app
from app.models.enums import ContentLanguage
from app.models.generated_cv import GeneratedCV
from app.models.job import Job
from app.models.user import User
from app.render.typst import TypstRenderTimeout, TypstRenderer, build_typst_source

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_users_and_overrides():
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    yield
    app.dependency_overrides.clear()
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def _auth_headers(email: str) -> dict[str, str]:
    password = "strong-password"
    register = client.post(
        "/auth/register",
        json={"email": email, "password": password, "kvkk_consent": True},
    )
    assert register.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _tailored_cv(source_id: UUID) -> dict[str, object]:
    return {
        "output_language": "en",
        "summary": "Backend engineer focused on FastAPI services.",
        "experience": [
            {
                "source_pool_item_id": str(source_id),
                "title": "Backend Engineer",
                "content": "Built APIs with FastAPI and PostgreSQL.",
                "technologies": ["FastAPI", "PostgreSQL"],
            }
        ],
        "projects": [],
        "skills": [],
    }


def test_typst_renderer_writes_pdf_and_cleans_temporary_directory(tmp_path: Path, monkeypatch) -> None:
    seen_tmp_dirs: list[Path] = []

    def fake_run(command, cwd, capture_output, text, timeout, check):
        seen_tmp_dirs.append(Path(cwd))
        assert command[1] == "compile"
        assert timeout == 1.0
        Path(cwd, "cv.pdf").write_bytes(b"%PDF-1.7\nfake\n")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    content = TailoredCVContent(
        output_language=ContentLanguage.EN,
        summary="Summary",
        experience=[
            TailoredCVItem(
                source_pool_item_id=uuid4(),
                title="Engineer",
                content='Escapes "quotes" and backslashes \\ safely.',
                technologies=["Python"],
            )
        ],
    )
    source = build_typst_source(tailored_cv=content, name="Ada Lovelace", contact=["ada@example.test"])

    output = TypstRenderer(typst_binary="typst", timeout_seconds=1.0, output_dir=tmp_path).render_pdf(
        typst_source=source,
        generated_cv_id=uuid4(),
    )

    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF")
    assert seen_tmp_dirs and not seen_tmp_dirs[0].exists()


def test_typst_renderer_timeout_does_not_leave_temporary_directory(tmp_path: Path, monkeypatch) -> None:
    seen_tmp_dirs: list[Path] = []

    def fake_timeout(command, cwd, capture_output, text, timeout, check):
        seen_tmp_dirs.append(Path(cwd))
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(subprocess, "run", fake_timeout)
    renderer = TypstRenderer(typst_binary="typst", timeout_seconds=0.01, output_dir=tmp_path)

    try:
        renderer.render_pdf(typst_source="#let cv = (:)\n", generated_cv_id=uuid4())
    except TypstRenderTimeout:
        pass
    else:
        raise AssertionError("TypstRenderTimeout was not raised")

    assert seen_tmp_dirs and not seen_tmp_dirs[0].exists()
    assert list(tmp_path.iterdir()) == []


def test_render_queue_creates_generated_cv_pdf_and_downloads(tmp_path: Path, monkeypatch) -> None:
    first_headers = _auth_headers("render-one@example.com")
    second_headers = _auth_headers("render-two@example.com")
    source_id = uuid4()

    with SessionLocal() as db:
        first_user = db.scalar(select(User).where(User.email == "render-one@example.com"))
        assert first_user is not None
        job = Job(
            user_id=first_user.id,
            raw_text="We need FastAPI and PostgreSQL.",
            detected_language=ContentLanguage.EN,
            parsed_requirements_json={"required_skills": ["FastAPI"]},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    def fake_render_task(generated_cv_id: UUID) -> None:
        pdf_path = tmp_path / f"{generated_cv_id}.pdf"
        pdf_path.write_bytes(b"%PDF-1.7\nrendered\n")
        with SessionLocal() as db:
            generated = db.get(GeneratedCV, generated_cv_id)
            assert generated is not None
            generated.pdf_path = str(pdf_path)
            db.commit()

    monkeypatch.setattr(generated_cvs_api, "render_generated_cv_task", fake_render_task)

    response = client.post(
        "/generated-cvs/render",
        headers=first_headers,
        json={
            "job_id": str(job_id),
            "selected_pool_item_ids": [str(source_id)],
            "tailored_cv": _tailored_cv(source_id),
            "ats_score": 88.5,
        },
    )

    assert response.status_code == 202
    generated_id = UUID(response.json()["id"])
    with SessionLocal() as db:
        generated = db.get(GeneratedCV, generated_id)
        assert generated is not None
        assert generated.pdf_path is not None
        assert generated.selected_pool_item_ids == [source_id]
        assert generated.ats_score == 88.5
        assert generated.output_language == ContentLanguage.EN
        assert "FastAPI" in (generated.typst_source or "")

    other_user_download = client.get(f"/generated-cvs/{generated_id}/download", headers=second_headers)
    assert other_user_download.status_code == 404

    download = client.get(f"/generated-cvs/{generated_id}/download", headers=first_headers)
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.content.startswith(b"%PDF")
