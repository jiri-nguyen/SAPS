"""SQLAlchemy implementation of the UserRepository port (SAPS-27, SAPS-44).

Sign-in and session lookups happen before the company is known: they find the rows through the SECURITY
DEFINER functions of SAPS-41 and SAPS-44, then set the company on the transaction, so everything else runs
under row-level security.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from saps.adapters.persistence.db import set_tenant
from saps.adapters.persistence.models import Tenant, UserAccount, UserSession
from saps.domain.identity import CompanyRef, IdentityClaims
from saps.domain.users import Role
from saps.ports.auth import KnownIdentity, SessionRecord, SessionTokens, UserRecord

SYSTEM_ACTOR = "sso"


def _user_record(user: UserAccount, tenant: Tenant) -> UserRecord:
    return UserRecord(
        id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        tenant_is_active=tenant.is_active,
        company_name=tenant.name,
        idp_subject=user.idp_subject,
    )


def _session_record(session: UserSession) -> SessionRecord:
    tokens = None
    if session.refresh_token_encrypted and session.id_token_encrypted and session.access_token_expires_at:
        tokens = SessionTokens(
            idp_session_id=session.idp_session_id,
            refresh_token_encrypted=session.refresh_token_encrypted,
            id_token_encrypted=session.id_token_encrypted,
            access_token_expires_at=session.access_token_expires_at,
        )
    return SessionRecord(
        id=session.id,
        user=_user_record(session.user, session.user.tenant),
        expires_at=session.expires_at,
        last_seen_at=session.last_seen_at,
        revoked_at=session.revoked_at,
        tokens=tokens,
    )


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Sign-in --------------------------------------------------------------------------------------------

    async def find_company_by_group(self, group: str) -> CompanyRef | None:
        tenant = (
            await self._session.execute(select(Tenant).where(Tenant.keycloak_group == group))
        ).scalar_one_or_none()
        if tenant is None or tenant.keycloak_group is None or tenant.email_domain is None:
            return None
        return CompanyRef(
            tenant_id=tenant.id,
            name=tenant.name,
            keycloak_group=tenant.keycloak_group,
            email_domain=tenant.email_domain,
            is_active=tenant.is_active,
        )

    async def find_known_identities(self, *, issuer: str, subject: str, email: str) -> list[KnownIdentity]:
        rows = await self._session.execute(
            select(
                func.saps_find_user_for_sign_in(issuer, subject, email).table_valued(
                    "user_id", "tenant_id", "idp_issuer", "idp_subject"
                )
            )
        )
        return [
            KnownIdentity(
                user_id=row.user_id,
                tenant_id=row.tenant_id,
                idp_issuer=row.idp_issuer,
                idp_subject=row.idp_subject,
            )
            for row in rows
        ]

    async def save_signed_in_user(
        self, *, company: CompanyRef, claims: IdentityClaims, role: Role, user_id: UUID | None
    ) -> UserRecord:
        await set_tenant(self._session, company.tenant_id)
        if user_id is None:
            user = UserAccount(
                tenant_id=company.tenant_id,
                username=claims.email.lower(),
                created_by=SYSTEM_ACTOR,
                updated_by=SYSTEM_ACTOR,
            )
            self._session.add(user)
        else:
            user = (
                await self._session.execute(select(UserAccount).where(UserAccount.id == user_id))
            ).scalar_one()
            user.updated_by = SYSTEM_ACTOR
        user.display_name = claims.display_name
        user.role = role
        user.email = claims.email.lower()
        user.idp_issuer = claims.issuer
        user.idp_subject = claims.subject
        await self._session.flush()
        tenant = await self._session.get_one(Tenant, company.tenant_id)
        return _user_record(user, tenant)

    async def update_user(self, user_id: UUID, *, display_name: str, role: Role) -> None:
        await self._session.execute(
            update(UserAccount)
            .where(UserAccount.id == user_id)
            .values(display_name=display_name, role=role, updated_by=SYSTEM_ACTOR)
        )

    # --- Sessions -------------------------------------------------------------------------------------------

    async def add_session(
        self,
        *,
        user: UserRecord,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
        tokens: SessionTokens,
    ) -> None:
        self._session.add(
            UserSession(
                tenant_id=user.tenant_id,
                user_account_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
                last_seen_at=now,
                idp_session_id=tokens.idp_session_id,
                refresh_token_encrypted=tokens.refresh_token_encrypted,
                id_token_encrypted=tokens.id_token_encrypted,
                access_token_expires_at=tokens.access_token_expires_at,
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
        return None if session is None else _session_record(session)

    async def lock_session(self, session_id: UUID) -> SessionRecord | None:
        locked = (
            await self._session.execute(
                select(UserSession.id).where(UserSession.id == session_id).with_for_update()
            )
        ).scalar_one_or_none()
        if locked is None:
            return None
        result = await self._session.execute(
            select(UserSession)
            .options(joinedload(UserSession.user).joinedload(UserAccount.tenant))
            .where(UserSession.id == session_id)
            .execution_options(populate_existing=True)
        )
        return _session_record(result.scalar_one())

    async def update_session_tokens(self, session_id: UUID, tokens: SessionTokens) -> None:
        await self._session.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(
                idp_session_id=tokens.idp_session_id,
                refresh_token_encrypted=tokens.refresh_token_encrypted,
                id_token_encrypted=tokens.id_token_encrypted,
                access_token_expires_at=tokens.access_token_expires_at,
            )
        )

    async def touch_session(self, session_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(UserSession).where(UserSession.id == session_id).values(last_seen_at=now)
        )

    async def revoke_session(self, session_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(UserSession)
            .where(UserSession.id == session_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def revoke_idp_sessions(self, idp_session_id: str, now: datetime) -> int:
        tenants = (
            await self._session.execute(
                select(func.saps_find_idp_sessions(idp_session_id).table_valued("tenant_id"))
            )
        ).all()
        count = 0
        for row in tenants:
            await set_tenant(self._session, row.tenant_id)
            result = await self._session.execute(
                update(UserSession)
                .where(UserSession.idp_session_id == idp_session_id, UserSession.revoked_at.is_(None))
                .values(revoked_at=now)
                .returning(UserSession.id)
            )
            count += len(result.all())
        return count

    async def _enter_tenant_of_session(self, token_hash: str) -> bool:
        found = (
            await self._session.execute(select(func.saps_find_session(token_hash).table_valued("tenant_id")))
        ).first()
        if found is None:
            return False
        await set_tenant(self._session, found.tenant_id)
        return True
