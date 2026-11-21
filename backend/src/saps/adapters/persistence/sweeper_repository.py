"""SQL implementation of the sweeper port (SAPS-37); one transaction per sweep."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from saps.adapters.persistence.models import Invoice, InvoiceEvent
from saps.domain.invoices import InvoiceStatus
from saps.ports.sweeper import StuckInvoice

SWEEPER_LOCK_KEY = 3700037  # pg_try_advisory_xact_lock key shared by all SAPS Worker processes (BR-03)
SWEEPER_ACTOR = "system"
SWEEPER_ACTION = "RESEND"
STUCK_STATUSES = (InvoiceStatus.UPLOADED, InvoiceStatus.MATCHING)


class SqlSweeperRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def try_lock(self) -> bool:
        return bool(await self._session.scalar(select(func.pg_try_advisory_xact_lock(SWEEPER_LOCK_KEY))))

    async def lock_stuck(self, older_than_seconds: int, limit: int) -> list[StuckInvoice]:
        rows = await self._session.execute(
            select(Invoice.id, Invoice.tenant_id, Invoice.status)
            .where(
                Invoice.status.in_(STUCK_STATUSES),
                Invoice.updated_at < func.now() - timedelta(seconds=older_than_seconds),  # database clock
            )
            .order_by(Invoice.updated_at, Invoice.id)
            .limit(limit)
            .with_for_update(skip_locked=True, of=Invoice)
        )
        return [StuckInvoice(row.id, row.tenant_id, row.status) for row in rows]

    async def mark_resent(self, invoice: StuckInvoice, message: str) -> None:
        await self._session.execute(
            update(Invoice).where(Invoice.id == invoice.id).values(updated_at=func.now())
        )
        self._session.add(
            InvoiceEvent(
                tenant_id=invoice.tenant_id,
                invoice_id=invoice.id,
                status_from=invoice.status,
                status_to=invoice.status,
                action=SWEEPER_ACTION,
                actor=SWEEPER_ACTOR,
                details={"message": message},
            )
        )
        await self._session.flush()


class SqlSweepUnitOfWork:
    """One transaction per call; the block's end commits and releases the lock, an error rolls back."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[SqlSweeperRepository]:
        async with self._sessions() as session, session.begin():
            yield SqlSweeperRepository(session)
