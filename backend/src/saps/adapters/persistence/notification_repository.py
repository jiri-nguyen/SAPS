"""SQL implementation of the notification port (DEC-021); base of the job repositories."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saps.adapters.persistence.models import Notification, UserAccount
from saps.domain.invoices import NotificationType
from saps.domain.users import Role


class SqlNotifications:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_user_ids(self, tenant_id: UUID, role: Role) -> list[UUID]:
        rows = await self._session.execute(
            select(UserAccount.id)
            .where(UserAccount.tenant_id == tenant_id, UserAccount.role == role, UserAccount.is_active)
            .order_by(UserAccount.username)
        )
        return list(rows.scalars())

    async def add_notifications(
        self,
        tenant_id: UUID,
        invoice_id: UUID,
        recipients: Sequence[UUID],
        notification_type: NotificationType,
        message: str,
    ) -> None:
        self._session.add_all(
            Notification(
                tenant_id=tenant_id,
                recipient_id=recipient,
                invoice_id=invoice_id,
                type=notification_type,
                message=message,
            )
            for recipient in recipients
        )
        await self._session.flush()
