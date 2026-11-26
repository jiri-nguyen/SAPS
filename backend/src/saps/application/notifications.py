"""Notifications when an invoice reaches a status (DEC-021; SAPS-19 BR-13, SAPS-18 BR-03, SAPS-20 BR-10)."""

import logging
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from saps.domain.invoices import ExceptionCode, InvoiceStatus, NotificationType
from saps.domain.users import CurrentUser, Role
from saps.ports.notifications import NotificationInbox, NotificationPage, NotificationPort

log = logging.getLogger("saps.notifications")


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
    Managers. Posting and Posted notify nobody: there is no final review any more (SAPS-49 BR-08, DEC-063)."""
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
        return
    if not recipients:  # EC-04
        log.warning("notification_no_recipient", extra={"invoice_id": str(invoice.id), "type": kind.value})
        return
    await port.add_notifications(invoice.tenant_id, invoice.id, recipients, kind, message)
    # The message names the invoice (Confidential), so it is not logged (SAPS-24 §3.7).
    log.info(
        "notifications_created",
        extra={"invoice_id": str(invoice.id), "type": kind.value, "recipient_count": len(recipients)},
    )


class NotificationNotFoundError(Exception):
    """The notification does not exist for the caller (answers 404, EC-02)."""


class NotificationInboxService:
    """The caller's own notifications: list with the unread count, mark one or all as read (SAPS-24 BR-06)."""

    def __init__(self, inbox: NotificationInbox, clock: Callable[[], datetime]) -> None:
        self._inbox = inbox
        self._clock = clock

    async def list(
        self, user: CurrentUser, unread_only: bool, page_size: int, page_token: str | None
    ) -> NotificationPage:
        return await self._inbox.list(user.tenant_id, user.user_id, unread_only, page_size, page_token)

    async def mark_read(self, user: CurrentUser, notification_id: UUID) -> None:
        if not await self._inbox.mark_read(user.tenant_id, user.user_id, notification_id, self._clock()):
            raise NotificationNotFoundError(notification_id)

    async def mark_all_read(self, user: CurrentUser) -> None:
        await self._inbox.mark_all_read(user.tenant_id, user.user_id, self._clock())
