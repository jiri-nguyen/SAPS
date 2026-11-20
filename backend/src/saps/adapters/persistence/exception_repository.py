"""SQL implementation of the exception handling port (SAPS-20): one transaction per operation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from saps.adapters.persistence.models import (
    Approval,
    Invoice,
    InvoiceEvent,
    InvoiceException,
    InvoiceLine,
    MatchingSettings,
)
from saps.adapters.persistence.notification_repository import SqlNotifications
from saps.domain.duplicates import normalize_invoice_number
from saps.domain.exception_handling import InvoiceChange, InvoiceData, LineData, change_details
from saps.domain.invoices import ApprovalDecision, ExceptionStatus, InvoiceStatus, MatchStatus
from saps.ports.exception_handling import InvoiceForHandling
from saps.ports.matching import OpenException

CLAIM_ACTION = "CLAIM"
RELEASE_ACTION = "RELEASE"
UPDATE_ACTION = "UPDATE_FIELDS"
RESOLVE_ACTION = "RESOLVE"
REJECT_ACTION = "REJECT"
APPROVE_ACTION = "APPROVE"


class SqlExceptionRepository(SqlNotifications):
    async def lock_invoice(self, tenant_id: UUID, invoice_id: UUID) -> InvoiceForHandling | None:
        invoice = await self._session.scalar(
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
            .options(selectinload(Invoice.lines), selectinload(Invoice.exceptions))
            .with_for_update(of=Invoice)
        )
        if invoice is None:
            return None
        return InvoiceForHandling(
            id=invoice.id,
            tenant_id=invoice.tenant_id,
            status=invoice.status,
            assigned_to=invoice.assigned_to,
            updated_at=invoice.updated_at,
            invoice_number=invoice.invoice_number,
            vendor_name=invoice.vendor_name,
            file_name=invoice.file_name,
            total_amount=invoice.total_amount,
            approval_threshold_applied=invoice.approval_threshold_applied,
            data=InvoiceData(
                vendor_code=invoice.vendor_code,
                vendor_name=invoice.vendor_name,
                invoice_number=invoice.invoice_number,
                invoice_date=invoice.invoice_date,
                subtotal_amount=invoice.subtotal_amount,
                tax_amount=invoice.tax_amount,
                total_amount=invoice.total_amount,
                lines=tuple(
                    LineData(
                        ln.line_number,
                        ln.description,
                        ln.po_number,
                        ln.po_line_number,
                        ln.quantity,
                        ln.unit_price,
                        ln.line_amount,
                    )
                    for ln in invoice.lines
                ),
            ),
            open_exceptions=tuple(
                OpenException(e.id, e.code, e.invoice_line_id)
                for e in invoice.exceptions
                if e.status is ExceptionStatus.OPEN
            ),
        )

    async def current_approval_threshold(self, tenant_id: UUID) -> Decimal:
        settings = await self._session.get_one(MatchingSettings, tenant_id)
        return settings.approval_threshold_usd

    async def claim(self, invoice: InvoiceForHandling, user_id: UUID, *, actor: str, now: datetime) -> None:
        await self._update_invoice(invoice.id, actor, assigned_to=user_id)
        self._add_event(invoice, invoice.status, CLAIM_ACTION, actor, now, None)
        await self._session.flush()

    async def release(self, invoice: InvoiceForHandling, *, actor: str, now: datetime) -> None:
        await self._update_invoice(invoice.id, actor, assigned_to=None)
        self._add_event(invoice, invoice.status, RELEASE_ACTION, actor, now, None)
        await self._session.flush()

    async def save_update(
        self,
        invoice: InvoiceForHandling,
        change: InvoiceChange,
        *,
        status: InvoiceStatus,
        user_id: UUID,
        actor: str,
        now: datetime,
    ) -> None:
        values: dict[str, Any] = {name: new for name, (_, new) in change.header.items()}
        if "invoice_number" in values:
            values["invoice_number_normalized"] = normalize_invoice_number(values["invoice_number"])
        await self._update_invoice(invoice.id, actor, status=status, **values)
        if change.lines is not None:
            await self._replace_lines(invoice, change.lines[1], user_id=user_id, actor=actor, now=now)
        self._add_event(invoice, status, UPDATE_ACTION, actor, now, change_details(change))
        await self._session.flush()

    async def resolve(
        self,
        invoice: InvoiceForHandling,
        *,
        status: InvoiceStatus,
        requires_approval: bool,
        threshold: Decimal,
        user_id: UUID,
        actor: str,
        now: datetime,
    ) -> None:
        await self._session.execute(
            update(InvoiceException)
            .where(InvoiceException.invoice_id == invoice.id, InvoiceException.status == ExceptionStatus.OPEN)
            .values(status=ExceptionStatus.RESOLVED, resolved_by=user_id, resolved_at=now, updated_by=actor)
        )
        await self._update_invoice(
            invoice.id,
            actor,
            status=status,
            requires_approval=requires_approval,
            approval_threshold_applied=threshold,
            assigned_to=None,
        )
        details = {"codes": sorted({c.value for c in invoice.open_codes}), "threshold": str(threshold)}
        self._add_event(invoice, status, RESOLVE_ACTION, actor, now, details)
        await self._session.flush()

    async def reject(self, invoice: InvoiceForHandling, reason: str, *, actor: str, now: datetime) -> None:
        await self._update_invoice(
            invoice.id, actor, status=InvoiceStatus.REJECTED, rejected_reason=reason, assigned_to=None
        )
        self._add_event(invoice, InvoiceStatus.REJECTED, REJECT_ACTION, actor, now, {"reason": reason})
        await self._session.flush()

    async def record_decision(
        self,
        invoice: InvoiceForHandling,
        decision: ApprovalDecision,
        comment: str | None,
        *,
        status: InvoiceStatus,
        user_id: UUID,
        actor: str,
        now: datetime,
    ) -> None:
        self._session.add(
            Approval(
                tenant_id=invoice.tenant_id,
                invoice_id=invoice.id,
                decided_by=user_id,
                decision=decision,
                comment=comment,
                decided_at=now,
                created_by=actor,
                updated_by=actor,
            )
        )
        values: dict[str, Any] = {"status": status}
        if decision is ApprovalDecision.REJECTED:
            values["rejected_reason"] = comment
        await self._update_invoice(invoice.id, actor, **values)
        action = APPROVE_ACTION if decision is ApprovalDecision.APPROVED else REJECT_ACTION
        details = {"decision": decision.value, "comment": comment}
        self._add_event(invoice, status, action, actor, now, details)
        await self._session.flush()

    # --- helpers -----------------------------------------------------------------------------------

    async def _update_invoice(self, invoice_id: UUID, actor: str, **values: Any) -> None:
        # Every operation changes the row, so `updated_at` and with it the ETag move on (EC-02).
        await self._session.execute(
            update(Invoice).where(Invoice.id == invoice_id).values(updated_by=actor, **values)
        )

    def _add_event(
        self,
        invoice: InvoiceForHandling,
        status_to: InvoiceStatus,
        action: str,
        actor: str,
        now: datetime,
        details: dict[str, Any] | None,
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

    async def _replace_lines(
        self,
        invoice: InvoiceForHandling,
        new_lines: tuple[LineData, ...],
        *,
        user_id: UUID,
        actor: str,
        now: datetime,
    ) -> None:
        """`lines` replaces all lines (BR-04). Lines are matched by number, so their IDs and exceptions stay
        valid; exceptions of a removed line are resolved (by the user) and detached from it."""
        session = self._session
        existing = {
            ln.line_number: ln
            for ln in (
                await session.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id))
            ).scalars()
        }
        for data in new_lines:
            fields = {
                "description": data.description,
                "po_number": data.po_number,
                "po_line_number": data.po_line_number,
                "quantity": data.quantity,
                "unit_price": data.unit_price,
                "line_amount": data.line_amount,
                "updated_by": actor,
            }
            line = existing.pop(data.line_number, None)
            if line is None:
                session.add(
                    InvoiceLine(
                        tenant_id=invoice.tenant_id,
                        invoice_id=invoice.id,
                        line_number=data.line_number,
                        match_status=MatchStatus.NOT_MATCHED,
                        created_by=actor,
                        **fields,
                    )
                )
            else:
                for name, value in fields.items():
                    setattr(line, name, value)
        removed = [ln.id for ln in existing.values()]  # numbers that are no longer sent
        if removed:
            await session.execute(
                update(InvoiceException)
                .where(
                    InvoiceException.invoice_line_id.in_(removed),
                    InvoiceException.status == ExceptionStatus.OPEN,
                )
                .values(
                    status=ExceptionStatus.RESOLVED, resolved_by=user_id, resolved_at=now, updated_by=actor
                )
            )
            await session.execute(
                update(InvoiceException)
                .where(InvoiceException.invoice_line_id.in_(removed))
                .values(invoice_line_id=None)
            )
            await session.execute(delete(InvoiceLine).where(InvoiceLine.id.in_(removed)))


class SqlExceptionUnitOfWork:
    """One transaction per call; the block's end commits, an error rolls back (ports.exception_handling)."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[SqlExceptionRepository]:
        async with self._sessions() as session, session.begin():
            yield SqlExceptionRepository(session)
