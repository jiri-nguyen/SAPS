"""Dramatiq broker for the SAPS Worker (ADR-0004)."""

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO

from saps.config import Settings


def build_broker(settings: Settings) -> RedisBroker:
    """Redis broker with explicit redelivery settings (ADR-0004 S7) and async actors (S5)."""
    broker = RedisBroker(
        url=settings.redis_url,
        heartbeat_timeout=settings.dramatiq_heartbeat_timeout_ms,
        maintenance_chance=settings.dramatiq_maintenance_chance,
    )
    broker.add_middleware(AsyncIO())
    return broker


def install_broker(settings: Settings) -> RedisBroker:
    broker = build_broker(settings)
    dramatiq.set_broker(broker)
    return broker
