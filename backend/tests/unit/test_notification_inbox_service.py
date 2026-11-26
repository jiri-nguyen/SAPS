"""SAPS-24: the inbox use case with an in-memory port, and the logs written when notifications are created."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from saps.application.notifications import (
    NotificationInboxService,
    NotificationNotFoundError,
    notify_status,
)
from saps.domain.invoices import ExceptionCode, InvoiceStatus, NotificationType
from saps.domain.users import CurrentUser, Role
from saps.ports.notifications import NotificationPage
from tests.fakes import NOW

USER = CurrentUser(uuid4(), uuid4(), "member1", "Member One", Role.ACCOUNTING_MEMBER)


class MemoryInbox:
    def __init__(self, known: bool = True) -> None:
        self.known = known
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def list(
        self, tenant_id: UUID, recipient_id: UUID, unread_only: bool, page_size: int, page_token: str | None
    ) -> NotificationPage:
        self.calls.append(("list", (tenant_id, recipient_id, unread_only, page_size, page_token)))
        return NotificationPage([], None, 0)

    async def mark_read(
        self, tenant_id: UUID, recipient_id: UUID, notification_id: UUID, now: datetime
    ) -> bool:
        self.calls.append(("mark_read", (tenant_id, recipient_id, notification_id, now)))
        return self.known

    async def mark_all_read(self, tenant_id: UUID, recipient_id: UUID, now: datetime) -> None:
        self.calls.append(("mark_all_read", (tenant_id, recipient_id, now)))


async def test_the_inbox_is_scoped_to_the_caller() -> None:
    inbox = MemoryInbox()
    service = NotificationInboxService(inbox, lambda: NOW)
    notification_id = uuid4()
    await service.list(USER, True, 5, "token")
    await service.mark_read(USER, notification_id)
    await service.mark_all_read(USER)
    assert inbox.calls == [
        ("list", (USER.tenant_id, USER.user_id, True, 5, "token")),
        ("mark_read", (USER.tenant_id, USER.user_id, notification_id, NOW)),
        ("mark_all_read", (USER.tenant_id, USER.user_id, NOW)),
    ]


async def test_an_unknown_notification_is_not_found() -> None:  # EC-02
    with pytest.raises(NotificationNotFoundError):
        await NotificationInboxService(MemoryInbox(known=False), lambda: NOW).mark_read(USER, uuid4())


@dataclass
class Invoice:
    id: UUID
    tenant_id: UUID
    invoice_number: str | None = "INV-1"
    vendor_name: str | None = "Alpha"
    file_name: str = "inv.pdf"
    assigned_to: UUID | None = None


class MemoryPort:
    def __init__(self, recipients: list[UUID]) -> None:
        self.recipients = recipients
        self.added: list[tuple[list[UUID], NotificationType, str]] = []

    async def active_user_ids(self, tenant_id: UUID, role: Role) -> list[UUID]:
        return self.recipients

    async def add_notifications(
        self,
        tenant_id: UUID,
        invoice_id: UUID,
        recipients: Sequence[UUID],
        notification_type: NotificationType,
        message: str,
    ) -> None:
        self.added.append((list(recipients), notification_type, message))


async def test_creating_notifications_is_logged_without_the_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="saps.notifications")
    invoice = Invoice(uuid4(), uuid4())
    port = MemoryPort([uuid4(), uuid4()])
    await notify_status(port, invoice, InvoiceStatus.PENDING_APPROVAL, [])
    assert port.added[0][1] is NotificationType.APPROVAL_REQUESTED
    [record] = caplog.records
    assert record.getMessage() == "notifications_created"
    assert (record.__dict__["recipient_count"], record.__dict__["type"]) == (2, "APPROVAL_REQUESTED")
    assert "INV-1" not in str(record.__dict__)  # §3.7: messages are Confidential


async def test_no_recipient_is_logged_as_a_warning(caplog: pytest.LogCaptureFixture) -> None:  # EC-04
    caplog.set_level(logging.INFO, logger="saps.notifications")
    port = MemoryPort([])
    await notify_status(port, Invoice(uuid4(), uuid4()), InvoiceStatus.EXCEPTION, [ExceptionCode.EX4])
    assert port.added == []
    [record] = caplog.records
    assert (record.levelno, record.getMessage()) == (logging.WARNING, "notification_no_recipient")


@pytest.mark.parametrize(
    "status", [InvoiceStatus.POSTING, InvoiceStatus.POSTED, InvoiceStatus.PENDING_REVIEW]
)
async def test_posting_and_final_states_notify_nobody(status: InvoiceStatus) -> None:  # SAPS-49 BR-08
    port = MemoryPort([uuid4()])
    await notify_status(port, Invoice(uuid4(), uuid4()), status, [])
    assert port.added == []
