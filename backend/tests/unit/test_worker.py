import logging

import dramatiq
import pytest

from saps.config import Settings
from saps.worker.broker import install_broker


def test_install_broker_sets_the_global_broker() -> None:
    broker = install_broker(Settings(_env_file=None))
    assert dramatiq.get_broker() is broker


async def test_ping_actor_logs_the_correlation_id(caplog: pytest.LogCaptureFixture) -> None:
    from saps.worker import actors  # importing configures JSON logging and replaces root handlers

    logging.getLogger().addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger="saps.worker")
    # actor.fn is Dramatiq's sync wrapper (needs the worker event loop); __wrapped__ is the coroutine.
    await actors.ping.fn.__wrapped__("cid-1")
    assert any(r.getMessage() == "ping_received" and r.correlation_id == "cid-1" for r in caplog.records)
