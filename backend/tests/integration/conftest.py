"""One PostgreSQL container (Testcontainers) for all integration tests.

Skipped when Docker is not available.
"""

import os
import subprocess
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.integration.api_world import Api, make_api
from tests.integration.db_urls import APP_DB_PASSWORD, SYSTEM_DB_PASSWORD, app_url, system_url
from tests.integration.mail_server import mail_server  # noqa: F401  (session fixture)

BACKEND = Path(__file__).parents[2]


def alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  (fixed command, test-only)
        ["uv", "run", "alembic", *args],  # noqa: S607
        cwd=BACKEND,
        env={
            **os.environ,
            "DATABASE_URL": database_url,
            "APP_DB_PASSWORD": APP_DB_PASSWORD,
            "SYSTEM_DB_PASSWORD": SYSTEM_DB_PASSWORD,
        },
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    postgres = pytest.importorskip("testcontainers.postgres")
    try:
        container = postgres.PostgresContainer("postgres:17-alpine", driver="psycopg")
        container.start()
    except Exception as exc:  # Docker not running
        pytest.skip(f"Docker not available: {exc}")
    try:
        url: str = container.get_connection_url()
        result = alembic(url, "upgrade", "head")
        assert result.returncode == 0, result.stderr
        yield url
    finally:
        container.stop()


@pytest.fixture
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def api(engine: AsyncEngine, database_url: str, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Api]:
    async with make_api(engine, database_url, monkeypatch) as api_:
        yield api_


@pytest.fixture
async def app_engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    """Connected as `saps_app`: row-level security applies (SAPS-41)."""
    engine = create_async_engine(app_url(database_url))
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def system_engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    """Connected as `saps_system` (BYPASSRLS), like the sweeper."""
    engine = create_async_engine(system_url(database_url))
    try:
        yield engine
    finally:
        await engine.dispose()
