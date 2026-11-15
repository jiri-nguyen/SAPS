"""SAPS-34 spike: Dramatiq broker + async actors using SQLAlchemy async."""
import asyncio
import logging
import os
import uuid

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO

from spike.db import Invoice, InvoiceEvent, Marker, session_factory

log = logging.getLogger("spike.tasks")

broker = RedisBroker(
    url="redis://localhost:56379/0",
    heartbeat_timeout=int(os.environ.get("HEARTBEAT_TIMEOUT_MS", "60000")),
    maintenance_chance=int(os.environ.get("MAINTENANCE_CHANCE", "1000")),
)
broker.add_middleware(AsyncIO())
dramatiq.set_broker(broker)

ACTOR = f"pid{os.getpid()}"


@dramatiq.actor(max_retries=3, time_limit=60_000)
async def process_invoice(invoice_id: str, work_seconds: float = 0.2) -> None:
    """Idempotent: lock the row, do nothing unless the invoice is still UPLOADED."""
    Session = session_factory()
    async with Session() as s, s.begin():
        inv = await s.get(Invoice, uuid.UUID(invoice_id), with_for_update=True)
        if inv is None or inv.status != "UPLOADED":
            log.info("skip %s (status=%s)", invoice_id, inv.status if inv else None)
            return
        inv.status = "MATCHING"
        await s.flush()
        await asyncio.sleep(work_seconds)          # stands in for extraction + matching
        inv.status = "PENDING_REVIEW"
        s.add(InvoiceEvent(invoice_id=inv.id, action="PROCESSED", actor=f"pid{os.getpid()}"))
    log.info("processed %s", invoice_id)


@dramatiq.actor(max_retries=0, time_limit=2_000)
async def slow_actor(tag: str, seconds: float) -> None:
    """Exceeds its 2 s time limit; checks cancellation and transaction rollback."""
    Session = session_factory()
    async with Session() as s, s.begin():
        s.add(Marker(tag=tag, stage="started"))           # committed before the slow part
    try:
        async with Session() as s, s.begin():
            s.add(Marker(tag=tag, stage="in-transaction"))  # must be rolled back on cancel
            await s.flush()
            await asyncio.sleep(seconds)
            s.add(Marker(tag=tag, stage="finished"))
    except asyncio.CancelledError:
        with open(os.environ.get("CANCEL_LOG", "cancel.log"), "a") as f:
            f.write(f"{tag} cancelled in pid{os.getpid()}\n")
        raise
