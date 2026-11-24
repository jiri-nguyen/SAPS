"""Connection URLs of the three database roles in tests (SAPS-41).

The owner runs migrations and test set-up, the SAPS API and worker jobs run as `saps_app`, the sweeper as
`saps_system`.
"""

import pytest
from sqlalchemy.engine import make_url

from saps.config import get_settings

APP_DB_PASSWORD = "saps-app-test"  # noqa: S105  (test-only role password)
SYSTEM_DB_PASSWORD = "saps-system-test"  # noqa: S105  (test-only role password)


def role_url(database_url: str, role: str, password: str) -> str:
    return make_url(database_url).set(username=role, password=password).render_as_string(hide_password=False)


def app_url(database_url: str) -> str:
    return role_url(database_url, "saps_app", APP_DB_PASSWORD)


def system_url(database_url: str) -> str:
    return role_url(database_url, "saps_system", SYSTEM_DB_PASSWORD)


def use_database(monkeypatch: pytest.MonkeyPatch, database_url: str) -> None:
    """Point the settings at the test database with the three roles."""
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_DATABASE_URL", app_url(database_url))
    monkeypatch.setenv("SYSTEM_DATABASE_URL", system_url(database_url))
    monkeypatch.setenv("APP_DB_PASSWORD", APP_DB_PASSWORD)
    monkeypatch.setenv("SYSTEM_DB_PASSWORD", SYSTEM_DB_PASSWORD)
    get_settings.cache_clear()
