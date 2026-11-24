"""Single Sign-On through the Identity Provider, session resolution and sign-out (SAPS-44, ADR-0011).

The SAPS API is the OpenID Connect client (backend for frontend): the browser only holds the `saps_session`
cookie, the tokens stay in the SAPS Database, encrypted. Session timeouts are those of SAPS-27.
"""

import base64
import hashlib
import json
import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from saps.domain.identity import (
    Acceptance,
    IdentityClaims,
    SignInRefusal,
    SignInRefusedError,
    accept,
    company_group,
    safe_return_to,
)
from saps.domain.users import CurrentUser, SessionPolicy
from saps.ports.auth import SessionRecord, SessionTokens, UserRecord, UserRepository
from saps.ports.identity import (
    IdentityProvider,
    IdentityProviderUnavailableError,
    IdentityRejectedError,
    TokenCipher,
    Tokens,
)

SIGN_IN_MAX_AGE_SECONDS = 600  # state, nonce and PKCE verifier live 10 minutes (EC-02)

log = logging.getLogger("saps.auth")


@dataclass(frozen=True)
class SignInStart:
    redirect_url: str
    cookie: str  # encrypted state, nonce, PKCE verifier and return path


@dataclass(frozen=True)
class SignInResult:
    user: CurrentUser
    token: str
    return_to: str


def hash_token(token: str) -> str:
    """Only the SHA-256 of the cookie value is stored (ADR-0008)."""
    return hashlib.sha256(token.encode()).hexdigest()


