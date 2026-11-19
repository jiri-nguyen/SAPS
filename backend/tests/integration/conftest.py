"""One PostgreSQL container (Testcontainers) for all integration tests.

Skipped when Docker is not available.
"""

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

BACKEND = Path(__file__).parents[2]


def alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  (fixed command, test-only)
        ["uv", "run", "alembic", *args],  # noqa: S607
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": database_url},
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
