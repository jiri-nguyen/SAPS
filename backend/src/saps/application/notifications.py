"""Notifications when an invoice reaches a status (DEC-021; SAPS-19 BR-13, SAPS-18 BR-03, SAPS-20 BR-10)."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from saps.domain.invoices import ExceptionCode, InvoiceStatus, NotificationType
from saps.domain.users import Role
from saps.ports.notifications import NotificationPort


class NamedInvoice(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def tenant_id(self) -> UUID: ...
    @property
    def invoice_number(self) -> str | None: ...
    @property
    def vendor_name(self) -> str | None: ...
    @property
    def file_name(self) -> str: ...
    @property
    def assigned_to(self) -> UUID | None: ...


def invoice_display_name(invoice: NamedInvoice) -> str:
    """SAPS-24 BR-04: invoice number and vendor name, or the file name before extraction."""
    if invoice.invoice_number and invoice.vendor_name:
        return f"Invoice {invoice.invoice_number} from {invoice.vendor_name}"
    if invoice.invoice_number:
        return f"Invoice {invoice.invoice_number}"
    return f"Invoice file {invoice.file_name}"


async def notify_status(
    port: NotificationPort, invoice: NamedInvoice, status: InvoiceStatus, codes: Sequence[ExceptionCode]
) -> None:
    """Exception → Accounting Members (only the claimant of a claimed invoice); PendingApproval → Accounting
    Managers; PendingReview → Accounting Members."""
    name = invoice_display_name(invoice)
    if status is InvoiceStatus.EXCEPTION:
        kind = NotificationType.EXCEPTION_RAISED
        message = f"{name} has exceptions: {', '.join(c.value for c in codes)}."
        if invoice.assigned_to is not None:
            recipients = [invoice.assigned_to]
        else:
            recipients = await port.active_user_ids(invoice.tenant_id, Role.ACCOUNTING_MEMBER)
    elif status is InvoiceStatus.PENDING_APPROVAL:
        kind = NotificationType.APPROVAL_REQUESTED
        message = f"{name} needs approval."
        recipients = await port.active_user_ids(invoice.tenant_id, Role.ACCOUNTING_MANAGER)
    else:
        kind = NotificationType.REVIEW_REQUESTED
        message = f"{name} is ready for final review."
        recipients = await port.active_user_ids(invoice.tenant_id, Role.ACCOUNTING_MEMBER)
    if recipients:
        await port.add_notifications(invoice.tenant_id, invoice.id, recipients, kind, message)
