from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["database"] == "ok"


def test_metrics() -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "pipelines" in payload
    assert "render_queue" in payload
