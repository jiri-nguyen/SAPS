"""Notification port: recipients by role and in-app notifications (DEC-021, SAPS-24)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from saps.domain.invoices import NotificationType
from saps.domain.users import Role


class NotificationPort(Protocol):
    async def active_user_ids(self, tenant_id: UUID, role: Role) -> list[UUID]: ...

    async def add_notifications(
        self,
        tenant_id: UUID,
        invoice_id: UUID,
        recipients: Sequence[UUID],
        notification_type: NotificationType,
        message: str,
    ) -> None: ...


@dataclass(frozen=True)
class NotificationView:
    id: UUID
    type: NotificationType
    invoice_id: UUID
    message: str
    read_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class NotificationPage:
    items: Sequence[NotificationView]
    next_page_token: str | None
    unread_count: int
    """All unread notifications of the caller, not only those on this page (bell badge)."""


class NotificationInbox(Protocol):
    """What a user reads and marks (SAPS-24 BR-06); every call is scoped to the caller's tenant and id."""

    async def list(
        self, tenant_id: UUID, recipient_id: UUID, unread_only: bool, page_size: int, page_token: str | None
    ) -> NotificationPage: ...

    async def mark_read(
        self, tenant_id: UUID, recipient_id: UUID, notification_id: UUID, now: datetime
    ) -> bool:
        """False when the notification does not exist or belongs to another user (EC-02); an already read
        notification is not an error (EC-03)."""
        ...

    async def mark_all_read(self, tenant_id: UUID, recipient_id: UUID, now: datetime) -> None: ...
