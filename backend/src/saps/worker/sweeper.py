"""The sweeper timer inside each SAPS Worker process (SAPS-37, ADR-0004 S1, S6).

A Dramatiq middleware starts an APScheduler timer in its own thread and event loop when the worker boots and
stops it on shutdown. Every process ticks; the advisory lock lets only one sweep per tick (BR-03).
"""

import asyncio
import logging
import threading
from collections.abc import Awaitable, Callable

import dramatiq
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from saps.adapters.persistence.db import get_engine, session_factory
from saps.adapters.persistence.sweeper_repository import SqlSweepUnitOfWork
from saps.application.sweeper import SweeperService
from saps.config import Settings
from saps.ports.job_queue import JobQueuePort

log = logging.getLogger("saps.worker.sweeper")


async def run_sweep(settings: Settings, queue: JobQueuePort) -> None:
    """One tick. Never raises: a failed tick is logged and the next one tries again (EC-03, EC-05)."""
    try:
        sessions = session_factory(get_engine(settings.system_database_url))  # every company (SAPS-41 BR-04)
        service = SweeperService(
            SqlSweepUnitOfWork(sessions),
            queue,
            settings.sweeper_stuck_after_seconds,
            max_resends=settings.sweeper_max_resends,
        )
        result = await service.sweep()
    except Exception:
        log.exception("sweeper_failed")
        return
    if result is None:
        return
    for item in result.resent:
        log.info(
            "sweeper_resent",
            extra={
                "invoice_id": str(item.invoice_id),
                "tenant_id": str(item.tenant_id),
                "message_name": item.message,
            },
        )
    for gave_up in result.gave_up:
        log.warning(
            "sweeper_gave_up",
            extra={
                "invoice_id": str(gave_up.invoice_id),
                "tenant_id": str(gave_up.tenant_id),
                "resends": gave_up.resends,
            },
        )


class SweeperMiddleware(dramatiq.Middleware):
    def __init__(self, interval_seconds: float, tick: Callable[[], Awaitable[None]]) -> None:
        self._interval = interval_seconds
        self._tick = tick
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop: asyncio.Event | None = None

    def after_worker_boot(self, broker: dramatiq.Broker, worker: dramatiq.Worker) -> None:
        self._thread = threading.Thread(target=lambda: asyncio.run(self._main()), name="sweeper", daemon=True)
        self._thread.start()
        self._started.wait(timeout=10)

    def before_worker_shutdown(self, broker: dramatiq.Broker, worker: dramatiq.Worker) -> None:
        if self._thread is None:
            return
        if self._loop is not None and self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)  # EC-06
        self._thread.join(timeout=10)
        self._thread = None

    async def _main(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        scheduler = AsyncIOScheduler()
        scheduler.add_job(self._tick, "interval", seconds=self._interval, max_instances=1, coalesce=True)
        scheduler.start()
        self._started.set()
        await self._stop.wait()
        scheduler.shutdown(wait=False)
