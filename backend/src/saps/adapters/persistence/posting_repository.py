"""SQL implementation of the posting port (SAPS-49); each unit of work is one transaction (ADR-0013)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from saps.adapters.persistence.models import Invoice, InvoiceEvent, Tenant
from saps.adapters.persistence.processing_calendar_repository import calendar_snapshot
from saps.domain.invoices import InvoiceStatus
from saps.ports.erp_posting import PostingLine, PostingRequest
from saps.ports.posting import InvoiceToPost
from saps.ports.processing_calendar import CalendarSnapshot

SYSTEM_ACTOR = "system"
HOLD_ACTION = "POSTING_HOLD"
POST_ACTION = "POST"


class SqlPostingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_invoice(self, invoice_id: UUID) -> InvoiceToPost | None:
        invoice = (
            await self._session.execute(
                select(Invoice)
                .where(Invoice.id == invoice_id)
                .options(selectinload(Invoice.lines))
                .with_for_update(of=Invoice)
            )
        ).scalar_one_or_none()
        if invoice is None:
            return None
        company_code = await self._session.scalar(select(Tenant.code).where(Tenant.id == invoice.tenant_id))
        request = PostingRequest(
            invoice_id=invoice.id,
            company_code=company_code or "",
            vendor_code=invoice.vendor_code,
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date,
            currency=invoice.currency,
            subtotal_amount=invoice.subtotal_amount,
            tax_amount=invoice.tax_amount,
            total_amount=invoice.total_amount,
            lines=[
                PostingLine(
                    ln.line_number,
                    ln.po_number,
                    ln.po_line_number,
                    ln.matched_do_number,
                    ln.quantity,
                    ln.unit_price,
                    ln.line_amount,
                )
                for ln in sorted(invoice.lines, key=lambda line: line.line_number)
            ],
        )
        return InvoiceToPost(invoice.id, invoice.tenant_id, invoice.status, invoice.posting_held_at, request)

    async def calendar_of(self, tenant_id: UUID) -> CalendarSnapshot:
        return await calendar_snapshot(self._session, tenant_id)

    async def hold(self, invoice: InvoiceToPost, *, now: datetime) -> bool:
        if invoice.posting_held_at is not None:
            return False
        await self._session.execute(
            update(Invoice)
            .where(Invoice.id == invoice.id)
            .values(posting_held_at=now, updated_by=SYSTEM_ACTOR)
        )
        self._add_event(invoice, InvoiceStatus.POSTING, HOLD_ACTION, now, None)
        await self._session.flush()
        return True

    async def mark_posted(self, invoice: InvoiceToPost, document_number: str, *, now: datetime) -> None:
        await self._session.execute(
            update(Invoice)
            .where(Invoice.id == invoice.id)
            .values(
                status=InvoiceStatus.POSTED,
                erp_document_number=document_number,
                posted_at=now,
                posting_held_at=None,
                updated_by=SYSTEM_ACTOR,
            )
        )
        self._add_event(invoice, InvoiceStatus.POSTED, POST_ACTION, now, {"documentNumber": document_number})
        await self._session.flush()

    def _add_event(
        self,
        invoice: InvoiceToPost,
        status_to: InvoiceStatus,
        action: str,
        now: datetime,
        details: dict[str, object] | None,
    ) -> None:
        self._session.add(
            InvoiceEvent(
                tenant_id=invoice.tenant_id,
                invoice_id=invoice.id,
                status_from=invoice.status,
                status_to=status_to,
                action=action,
                actor=SYSTEM_ACTOR,
                details=details,
                occurred_at=now,
                created_by=SYSTEM_ACTOR,
                updated_by=SYSTEM_ACTOR,
            )
        )


class SqlPostingUnitOfWork:
    """One transaction per call; the block's end commits and releases the lock, an error rolls back."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[SqlPostingRepository]:
        async with self._sessions() as session, session.begin():
            yield SqlPostingRepository(session)
