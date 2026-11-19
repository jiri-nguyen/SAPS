"""Ports used by the sign-in use cases (SAPS-27, ADR-0001)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from saps.domain.users import Role


@dataclass(frozen=True)
class UserRecord:
    id: UUID
    tenant_id: UUID
    username: str
    display_name: str
    role: Role
    password_hash: str
    is_active: bool
    tenant_is_active: bool


@dataclass(frozen=True)
class SessionRecord:
    id: UUID
    user: UserRecord
    expires_at: datetime
    last_seen_at: datetime
    revoked_at: datetime | None


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...

    def dummy_verify(self, password: str) -> None:
        """Spend the same time as a real check (unknown usernames, SAPS-27 EC-01)."""
        ...


class UserRepository(Protocol):
    async def find_user_by_username(self, username: str) -> UserRecord | None: ...

    async def add_session(
        self, *, user: UserRecord, token_hash: str, expires_at: datetime, now: datetime
    ) -> None: ...

    async def find_session(self, token_hash: str) -> SessionRecord | None: ...

    async def touch_session(self, session_id: UUID, now: datetime) -> None: ...

    async def revoke_session(self, token_hash: str, now: datetime) -> None: ...
