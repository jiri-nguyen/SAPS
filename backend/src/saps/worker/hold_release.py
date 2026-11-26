"""The release timer of the SAPS Worker (SAPS-52 BR-05); the timer itself is `worker/timer.py`.

Every process ticks; an advisory lock lets one of them release at a time. A tick never raises: a failed
tick is logged and the next one tries again.
"""

import logging
from datetime import UTC, datetime

from saps.adapters.persistence.db import get_engine
from saps.adapters.persistence.processing_calendar_repository import SqlHeldInvoiceRepository
from saps.application.processing_calendar import HoldReleaseService
from saps.config import Settings
from saps.ports.job_queue import JobQueuePort

log = logging.getLogger("saps.worker.hold_release")


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def run_hold_release(settings: Settings, queue: JobQueuePort) -> None:
    try:
        repository = SqlHeldInvoiceRepository(get_engine(settings.app_database_url))
        async with repository.try_lock() as got:
            if not got:  # another process releases now
                return
            service = HoldReleaseService(repository, queue, _utc_now, settings.hold_release_batch)
            await service.release_due()
    except Exception:
        log.exception("hold_release_failed")
