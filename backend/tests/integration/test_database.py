"""Integration: real PostgreSQL in Docker (Testcontainers); skipped when Docker is not available."""

import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.integration

docker = pytest.importorskip("testcontainers.postgres")


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    try:
        container = docker.PostgresContainer("postgres:17-alpine", driver="psycopg")
        container.start()
    except Exception as exc:  # Docker not running
        pytest.skip(f"Docker not available: {exc}")
    try:
        yield container.get_connection_url()
    finally:
        container.stop()


def test_migrations_run_to_head(database_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    backend = Path(__file__).parents[2]
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],  # noqa: S607
        cwd=backend,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


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
