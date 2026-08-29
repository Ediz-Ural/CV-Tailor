from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)

ALLOWED_ORIGIN = settings.cors_allow_origin_list[0]


def test_preflight_allows_configured_origin() -> None:
    response = client.options(
        "/auth/login",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_preflight_rejects_unknown_origin() -> None:
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_origin_list_is_parsed_and_normalised() -> None:
    settings_origins = settings.cors_allow_origin_list

    assert settings_origins
    assert all(not origin.endswith("/") for origin in settings_origins)
    assert all(origin == origin.strip() for origin in settings_origins)
