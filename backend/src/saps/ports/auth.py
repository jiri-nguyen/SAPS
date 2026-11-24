"""Ports used by the sign-in use cases (SAPS-27, SAPS-44, ADR-0001)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from saps.domain.identity import CompanyRef, IdentityClaims
from saps.domain.users import Role


@dataclass(frozen=True)
class UserRecord:
    id: UUID
    tenant_id: UUID
    username: str
    display_name: str
    role: Role
    is_active: bool
    tenant_is_active: bool
    company_name: str = ""  # SAPS-42
    idp_subject: str | None = None  # SAPS-44; empty until the first sign-in through the Identity Provider


@dataclass(frozen=True)
class SessionTokens:
    """What a session keeps of the Identity Provider (SAPS-44 BR-04); the tokens are encrypted."""

    idp_session_id: str | None
    refresh_token_encrypted: str
    id_token_encrypted: str
    access_token_expires_at: datetime


@dataclass(frozen=True)
class SessionRecord:
    id: UUID
    user: UserRecord
    expires_at: datetime
    last_seen_at: datetime
    revoked_at: datetime | None
    tokens: SessionTokens | None = None  # None only for sessions created before SAPS-44 (revoked by 0008)


@dataclass(frozen=True)
class KnownIdentity:
    """An account that may belong to a signing-in identity: same subject or same e-mail (SAPS-44 BR-03)."""

    user_id: UUID
    tenant_id: UUID
    idp_issuer: str | None
    idp_subject: str | None


class UserRepository(Protocol):
    async def find_company_by_group(self, group: str) -> CompanyRef | None: ...

    async def find_known_identities(self, *, issuer: str, subject: str, email: str) -> list[KnownIdentity]:
        """Accounts of any company with this subject or this e-mail (before the company is set)."""
        ...

    async def save_signed_in_user(
        self, *, company: CompanyRef, claims: IdentityClaims, role: Role, user_id: UUID | None
    ) -> UserRecord:
        """Update the account `user_id` (and link it to the identity), or create one when it is None."""
        ...

    async def update_user(self, user_id: UUID, *, display_name: str, role: Role) -> None: ...

    async def add_session(
        self,
        *,
        user: UserRecord,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
        tokens: SessionTokens,
    ) -> None: ...

    async def find_session(self, token_hash: str) -> SessionRecord | None: ...

    async def lock_session(self, session_id: UUID) -> SessionRecord | None:
        """The session again, locked until the transaction ends (one refresh at a time)."""
        ...

    async def update_session_tokens(self, session_id: UUID, tokens: SessionTokens) -> None: ...

    async def touch_session(self, session_id: UUID, now: datetime) -> None: ...

    async def revoke_session(self, session_id: UUID, now: datetime) -> None: ...

    async def revoke_idp_sessions(self, idp_session_id: str, now: datetime) -> int:
        """Revoke every open session of an Identity Provider session, in any company; returns how many."""
        ...
