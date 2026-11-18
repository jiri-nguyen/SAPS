from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from saps.domain.users import AccessDeniedError, CurrentUser, Role, SessionPolicy, ensure_role

NOW = datetime(2026, 12, 15, 9, 0, tzinfo=UTC)
POLICY = SessionPolicy(idle_timeout=timedelta(minutes=30), absolute_timeout=timedelta(hours=8))


def _user(role: Role) -> CurrentUser:
    return CurrentUser(uuid4(), uuid4(), "member1", "Accounting Member 1", role)


def test_ensure_role_allows_listed_roles() -> None:
    ensure_role(_user(Role.ACCOUNTING_MANAGER), [Role.ACCOUNTING_MANAGER])


def test_ensure_role_refuses_other_roles() -> None:
    with pytest.raises(AccessDeniedError):
        ensure_role(_user(Role.ACCOUNTING_MEMBER), [Role.ACCOUNTING_MANAGER])


def test_session_expires_after_the_absolute_timeout() -> None:
    assert POLICY.expires_at(NOW) == NOW + timedelta(hours=8)


@pytest.mark.parametrize(
    ("now", "last_seen", "revoked", "active"),
    [
        (NOW + timedelta(minutes=29), NOW, None, True),
        (NOW + timedelta(minutes=30), NOW, None, False),  # idle timeout
        (NOW + timedelta(hours=8), NOW + timedelta(hours=8) - timedelta(minutes=1), None, False),  # absolute
        (NOW + timedelta(minutes=1), NOW, NOW, False),  # revoked
    ],
)
def test_session_activity(now: datetime, last_seen: datetime, revoked: datetime | None, active: bool) -> None:
    expires = POLICY.expires_at(NOW)
    assert POLICY.is_active(now=now, expires_at=expires, last_seen_at=last_seen, revoked_at=revoked) is active
