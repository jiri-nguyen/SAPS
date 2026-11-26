"""SQL implementation of the processing port (SAPS-18); shares the job's session with matching."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update

from saps.adapters.persistence.models import Invoice, InvoiceEvent, InvoiceException, InvoiceLine
from saps.adapters.persistence.notification_repository import SqlNotifications
from saps.adapters.persistence.processing_calendar_repository import calendar_snapshot
from saps.domain.duplicates import normalize_invoice_number
from saps.domain.extraction import ExtractedInvoice
from saps.domain.invoices import ExceptionCode, InvoiceStatus
from saps.ports.extraction import StoredFile
from saps.ports.processing import InvoiceToProcess
from saps.ports.processing_calendar import CalendarSnapshot

EXTRACT_ACTION = "EXTRACT"
HOLD_ACTION = "HOLD"  # SAPS-52


class SqlProcessingRepository(SqlNotifications):
    async def lock_invoice(self, invoice_id: UUID) -> InvoiceToProcess | None:
        invoice = await self._session.scalar(
            select(Invoice).where(Invoice.id == invoice_id).with_for_update()
        )
        if invoice is None:
            return None
        return InvoiceToProcess(
            id=invoice.id,
            tenant_id=invoice.tenant_id,
            status=invoice.status,
            file=StoredFile(invoice.file_sha256, invoice.file_storage_key, invoice.file_content_type),
            file_name=invoice.file_name,
            assigned_to=invoice.assigned_to,
            invoice_number=invoice.invoice_number,
            vendor_name=invoice.vendor_name,
            released_from_hold_at=invoice.released_from_hold_at,
        )

    async def calendar_of(self, tenant_id: UUID) -> CalendarSnapshot:
        return await calendar_snapshot(self._session, tenant_id)

    async def hold(self, invoice: InvoiceToProcess, *, actor: str, now: datetime) -> None:
        await self._session.execute(
            update(Invoice)
            .where(Invoice.id == invoice.id)
            .values(status=InvoiceStatus.ON_HOLD, updated_by=actor)
        )
        self._add_event(
            invoice, InvoiceStatus.ON_HOLD, {"reason": "closed day"}, actor, now, action=HOLD_ACTION
        )
        await self._session.flush()

    async def save_extraction(
        self, invoice: InvoiceToProcess, extracted: ExtractedInvoice, *, actor: str, now: datetime
    ) -> None:
        await self._session.execute(
            update(Invoice)
            .where(Invoice.id == invoice.id)
            .values(
                status=InvoiceStatus.MATCHING,
                vendor_code=extracted.vendor_code,
                vendor_name=extracted.vendor_name,
                invoice_number=extracted.invoice_number,
                invoice_number_normalized=normalize_invoice_number(extracted.invoice_number),  # SAPS-23
                invoice_date=extracted.invoice_date,
                currency=extracted.currency,
                subtotal_amount=extracted.subtotal_amount,
                tax_amount=extracted.tax_amount,
                total_amount=extracted.total_amount,
                updated_by=actor,
            )
        )
        self._session.add_all(
            InvoiceLine(
                tenant_id=invoice.tenant_id,
                invoice_id=invoice.id,
                line_number=line.line_number,
                description=line.description,
                po_number=line.po_number,
                po_line_number=line.po_line_number,
                quantity=line.quantity,
                unit_price=line.unit_price,
                line_amount=line.line_amount,
                do_number=line.do_number,
                created_by=actor,
                updated_by=actor,
            )
            for line in extracted.lines
        )
        self._add_event(
            invoice, InvoiceStatus.MATCHING, {"found": True, "lineCount": len(extracted.lines)}, actor, now
        )
        await self._session.flush()

    async def raise_unreadable(
        self, invoice: InvoiceToProcess, reason: str, *, actor: str, now: datetime
    ) -> None:
        await self._session.execute(
            update(Invoice)
            .where(Invoice.id == invoice.id)
            .values(status=InvoiceStatus.EXCEPTION, updated_by=actor)
        )
        self._session.add(
            InvoiceException(
                tenant_id=invoice.tenant_id,
                invoice_id=invoice.id,
                invoice_line_id=None,
                code=ExceptionCode.EX1,
                message=f"Invoice unreadable: {reason}",
                created_by=actor,
                updated_by=actor,
            )
        )
        self._add_event(invoice, InvoiceStatus.EXCEPTION, {"found": False, "reason": reason}, actor, now)
        await self._session.flush()

    def _add_event(
        self,
        invoice: InvoiceToProcess,
        status_to: InvoiceStatus,
        details: dict[str, object],
        actor: str,
        now: datetime,
        action: str = EXTRACT_ACTION,
    ) -> None:
        self._session.add(
            InvoiceEvent(
                tenant_id=invoice.tenant_id,
                invoice_id=invoice.id,
                status_from=invoice.status,
                status_to=status_to,
                action=action,
                actor=actor,
                details=details,
                occurred_at=now,
                created_by=actor,
                updated_by=actor,
            )
        )
