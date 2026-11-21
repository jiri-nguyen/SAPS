"""Dramatiq actors of the SAPS Worker.

Start with: `dramatiq saps.worker.actors`. `process_invoice` runs extraction and matching (SAPS-18, SAPS-19);
`rematch_invoice` runs matching again (SAPS-19). The sweeper (SAPS-37) is a timer started by a middleware.
`ping` checks the path SAPS API → SAPS Message Broker → SAPS Worker.
Failing invoice actors are retried by Dramatiq with exponential back-off (ADR-0004 S4).
"""

import logging
from functools import partial
from uuid import UUID

import dramatiq

from saps.adapters.queue.dramatiq_queue import DramatiqJobQueue
from saps.config import get_settings
from saps.logging_config import configure_logging
from saps.worker.broker import install_broker
from saps.worker.jobs import load_adapters, run_matching, run_processing
from saps.worker.sweeper import SweeperMiddleware, run_sweep

settings = get_settings()
configure_logging(settings.log_level)
broker = install_broker(settings)
broker.add_middleware(
    SweeperMiddleware(
        settings.sweeper_interval_seconds, partial(run_sweep, settings, DramatiqJobQueue(broker))
    )
)
load_adapters(settings)  # broken fixtures stop the worker here, not during a demo (SAPS-18 EC-04)
log = logging.getLogger("saps.worker")


@dramatiq.actor(max_retries=0, time_limit=settings.actor_time_limit_ms)
async def ping(correlation_id: str) -> None:
    """Smoke-test actor: logs that the worker received a message."""
    log.info("ping_received", extra={"correlation_id": correlation_id})


@dramatiq.actor(time_limit=settings.actor_time_limit_ms)
async def rematch_invoice(invoice_id: str) -> None:
    """Re-match an invoice in status Matching after a matching field changed (SAPS-19 BR-14)."""
    await run_matching(UUID(invoice_id))


@dramatiq.actor(time_limit=settings.actor_time_limit_ms)
async def process_invoice(invoice_id: str) -> None:
    """Sent by uploadInvoice (SAPS-17) and the sweeper (SAPS-37); expects status Uploaded."""
    await run_processing(UUID(invoice_id))
