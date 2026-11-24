import pytest
from httpx import ASGITransport, AsyncClient

from saps.api.main import create_app


async def test_health_returns_ok_without_dependencies() -> None:
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_returns_503_when_database_is_unreachable(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://nobody:none@127.0.0.1:1/none")
    from saps.config import get_settings

    get_settings.cache_clear()
    try:
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
            response = await client.get("/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "not_ready", "database": False}
    finally:
        get_settings.cache_clear()


async def test_lifespan_configures_logging_and_disposes_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    import logging

    from cryptography.fernet import Fernet

    from saps.api.deps import token_cipher
    from saps.api.main import lifespan
    from saps.config import get_settings
    from saps.logging_config import JsonFormatter

    monkeypatch.setenv("SESSION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    get_settings.cache_clear()
    token_cipher.cache_clear()
    app = create_app()
    try:
        async with lifespan(app):
            assert isinstance(logging.getLogger().handlers[0].formatter, JsonFormatter)
    finally:
        get_settings.cache_clear()
        token_cipher.cache_clear()


async def test_start_up_fails_without_the_session_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from saps.api.deps import token_cipher
    from saps.api.main import lifespan
    from saps.config import get_settings

    monkeypatch.setenv("SESSION_ENCRYPTION_KEY", "")
    get_settings.cache_clear()
    token_cipher.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="SESSION_ENCRYPTION_KEY"):
            async with lifespan(create_app()):
                pass
    finally:
        get_settings.cache_clear()
        token_cipher.cache_clear()
