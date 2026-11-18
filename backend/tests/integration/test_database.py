"""Integration: migrations and readiness on a real PostgreSQL."""

import pytest
from httpx import ASGITransport, AsyncClient

from tests.integration.conftest import alembic

pytestmark = pytest.mark.integration


def test_migrations_match_the_models_and_downgrade(database_url: str) -> None:
    check = alembic(database_url, "check")
    assert check.returncode == 0, check.stdout + check.stderr  # no drift between models and migrations
    down = alembic(database_url, "downgrade", "0001")
    assert down.returncode == 0, down.stderr
    up = alembic(database_url, "upgrade", "head")
    assert up.returncode == 0, up.stderr


async def test_ready_is_ok_with_a_reachable_database(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saps.adapters.persistence.db import dispose_engines
    from saps.api.main import create_app
    from saps.config import get_settings

    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
            response = await client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": True}
    finally:
        await dispose_engines()
        get_settings.cache_clear()
