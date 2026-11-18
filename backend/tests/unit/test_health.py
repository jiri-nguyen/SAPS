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


async def test_lifespan_configures_logging_and_disposes_engines() -> None:
    import logging

    from saps.api.main import lifespan
    from saps.logging_config import JsonFormatter

    app = create_app()
    async with lifespan(app):
        assert isinstance(logging.getLogger().handlers[0].formatter, JsonFormatter)
