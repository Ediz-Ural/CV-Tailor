"""Shared test setup.

The suite runs against a real Postgres instance and truncates tables between
tests, so it refuses to start unless it is clearly pointed at a throwaway
database. Set CV_TAILOR_ALLOW_DESTRUCTIVE_TESTS=1 to override.
"""

import os

import pytest
from sqlalchemy.engine import make_url

from app.core.config import settings

SAFE_DATABASE_SUFFIXES = ("_test", "_ci")


def _database_name() -> str:
    return make_url(settings.database_url).database or ""


def pytest_configure(config: pytest.Config) -> None:
    if os.getenv("CV_TAILOR_ALLOW_DESTRUCTIVE_TESTS") == "1":
        return

    database = _database_name()
    if database.endswith(SAFE_DATABASE_SUFFIXES):
        return

    raise pytest.UsageError(
        f"Refusing to run the destructive test suite against database {database!r}. "
        "Point DATABASE_URL at a database whose name ends with '_test' "
        "(e.g. cv_tailor_test), or set CV_TAILOR_ALLOW_DESTRUCTIVE_TESTS=1 if you "
        "really mean to wipe this one."
    )
