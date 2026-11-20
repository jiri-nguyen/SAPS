"""SQL implementation of the matching port (SAPS-19); runs in the actor's transaction (ADR-0004, TD-01)."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text, tuple_, update
from sqlalchemy.orm import selectinload

from saps.adapters.persistence.models import (
    Invoice,
    InvoiceEvent,
    InvoiceException,
    InvoiceLine,
    MatchingSettings,
)
from saps.adapters.persistence.notification_repository import SqlNotifications
from saps.domain.duplicates import COMPARED_STATUSES, DuplicateCandidate
from saps.domain.invoices import ExceptionStatus, InvoiceStatus
from saps.domain.matching import InvoiceToMatch, LineToMatch, MatchingRules, PoLineKey
from saps.ports.matching import InvoiceForMatching, MatchUpdate, OpenException

# DEC-023: invoices whose quantities are already taken from the PO line.
INVOICED_STATUSES = (InvoiceStatus.PENDING_APPROVAL, InvoiceStatus.PENDING_REVIEW, InvoiceStatus.COMPLETED)


class SqlMatchingRepository(SqlNotifications):
    async def lock_invoice(self, invoice_id: UUID) -> InvoiceForMatching | None:
        invoice = (
            await self._session.execute(
                select(Invoice)
                .where(Invoice.id == invoice_id)
                .options(selectinload(Invoice.lines), selectinload(Invoice.exceptions))
                .with_for_update(of=Invoice)
            )
        ).scalar_one_or_none()
        if invoice is None:
            return None
        return InvoiceForMatching(
            id=invoice.id,
            tenant_id=invoice.tenant_id,
            status=invoice.status,
            invoice_number=invoice.invoice_number,
            vendor_name=invoice.vendor_name,
            file_name=invoice.file_name,
            assigned_to=invoice.assigned_to,
            invoice=InvoiceToMatch(
                vendor_code=invoice.vendor_code,
                total_amount=invoice.total_amount,
                lines=[
                    LineToMatch(
                        ln.id, ln.line_number, ln.po_number, ln.po_line_number, ln.quantity, ln.unit_price
                    )
                    for ln in invoice.lines
                ],
            ),
            open_exceptions=tuple(
                OpenException(e.id, e.code, e.invoice_line_id)
                for e in invoice.exceptions
                if e.status is ExceptionStatus.OPEN
            ),
        )

    async def get_rules(self, tenant_id: UUID) -> MatchingRules:
        settings = await self._session.get_one(MatchingSettings, tenant_id)
        return MatchingRules(settings.price_tolerance_usd, settings.approval_threshold_usd)

    async def lock_po_lines(self, tenant_id: UUID, keys: Sequence[PoLineKey]) -> None:
        # Sorted, so two invoices sharing PO lines always lock in the same order (no deadlock).
        for po_number, po_line_number in sorted(keys):
            await self._session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": f"po-line:{tenant_id}:{po_number}:{po_line_number}"},
            )

    async def lock_duplicate_key(self, tenant_id: UUID, vendor_code: str, invoice_number: str) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"dup:{tenant_id}:{vendor_code}:{invoice_number}"},
        )

    async def find_duplicates(
        self, tenant_id: UUID, vendor_code: str, invoice_number: str, exclude_invoice_id: UUID
    ) -> list[DuplicateCandidate]:
        rows = await self._session.execute(
            select(Invoice.id, Invoice.invoice_number, Invoice.status)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.vendor_code == vendor_code,
                Invoice.invoice_number_normalized == invoice_number,
                Invoice.status.in_(COMPARED_STATUSES),
                Invoice.id != exclude_invoice_id,
            )
            .order_by(Invoice.created_at)
        )
        return [DuplicateCandidate(i, number, status) for i, number, status in rows]

    async def already_invoiced(
        self, tenant_id: UUID, keys: Sequence[PoLineKey], exclude_invoice_id: UUID
    ) -> dict[PoLineKey, Decimal]:
        if not keys:
            return {}
        rows = await self._session.execute(
            select(InvoiceLine.po_number, InvoiceLine.po_line_number, func.sum(InvoiceLine.quantity))
            .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
            .where(
                InvoiceLine.tenant_id == tenant_id,
                tuple_(InvoiceLine.po_number, InvoiceLine.po_line_number).in_(list(keys)),
                Invoice.status.in_(INVOICED_STATUSES),
                Invoice.id != exclude_invoice_id,
            )
            .group_by(InvoiceLine.po_number, InvoiceLine.po_line_number)
        )
        return {(po, line): total for po, line, total in rows if po and line is not None and total}

    async def save_match(
        self, invoice: InvoiceForMatching, update_: MatchUpdate, *, actor: str, action: str, now: datetime
    ) -> None:
        session = self._session
        for line_id, result in update_.lines.items():
            await session.execute(
                update(InvoiceLine)
                .where(InvoiceLine.id == line_id)
                .values(
                    match_status=result.match_status,
                    po_unit_price=result.po_unit_price,
                    expected_quantity=result.expected_quantity,
                    updated_by=actor,
                )
            )
        if update_.resolved:
            await session.execute(
                update(InvoiceException)
                .where(InvoiceException.id.in_(update_.resolved))
                .values(status=ExceptionStatus.RESOLVED, resolved_by=None, resolved_at=now, updated_by=actor)
            )
        for exception_id, message in update_.messages.items():
            await session.execute(
                update(InvoiceException)
                .where(InvoiceException.id == exception_id)
                .values(message=message, updated_by=actor)
            )
        session.add_all(
            InvoiceException(
                tenant_id=invoice.tenant_id,
                invoice_id=invoice.id,
                invoice_line_id=new.line_id,
                code=new.code,
                message=new.message,
                created_by=actor,
                updated_by=actor,
            )
            for new in update_.opened
        )
        values: dict[str, Any] = {
            "status": update_.status,
            "invoice_type": update_.invoice_type,
            "requires_approval": update_.requires_approval,
            "price_tolerance_applied": update_.rules.price_tolerance,
            "approval_threshold_applied": update_.rules.approval_threshold,
            "updated_by": actor,
        }
        if update_.status is not InvoiceStatus.EXCEPTION:
            values["assigned_to"] = None  # SAPS-20 BR-09: the claim ends when the invoice leaves Exception
        await session.execute(update(Invoice).where(Invoice.id == invoice.id).values(**values))
        session.add(
            InvoiceEvent(
                tenant_id=invoice.tenant_id,
                invoice_id=invoice.id,
                status_from=invoice.status,
                status_to=update_.status,
                action=action,
                actor=actor,
                details=dict(update_.event_details),
                occurred_at=now,
                created_by=actor,
                updated_by=actor,
            )
        )
        await session.flush()
