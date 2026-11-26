"""Dramatiq actors of the SAPS Worker.

Start with: `dramatiq saps.worker.actors`. `process_invoice` runs extraction and matching (SAPS-18, SAPS-19);
`rematch_invoice` runs matching again (SAPS-19). The sweeper (SAPS-37), the mail intake (SAPS-45) and
the release of held invoices (SAPS-52) are timers started by middlewares.
`ping` checks the path SAPS API → SAPS Message Broker → SAPS Worker.
Failing invoice actors are retried by Dramatiq with exponential back-off (ADR-0004 S4); after the last
retry of `process_invoice`, `process_invoice_failed` raises EX1 (SAPS-38).
"""

import logging
from functools import partial
from typing import Any
from uuid import UUID

import dramatiq

from saps.adapters.queue.dramatiq_queue import DramatiqJobQueue
from saps.application.processing import describe_failure
from saps.config import get_settings
from saps.logging_config import configure_logging
from saps.worker.broker import install_broker
from saps.worker.hold_release import run_hold_release
from saps.worker.jobs import load_adapters, run_failure, run_matching, run_processing
from saps.worker.mail_intake import build_mailbox, run_mail_intake
from saps.worker.sweeper import SweeperMiddleware, run_sweep
from saps.worker.timer import TimerMiddleware

settings = get_settings()
configure_logging(settings.log_level)
broker = install_broker(settings)
broker.add_middleware(
    SweeperMiddleware(
        settings.sweeper_interval_seconds, partial(run_sweep, settings, DramatiqJobQueue(broker))
    )
)
if settings.mail_adapter != "none":  # SAPS-45: one more timer, read like the sweeper's
    broker.add_middleware(
        TimerMiddleware(
            "mail-intake",
            settings.mail_poll_seconds,
            partial(run_mail_intake, settings, DramatiqJobQueue(broker), build_mailbox(settings)),
        )
    )
broker.add_middleware(  # SAPS-52: held invoices are released when the company is open again
    TimerMiddleware(
        "hold-release",
        settings.hold_release_seconds,
        partial(run_hold_release, settings, DramatiqJobQueue(broker)),
    )
)
load_adapters(settings)  # broken fixtures stop the worker here, not during a demo (SAPS-18 EC-04)
log = logging.getLogger("saps.worker")


@dramatiq.actor(max_retries=0, time_limit=settings.actor_time_limit_ms)
async def ping(correlation_id: str) -> None:
    """Smoke-test actor: logs that the worker received a message."""
    log.info("ping_received", extra={"correlation_id": correlation_id})


@dramatiq.actor(time_limit=settings.actor_time_limit_ms)
async def rematch_invoice(invoice_id: str, tenant_id: str | None = None) -> None:
    """Re-match an invoice in status Matching after a matching field changed (SAPS-19 BR-14).

    `tenant_id` is the invoice's company (SAPS-41); messages sent before SAPS-41 have none (EC-05)."""
    await run_matching(UUID(invoice_id), _tenant(tenant_id))


@dramatiq.actor(
    time_limit=settings.actor_time_limit_ms,
    max_retries=settings.process_invoice_max_retries,
    min_backoff=settings.process_invoice_min_backoff_ms,
    max_backoff=settings.process_invoice_max_backoff_ms,
    on_retry_exhausted="process_invoice_failed",
)
async def process_invoice(invoice_id: str, tenant_id: str | None = None) -> None:
    """Sent by uploadInvoice (SAPS-17) and the sweeper (SAPS-37); expects status Uploaded."""
    await run_processing(UUID(invoice_id), _tenant(tenant_id))


@dramatiq.actor(max_retries=0, time_limit=settings.actor_time_limit_ms)
async def process_invoice_failed(message_data: dict[str, Any], retry_data: dict[str, Any]) -> None:
    """Sent once after the last retry of `process_invoice` failed (SAPS-38 BR-01).

    Dramatiq passes the failed message; its `options["traceback"]` holds the last error (BR-02).
    """
    args = message_data["args"]
    invoice_id = UUID(str(args[0]))
    reason = describe_failure(str(message_data.get("options", {}).get("traceback", "")))
    await run_failure(invoice_id, reason, _tenant(args[1] if len(args) > 1 else None))


def _tenant(tenant_id: str | None) -> UUID | None:
    return None if tenant_id is None else UUID(str(tenant_id))