def code_challenge(verifier: str) -> str:
    """PKCE S256 (RFC 7636)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


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
        provider: IdentityProvider,
        cipher: TokenCipher,
        policy: SessionPolicy,
        clock: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._cipher = cipher
        self._policy = policy
        self._clock = clock

    # --- Sign-in (BR-01 to BR-03) ---------------------------------------------------------------------------

    async def start_sign_in(self, return_to: str | None) -> SignInStart:
        state, nonce, verifier = (
            secrets.token_urlsafe(32),
            secrets.token_urlsafe(32),
            secrets.token_urlsafe(48),
        )
        url = await self._provider.authorization_url(
            state=state, nonce=nonce, code_challenge=code_challenge(verifier)
        )
        payload = {
            "state": state,
            "nonce": nonce,
            "verifier": verifier,
            "returnTo": safe_return_to(return_to),
        }
        return SignInStart(redirect_url=url, cookie=self._cipher.encrypt(json.dumps(payload)))

    async def complete_sign_in(
        self, *, code: str | None, state: str | None, error: str | None, cookie: str | None
    ) -> SignInResult:
        """Raises `SignInRefusedError`; nothing is stored then."""
        if error:
            raise SignInRefusedError(SignInRefusal.CANCELLED)  # EC-01
        pending = self._pending_sign_in(cookie)
        if pending is None or not code or not state or not secrets.compare_digest(state, pending["state"]):
            raise SignInRefusedError(SignInRefusal.EXPIRED)  # EC-02
        try:
            tokens = await self._provider.exchange_code(
                code=code, code_verifier=pending["verifier"], nonce=pending["nonce"]
            )
        except IdentityProviderUnavailableError as exc:
            raise SignInRefusedError(SignInRefusal.UNAVAILABLE) from exc  # EC-07
        except IdentityRejectedError as exc:
            raise SignInRefusedError(SignInRefusal.EXPIRED) from exc

        claims = tokens.claims
        try:
            acceptance = await self._accept(claims)
        except SignInRefusedError as exc:
            log.info("sign_in_refused", extra={"reason": exc.reason.value})
            raise
        user_id = await self._existing_user(claims, acceptance.company.tenant_id)
        user = await self._repository.save_signed_in_user(
            company=acceptance.company, claims=claims, role=acceptance.role, user_id=user_id
        )
        token = secrets.token_urlsafe(32)  # 256 bits
        now = self._clock()
        await self._repository.add_session(
            user=user,
            token_hash=hash_token(token),
            expires_at=self._policy.expires_at(now),
            now=now,
            tokens=self._session_tokens(tokens),
        )
        log.info("sign_in_succeeded", extra={"user_id": str(user.id), "tenant_id": str(user.tenant_id)})
        return SignInResult(user=_current_user(user), token=token, return_to=pending["returnTo"])

    def _pending_sign_in(self, cookie: str | None) -> dict[str, str] | None:
        if not cookie:
            return None
        plain = self._cipher.decrypt(cookie, max_age_seconds=SIGN_IN_MAX_AGE_SECONDS)
        if plain is None:
            return None
        try:
            payload = json.loads(plain)
        except ValueError:
            return None
        keys = ("state", "nonce", "verifier", "returnTo")
        if not isinstance(payload, dict) or not all(isinstance(payload.get(k), str) for k in keys):
            return None
        return {k: payload[k] for k in keys}

    async def _accept(self, claims: IdentityClaims) -> Acceptance:
        group = company_group(claims)
        company = await self._repository.find_company_by_group(group) if group else None
        return accept(claims, company)

    async def _existing_user(self, claims: IdentityClaims, tenant_id: UUID) -> UUID | None:
        """The account to update: same subject, or a not yet linked account with the same e-mail in the same
        company (BR-03). Any other match is a conflict (EC-06)."""
        known = await self._repository.find_known_identities(
            issuer=claims.issuer, subject=claims.subject, email=claims.email
        )
        by_subject = [k for k in known if (k.idp_issuer, k.idp_subject) == (claims.issuer, claims.subject)]
        candidates = by_subject or known
        if not candidates:
            return None
        if len(candidates) == 1:
            match = candidates[0]
            linkable = by_subject or match.idp_subject is None
            if match.tenant_id == tenant_id and linkable:
                return match.user_id
        log.warning("sign_in_conflict", extra={"tenant_id": str(tenant_id)})
        raise SignInRefusedError(SignInRefusal.NO_COMPANY)

    def _session_tokens(self, tokens: Tokens) -> SessionTokens:
        return SessionTokens(
            idp_session_id=tokens.claims.session_id,
            refresh_token_encrypted=self._cipher.encrypt(tokens.refresh_token),
            id_token_encrypted=self._cipher.encrypt(tokens.id_token),
            access_token_expires_at=tokens.access_token_expires_at,
        )

    # --- Requests (BR-04, BR-05) ----------------------------------------------------------------------------

    async def resolve(self, token: str) -> CurrentUser | None:
        """The user of a session cookie, or None.

        Raises `IdentityProviderUnavailableError` when a needed refresh cannot reach the Identity Provider;
        the session is kept then (EC-08).
        """
        session = await self._repository.find_session(hash_token(token))
        if session is None:
            return None
        now = self._clock()
        if not self._usable(session, now):
            return None
        user = session.user
        if session.tokens is None:
            return None
        if session.tokens.access_token_expires_at <= now:
            refreshed = await self._refresh(session, now)
            if refreshed is None:
                return None
            user = refreshed
        await self._repository.touch_session(session.id, now)
        return _current_user(user)

    def _usable(self, session: SessionRecord, now: datetime) -> bool:
        active = self._policy.is_active(
            now=now,
            expires_at=session.expires_at,
            last_seen_at=session.last_seen_at,
            revoked_at=session.revoked_at,
        )
        return active and session.user.is_active and session.user.tenant_is_active

    async def _refresh(self, session: SessionRecord, now: datetime) -> UserRecord | None:
        locked = await self._repository.lock_session(session.id)
        if locked is None or locked.tokens is None or not self._usable(locked, now):
            return None
        if locked.tokens.access_token_expires_at > now:
            return locked.user  # refreshed by a parallel request meanwhile
        refresh_token = self._cipher.decrypt(locked.tokens.refresh_token_encrypted)
        if refresh_token is None:
            await self._end(locked, now, "token_unreadable")
            return None
        try:
            tokens = await self._provider.refresh(refresh_token)
        except IdentityRejectedError:
            await self._end(locked, now, "refresh_refused")  # EC-09
            return None
        user = locked.user
        try:
            acceptance = await self._accept(tokens.claims)
        except SignInRefusedError as exc:
            await self._end(locked, now, exc.reason.value)
            return None
        if acceptance.company.tenant_id != user.tenant_id or tokens.claims.subject != user.idp_subject:
            await self._end(locked, now, "company_changed")
            return None
        await self._repository.update_session_tokens(locked.id, self._session_tokens(tokens))
        if (tokens.claims.display_name, acceptance.role) != (user.display_name, user.role):
            await self._repository.update_user(
                user.id, display_name=tokens.claims.display_name, role=acceptance.role
            )
            user = replace(user, display_name=tokens.claims.display_name, role=acceptance.role)
        log.info("session_refreshed", extra={"user_id": str(user.id), "tenant_id": str(user.tenant_id)})
        return user

    async def _end(self, session: SessionRecord, now: datetime, reason: str) -> None:
        await self._repository.revoke_session(session.id, now)
        log.info(
            "session_ended",
            extra={
                "user_id": str(session.user.id),
                "tenant_id": str(session.user.tenant_id),
                "reason": reason,
            },
        )

    # --- Sign-out (BR-06, BR-07) ----------------------------------------------------------------------------

    async def sign_out(self, token: str) -> str | None:
        """Revoke the session; returns the Identity Provider's end-session URL (None: unknown session)."""
        session = await self._repository.find_session(hash_token(token))
        if session is None:
            return None
        await self._end(session, self._clock(), "signed_out")
        id_token = self._cipher.decrypt(session.tokens.id_token_encrypted) if session.tokens else None
        try:
            return await self._provider.end_session_url(id_token=id_token or "")
        except IdentityProviderUnavailableError:
            return None

    async def backchannel_logout(self, logout_token: str) -> int:
        """Raises `InvalidLogoutTokenError` (EC-11); an unknown session revokes nothing (EC-12)."""
        idp_session_id = await self._provider.logout_session_id(logout_token)
        count = await self._repository.revoke_idp_sessions(idp_session_id, self._clock())
        log.info("backchannel_logout", extra={"sessions": count})
        return count
