"""The sweeper tick of the SAPS Worker (SAPS-37, ADR-0004 S1, S6); the timer is `worker/timer.py`.

Every process ticks; the advisory lock lets only one sweep per tick (BR-03).
"""

import logging
from collections.abc import Awaitable, Callable

from saps.adapters.persistence.db import get_engine, session_factory
from saps.adapters.persistence.sweeper_repository import SqlSweepUnitOfWork
from saps.application.sweeper import SweeperService
from saps.config import Settings
from saps.ports.job_queue import JobQueuePort
from saps.worker.timer import TimerMiddleware

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


class SweeperMiddleware(TimerMiddleware):
    def __init__(self, interval_seconds: float, tick: Callable[[], Awaitable[None]]) -> None:
        super().__init__("sweeper", interval_seconds, tick)
