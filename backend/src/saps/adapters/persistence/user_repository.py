"""SQLAlchemy implementation of the UserRepository port (SAPS-27).

Sign-in and session lookups happen before the company is known: they find the row through the SECURITY DEFINER
functions of SAPS-41 (BR-05), then set the company on the transaction, so everything else runs under row-level
security.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from saps.adapters.persistence.db import set_tenant
from saps.adapters.persistence.models import Tenant, UserAccount, UserSession
from saps.ports.auth import SessionRecord, UserRecord


def _user_record(user: UserAccount, tenant: Tenant) -> UserRecord:
    return UserRecord(
        id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        password_hash=user.password_hash,
        is_active=user.is_active,
        tenant_is_active=tenant.is_active,
    )


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_user_by_username(self, username: str) -> UserRecord | None:
        found_user = (
            await self._session.execute(
                select(func.saps_find_user_for_sign_in(username).table_valued("tenant_id"))
            )
        ).first()
        if found_user is None:
            return None
        await set_tenant(self._session, found_user.tenant_id)
        row = await self._session.execute(
            select(UserAccount, Tenant).join(Tenant).where(UserAccount.username == username)
        )
        found = row.first()
        return None if found is None else _user_record(found[0], found[1])

    async def add_session(
        self, *, user: UserRecord, token_hash: str, expires_at: datetime, now: datetime
    ) -> None:
        self._session.add(
            UserSession(
                tenant_id=user.tenant_id,
                user_account_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
                last_seen_at=now,
                created_by=user.username,
                updated_by=user.username,
            )
        )
        await self._session.flush()

    async def find_session(self, token_hash: str) -> SessionRecord | None:
        if not await self._enter_tenant_of_session(token_hash):
            return None
        result = await self._session.execute(
            select(UserSession)
            .options(joinedload(UserSession.user).joinedload(UserAccount.tenant))
            .where(UserSession.token_hash == token_hash)
        )
        session = result.scalar_one_or_none()
        if session is None:
            return None
        return SessionRecord(
            id=session.id,
            user=_user_record(session.user, session.user.tenant),
            expires_at=session.expires_at,
            last_seen_at=session.last_seen_at,
            revoked_at=session.revoked_at,
        )

    async def touch_session(self, session_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(UserSession).where(UserSession.id == session_id).values(last_seen_at=now)
        )

    async def revoke_session(self, token_hash: str, now: datetime) -> None:
        if not await self._enter_tenant_of_session(token_hash):
            return
        await self._session.execute(
            update(UserSession)
            .where(UserSession.token_hash == token_hash, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def _enter_tenant_of_session(self, token_hash: str) -> bool:
        found = (
            await self._session.execute(select(func.saps_find_session(token_hash).table_valued("tenant_id")))
        ).first()
        if found is None:
            return False
        await set_tenant(self._session, found.tenant_id)
        return True
