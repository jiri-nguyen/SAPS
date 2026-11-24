"""Users, roles and session rules (SAPS-27). Pure domain code: no framework imports (ADR-0001)."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    """The two PoC roles (SCP-IN-12)."""

    ACCOUNTING_MEMBER = "ACCOUNTING_MEMBER"
    ACCOUNTING_MANAGER = "ACCOUNTING_MANAGER"


@dataclass(frozen=True)
class CurrentUser:
    """The signed-in user of a request; the tenant scopes every query (ADR-0007)."""

    user_id: UUID
    tenant_id: UUID
    username: str
    display_name: str
    role: Role
    company_name: str = ""  # shown in the Web App header (SAPS-42)


class AccessDeniedError(Exception):
    """The user's role is not allowed for the operation."""


def ensure_role(user: CurrentUser, allowed: Iterable[Role]) -> None:
    if user.role not in set(allowed):
        raise AccessDeniedError(f"Role {user.role} is not allowed")


@dataclass(frozen=True)
class SessionPolicy:
    """Idle and absolute timeouts of a session (ADR-0008)."""

    idle_timeout: timedelta
    absolute_timeout: timedelta

    def expires_at(self, now: datetime) -> datetime:
        return now + self.absolute_timeout

    def is_active(
        self, *, now: datetime, expires_at: datetime, last_seen_at: datetime, revoked_at: datetime | None
    ) -> bool:
        return revoked_at is None and now < expires_at and now - last_seen_at < self.idle_timeout
