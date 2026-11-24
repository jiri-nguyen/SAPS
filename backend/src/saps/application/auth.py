"""Sign-in, session resolution and sign-out (SAPS-27, ADR-0008)."""

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from saps.domain.users import CurrentUser, SessionPolicy
from saps.ports.auth import PasswordHasher, UserRecord, UserRepository


class InvalidCredentialsError(Exception):
    """Unknown user, wrong password, or inactive user or tenant — always the same error (SAPS-27 BR-02)."""


@dataclass(frozen=True)
class SignInResult:
    user: CurrentUser
    token: str


def hash_token(token: str) -> str:
    """Only the SHA-256 of the cookie value is stored (ADR-0008)."""
    return hashlib.sha256(token.encode()).hexdigest()


def _current_user(record: UserRecord) -> CurrentUser:
    return CurrentUser(
        user_id=record.id,
        tenant_id=record.tenant_id,
        username=record.username,
        display_name=record.display_name,
        role=record.role,
        company_name=record.company_name,
    )


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        hasher: PasswordHasher,
        policy: SessionPolicy,
        clock: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._hasher = hasher
        self._policy = policy
        self._clock = clock

    async def sign_in(self, username: str, password: str) -> SignInResult:
        record = await self._repository.find_user_by_username(username.strip())
        if record is None:
            self._hasher.dummy_verify(password)
            raise InvalidCredentialsError
        password_ok = self._hasher.verify(record.password_hash, password)
        if not (password_ok and record.is_active and record.tenant_is_active):
            raise InvalidCredentialsError
        token = secrets.token_urlsafe(32)  # 256 bits
        now = self._clock()
        await self._repository.add_session(
            user=record, token_hash=hash_token(token), expires_at=self._policy.expires_at(now), now=now
        )
        return SignInResult(user=_current_user(record), token=token)

    async def resolve(self, token: str) -> CurrentUser | None:
        session = await self._repository.find_session(hash_token(token))
        if session is None:
            return None
        now = self._clock()
        active = self._policy.is_active(
            now=now,
            expires_at=session.expires_at,
            last_seen_at=session.last_seen_at,
            revoked_at=session.revoked_at,
        )
        if not (active and session.user.is_active and session.user.tenant_is_active):
            return None
        await self._repository.touch_session(session.id, now)
        return _current_user(session.user)

    async def sign_out(self, token: str) -> None:
        await self._repository.revoke_session(hash_token(token), self._clock())
