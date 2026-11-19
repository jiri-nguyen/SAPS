from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from saps.application.auth import AuthService, InvalidCredentialsError, hash_token
from saps.domain.users import Role, SessionPolicy
from saps.ports.auth import SessionRecord, UserRecord

NOW = datetime(2026, 12, 15, 9, 0, tzinfo=UTC)
USER = UserRecord(
    uuid4(), uuid4(), "member1", "Accounting Member 1", Role.ACCOUNTING_MEMBER, "hash:pw", True, True
)


class FakeHasher:
    def __init__(self) -> None:
        self.dummy_calls = 0

    def hash(self, password: str) -> str:
        return f"hash:{password}"

    def verify(self, password_hash: str, password: str) -> bool:
        return password_hash == f"hash:{password}"

    def dummy_verify(self, password: str) -> None:
        self.dummy_calls += 1


class FakeRepo:
    def __init__(self, user: UserRecord | None = USER) -> None:
        self.user = user
        self.sessions: dict[str, SessionRecord] = {}
        self.touched: list[UUID] = []
        self.revoked: list[str] = []

    async def find_user_by_username(self, username: str) -> UserRecord | None:
        return self.user if self.user and self.user.username == username else None

    async def add_session(
        self, *, user: UserRecord, token_hash: str, expires_at: datetime, now: datetime
    ) -> None:
        self.sessions[token_hash] = SessionRecord(uuid4(), user, expires_at, now, None)

    async def find_session(self, token_hash: str) -> SessionRecord | None:
        return self.sessions.get(token_hash)

    async def touch_session(self, session_id: UUID, now: datetime) -> None:
        self.touched.append(session_id)

    async def revoke_session(self, token_hash: str, now: datetime) -> None:
        self.revoked.append(token_hash)


def _service(repo: FakeRepo, hasher: FakeHasher | None = None, now: datetime = NOW) -> AuthService:
    policy = SessionPolicy(timedelta(minutes=30), timedelta(hours=8))
    return AuthService(repo, hasher or FakeHasher(), policy, lambda: now)


async def test_sign_in_creates_a_session_storing_only_the_token_hash() -> None:
    repo = FakeRepo()
    result = await _service(repo).sign_in(" member1 ", "pw")
    assert result.user.username == "member1" and result.user.role is Role.ACCOUNTING_MEMBER
    assert list(repo.sessions) == [hash_token(result.token)]
    assert result.token not in repo.sessions
    assert len(result.token) >= 43  # 32 random bytes, URL-safe base64
    assert repo.sessions[hash_token(result.token)].expires_at == NOW + timedelta(hours=8)


async def test_unknown_user_runs_a_dummy_check_and_fails() -> None:
    hasher = FakeHasher()
    with pytest.raises(InvalidCredentialsError):
        await _service(FakeRepo(user=None), hasher).sign_in("nobody", "pw")
    assert hasher.dummy_calls == 1


@pytest.mark.parametrize(
    ("user", "password"),
    [(USER, "wrong"), (replace(USER, is_active=False), "pw"), (replace(USER, tenant_is_active=False), "pw")],
)
async def test_wrong_password_or_inactive_user_or_tenant_fails(user: UserRecord, password: str) -> None:
    repo = FakeRepo(user)
    with pytest.raises(InvalidCredentialsError):
        await _service(repo).sign_in("member1", password)
    assert repo.sessions == {}


async def test_resolve_returns_the_user_and_touches_the_session() -> None:
    repo = FakeRepo()
    token = (await _service(repo).sign_in("member1", "pw")).token
    user = await _service(repo, now=NOW + timedelta(minutes=10)).resolve(token)
    assert user is not None and user.user_id == USER.id
    assert len(repo.touched) == 1


async def test_resolve_rejects_unknown_expired_or_deactivated_sessions() -> None:
    repo = FakeRepo()
    token = (await _service(repo).sign_in("member1", "pw")).token
    assert await _service(repo).resolve("unknown-token") is None
    assert await _service(repo, now=NOW + timedelta(minutes=31)).resolve(token) is None
    key = hash_token(token)
    repo.sessions[key] = replace(repo.sessions[key], user=replace(USER, is_active=False))
    assert await _service(repo).resolve(token) is None
    assert repo.touched == []


async def test_sign_out_revokes_by_token_hash() -> None:
    repo = FakeRepo()
    await _service(repo).sign_out("some-token")
    assert repo.revoked == [hash_token("some-token")]
