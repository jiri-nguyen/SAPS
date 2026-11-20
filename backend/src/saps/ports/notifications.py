"""Notification port: recipients by role and in-app notifications (DEC-021, SAPS-24)."""

from collections.abc import Sequence
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
