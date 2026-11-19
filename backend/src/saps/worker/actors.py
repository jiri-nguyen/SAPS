"""Dramatiq actors of the SAPS Worker.

Start with: `dramatiq saps.worker.actors`. `rematch_invoice` runs matching (SAPS-19); `process_invoice`
and the sweeper are added by SAPS-18 and SAPS-20.
`ping` checks the path SAPS API → SAPS Message Broker → SAPS Worker.
Failing invoice actors are retried by Dramatiq with exponential back-off (ADR-0004 S4).
"""

import logging
from uuid import UUID

import dramatiq

from saps.config import get_settings
from saps.logging_config import configure_logging
from saps.worker.broker import install_broker
from saps.worker.jobs import run_matching

settings = get_settings()
configure_logging(settings.log_level)
broker = install_broker(settings)
log = logging.getLogger("saps.worker")


@dramatiq.actor(max_retries=0, time_limit=settings.actor_time_limit_ms)
async def ping(correlation_id: str) -> None:
    """Smoke-test actor: logs that the worker received a message."""
    log.info("ping_received", extra={"correlation_id": correlation_id})


@dramatiq.actor(time_limit=settings.actor_time_limit_ms)
async def rematch_invoice(invoice_id: str) -> None:
    """Re-match an invoice in status Matching after a matching field changed (SAPS-19 BR-14)."""
    await run_matching(UUID(invoice_id))
