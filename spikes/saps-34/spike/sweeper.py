"""SAPS-34 spike: periodic sweeper re-sending stuck invoices, guarded by a PostgreSQL advisory lock.

Run several instances to simulate several SAPS Worker containers: only one may sweep per tick.
"""
import asyncio
import logging
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

from spike.db import get_engine
from spike.tasks import process_invoice

SWEEPER_LOCK_ID = 340034
STUCK_AFTER = "3 seconds"
NAME = sys.argv[1] if len(sys.argv) > 1 else "sweeper"
logging.basicConfig(level=logging.INFO, format=f"%(asctime)s {NAME} %(message)s")
log = logging.getLogger("sweeper")


async def sweep() -> None:
    async with get_engine().begin() as conn:
        got = await conn.scalar(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": SWEEPER_LOCK_ID})
        if not got:
            log.info("tick: lock held by another instance -> skip")
            return
        rows = (await conn.execute(text(
            f"SELECT id FROM invoice WHERE status IN ('UPLOADED','MATCHING') "
            f"AND updated_at < now() - interval '{STUCK_AFTER}' FOR UPDATE SKIP LOCKED"))).all()
        for (inv_id,) in rows:
            process_invoice.send(str(inv_id))
            await conn.execute(text("UPDATE invoice SET updated_at = now() WHERE id = :i"), {"i": inv_id})
            await conn.execute(text(
                "INSERT INTO invoice_event (invoice_id, action, actor) VALUES (:i, 'SWEEPER_RESENT', :a)"),
                {"i": inv_id, "a": NAME})
        log.info("tick: lock acquired, re-sent %d invoice(s)", len(rows))
        await asyncio.sleep(1.0)  # keep the lock a moment so instances overlap


async def main() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(sweep, "interval", seconds=2, max_instances=1, coalesce=True)
    scheduler.start()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
