"""Timers inside each SAPS Worker process (SAPS-37 sweeper, SAPS-45 mail intake; ADR-0004 S1, S6).

A Dramatiq middleware starts an APScheduler timer in its own thread and event loop when the worker boots and
stops it on shutdown. Every process ticks; the tick itself decides who works (advisory locks).
"""

import asyncio
import threading
from collections.abc import Awaitable, Callable

import dramatiq
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class TimerMiddleware(dramatiq.Middleware):
    def __init__(self, name: str, interval_seconds: float, tick: Callable[[], Awaitable[None]]) -> None:
        self._name = name
        self._interval = interval_seconds
        self._tick = tick
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop: asyncio.Event | None = None

    def after_worker_boot(self, broker: dramatiq.Broker, worker: dramatiq.Worker) -> None:
        self._thread = threading.Thread(
            target=lambda: asyncio.run(self._main()), name=self._name, daemon=True
        )
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
