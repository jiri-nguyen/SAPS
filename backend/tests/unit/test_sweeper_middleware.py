"""SAPS-37 sweeper timer in the SAPS Worker and its tick (TS-07)."""

import asyncio
import logging
import time
from collections.abc import Callable
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from saps.application.sweeper import GaveUp, Resent, SweepResult
from saps.config import Settings
from saps.worker import sweeper
from saps.worker.sweeper import SweeperMiddleware, run_sweep
from tests.fakes import MemoryQueue


def _wait_for(condition: Callable[[], bool], seconds: float = 3.0) -> None:
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert condition()


def test_the_timer_ticks_after_boot_and_stops_at_shutdown() -> None:
    ticks: list[int] = []

    async def tick() -> None:
        ticks.append(1)

    middleware = SweeperMiddleware(0.05, tick)
    middleware.after_worker_boot(MagicMock(), MagicMock())
    _wait_for(lambda: len(ticks) >= 3)
    middleware.before_worker_shutdown(MagicMock(), MagicMock())  # EC-06
    stopped_at = len(ticks)
    time.sleep(0.25)
    assert len(ticks) == stopped_at
    middleware.before_worker_shutdown(MagicMock(), MagicMock())  # a second call changes nothing


def test_a_failing_tick_does_not_stop_the_timer() -> None:  # EC-05
    calls: list[int] = []

    async def tick() -> None:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("database down")

    middleware = SweeperMiddleware(0.05, tick)
    middleware.after_worker_boot(MagicMock(), MagicMock())
    try:
        _wait_for(lambda: len(calls) >= 3)
    finally:
        middleware.before_worker_shutdown(MagicMock(), MagicMock())


def test_shutdown_without_boot_does_nothing() -> None:
    SweeperMiddleware(1, MagicMock()).before_worker_shutdown(MagicMock(), MagicMock())


class _Service:
    outcome: SweepResult | Exception | None = None

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    async def sweep(self) -> SweepResult | None:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def no_database(monkeypatch: pytest.MonkeyPatch) -> type[_Service]:
    monkeypatch.setattr(sweeper, "get_engine", lambda url: None)
    monkeypatch.setattr(sweeper, "session_factory", lambda engine: None)
    monkeypatch.setattr(sweeper, "SweeperService", _Service)
    return _Service


async def test_every_resent_invoice_is_logged(
    no_database: type[_Service], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="saps.worker.sweeper")
    invoice_id, tenant_id = uuid4(), uuid4()
    no_database.outcome = SweepResult([Resent(invoice_id, tenant_id, "process_invoice")], [])
    await run_sweep(Settings(_env_file=None), MemoryQueue())
    [record] = caplog.records
    assert record.getMessage() == "sweeper_resent"
    assert (record.__dict__["invoice_id"], record.__dict__["message_name"]) == (
        str(invoice_id),
        "process_invoice",
    )


@pytest.mark.parametrize("outcome", [None, SweepResult([], [])])
async def test_an_idle_tick_logs_nothing(
    no_database: type[_Service], caplog: pytest.LogCaptureFixture, outcome: SweepResult | None
) -> None:
    caplog.set_level(logging.INFO, logger="saps.worker.sweeper")
    no_database.outcome = outcome
    await run_sweep(Settings(_env_file=None), MemoryQueue())
    assert caplog.records == []


async def test_a_failed_tick_is_logged_and_does_not_raise(
    no_database: type[_Service], caplog: pytest.LogCaptureFixture
) -> None:  # EC-03, EC-05
    no_database.outcome = ConnectionError("Redis down")
    await run_sweep(Settings(_env_file=None), MemoryQueue())
    [record] = caplog.records
    assert (record.levelno, record.getMessage()) == (logging.ERROR, "sweeper_failed")
    await asyncio.sleep(0)


async def test_giving_up_on_an_invoice_is_logged_as_a_warning(
    no_database: type[_Service], caplog: pytest.LogCaptureFixture
) -> None:  # SAPS-38 BR-05
    caplog.set_level(logging.INFO, logger="saps.worker.sweeper")
    invoice_id, tenant_id = uuid4(), uuid4()
    no_database.outcome = SweepResult([], [GaveUp(invoice_id, tenant_id, 3)])
    await run_sweep(Settings(_env_file=None), MemoryQueue())
    [record] = caplog.records
    assert (record.levelno, record.getMessage()) == (logging.WARNING, "sweeper_gave_up")
    assert (record.__dict__["invoice_id"], record.__dict__["resends"]) == (str(invoice_id), 3)
