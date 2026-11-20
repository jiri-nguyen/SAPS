"""SQL implementation of the notification inbox (SAPS-24); runs in the request's transaction."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from saps.adapters.persistence.invoice_repository import MAX_PAGE_SIZE, decode_token, encode_token
from saps.adapters.persistence.models import Notification
from saps.ports.notifications import NotificationPage, NotificationView


class SqlNotificationInbox:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, tenant_id: UUID, recipient_id: UUID, unread_only: bool, page_size: int, page_token: str | None
    ) -> NotificationPage:
        mine = (Notification.tenant_id == tenant_id, Notification.recipient_id == recipient_id)
        query = select(Notification).where(*mine)
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        if page_token is not None:
            query = query.where(
                tuple_(Notification.created_at, Notification.id) < tuple_(*decode_token(page_token))
            )
        size = min(max(page_size, 1), MAX_PAGE_SIZE)
        rows = list(
            (
                await self._session.execute(
                    query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(size + 1)
                )
            ).scalars()
        )
        more = len(rows) > size
        rows = rows[:size]
        unread = await self._session.scalar(
            select(func.count()).select_from(Notification).where(*mine, Notification.read_at.is_(None))
        )
        return NotificationPage(
            [NotificationView(r.id, r.type, r.invoice_id, r.message, r.read_at, r.created_at) for r in rows],
            encode_token(rows[-1].created_at, rows[-1].id) if more else None,
            unread or 0,
        )

    async def mark_read(
        self, tenant_id: UUID, recipient_id: UUID, notification_id: UUID, now: datetime
    ) -> bool:
        mine = (
            Notification.id == notification_id,
            Notification.tenant_id == tenant_id,
            Notification.recipient_id == recipient_id,
        )
        updated = await self._session.execute(
            update(Notification)
            .where(*mine, Notification.read_at.is_(None))
            .values(read_at=now)
            .returning(Notification.id)
        )
        if updated.first() is not None:
            return True
        return await self._session.scalar(select(Notification.id).where(*mine)) is not None  # EC-03

    async def mark_all_read(self, tenant_id: UUID, recipient_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(Notification)
            .where(
                Notification.tenant_id == tenant_id,
                Notification.recipient_id == recipient_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=now)
        )
