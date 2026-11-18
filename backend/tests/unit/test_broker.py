from dramatiq.middleware import AsyncIO

from saps.config import Settings
from saps.worker.broker import build_broker


def test_broker_uses_explicit_redelivery_settings_and_asyncio() -> None:
    settings = Settings(
        _env_file=None, dramatiq_heartbeat_timeout_ms=12_000, dramatiq_maintenance_chance=50_000
    )
    broker = build_broker(settings)
    assert broker.heartbeat_timeout == 12_000
    assert broker.maintenance_chance == 50_000
    assert any(isinstance(m, AsyncIO) for m in broker.middleware)
