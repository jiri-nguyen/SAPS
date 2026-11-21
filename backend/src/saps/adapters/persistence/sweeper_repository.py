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
SWEEPER_LIMIT_ACTION = "RESEND_LIMIT"
STUCK_STATUSES = (InvoiceStatus.UPLOADED, InvoiceStatus.MATCHING)


class SqlSweeperRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def try_lock(self) -> bool:
        return bool(await self._session.scalar(select(func.pg_try_advisory_xact_lock(SWEEPER_LOCK_KEY))))

    async def lock_stuck(self, older_than_seconds: int, limit: int) -> list[StuckInvoice]:
        resends = (
            select(func.count())
            .select_from(InvoiceEvent)
            .where(InvoiceEvent.invoice_id == Invoice.id, InvoiceEvent.action == SWEEPER_ACTION)
            .correlate(Invoice)
            .scalar_subquery()
        )
        gave_up = (
            select(InvoiceEvent.id)
            .where(InvoiceEvent.invoice_id == Invoice.id, InvoiceEvent.action == SWEEPER_LIMIT_ACTION)
            .correlate(Invoice)
            .exists()
        )
        rows = await self._session.execute(
            select(Invoice.id, Invoice.tenant_id, Invoice.status, resends.label("resends"))
            .where(
                Invoice.status.in_(STUCK_STATUSES),
                Invoice.updated_at < func.now() - timedelta(seconds=older_than_seconds),  # database clock
                ~gave_up,  # SAPS-38 BR-05: an invoice the sweeper gave up on is never selected again
            )
            .order_by(Invoice.updated_at, Invoice.id)
            .limit(limit)
            .with_for_update(skip_locked=True, of=Invoice)
        )
        return [StuckInvoice(row.id, row.tenant_id, row.status, row.resends) for row in rows]

    async def mark_gave_up(self, invoice: StuckInvoice) -> None:
        await self._mark(invoice, SWEEPER_LIMIT_ACTION, {"resends": invoice.resends})

    async def mark_resent(self, invoice: StuckInvoice, message: str) -> None:
        await self._mark(invoice, SWEEPER_ACTION, {"message": message})

    async def _mark(self, invoice: StuckInvoice, action: str, details: dict[str, object]) -> None:
        await self._session.execute(
            update(Invoice).where(Invoice.id == invoice.id).values(updated_at=func.now())
        )
        self._session.add(
            InvoiceEvent(
                tenant_id=invoice.tenant_id,
                invoice_id=invoice.id,
                status_from=invoice.status,
                status_to=invoice.status,
                action=action,
                actor=SWEEPER_ACTOR,
                details=details,
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
