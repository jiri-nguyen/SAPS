"""AuthService with fakes: sign-in, refresh, sign-out, back-channel logout (SAPS-44 TS-02 to TS-06 logic)."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from saps.application.auth import AuthService, code_challenge, hash_token
from saps.domain.identity import CompanyRef, IdentityClaims, SignInRefusal, SignInRefusedError
from saps.domain.users import Role, SessionPolicy
from saps.ports.auth import KnownIdentity, SessionRecord, SessionTokens, UserRecord
from saps.ports.identity import (
    IdentityProviderUnavailableError,
    IdentityRejectedError,
    InvalidLogoutTokenError,
    Tokens,
)

NOW = datetime(2027, 3, 1, 9, 0, tzinfo=UTC)
ISSUER = "http://idp.test/realms/saps"
VN = CompanyRef(uuid4(), "Demo Vietnam", "/companies/vn", "vn.example.com", True)
SG = CompanyRef(uuid4(), "Demo Singapore", "/companies/sg", "sg.example.com", True)
CLAIMS = IdentityClaims(
    issuer=ISSUER,
    subject="sub-1",
    email="member1@vn.example.com",
    display_name="Accounting Member 1",
    groups=("/companies/vn",),
    roles=("ACCOUNTING_MEMBER", "offline_access"),
    session_id="sid-1",
)


def _tokens(claims: IdentityClaims = CLAIMS, *, lifetime: int = 300, refresh: str = "rt-1") -> Tokens:
    return Tokens(claims, refresh, f"id-token-of-{claims.subject}", NOW + timedelta(seconds=lifetime))


class FakeCipher:
    """`enc:` prefix; a value older than allowed is marked `old:` by the test."""

    def encrypt(self, value: str) -> str:
        return f"enc:{value}"

    def decrypt(self, value: str, *, max_age_seconds: int | None = None) -> str | None:
        return value.removeprefix("enc:") if value.startswith("enc:") else None


class FakeProvider:
    def __init__(self) -> None:
        self.exchange_result: Tokens | Exception = _tokens()
        self.refresh_result: Tokens | Exception = _tokens(refresh="rt-2")
        self.exchanged: list[tuple[str, str, str]] = []
        self.refreshed: list[str] = []
        self.authorize_error: Exception | None = None
        self.end_session_error: Exception | None = None
        self.logout_sid: str | Exception = "sid-1"
        self.authorized: dict[str, str] = {}

    async def authorization_url(self, *, state: str, nonce: str, code_challenge: str) -> str:
        if self.authorize_error:
            raise self.authorize_error
        self.authorized = {"state": state, "nonce": nonce, "challenge": code_challenge}
        return f"http://idp.test/auth?state={state}"

    async def exchange_code(self, *, code: str, code_verifier: str, nonce: str) -> Tokens:
        self.exchanged.append((code, code_verifier, nonce))
        if isinstance(self.exchange_result, Exception):
            raise self.exchange_result
        return self.exchange_result

    async def refresh(self, refresh_token: str) -> Tokens:
        self.refreshed.append(refresh_token)
        if isinstance(self.refresh_result, Exception):
            raise self.refresh_result
        return self.refresh_result

    async def logout_session_id(self, logout_token: str) -> str:
        if isinstance(self.logout_sid, Exception):
            raise self.logout_sid
        return self.logout_sid

    async def end_session_url(self, *, id_token: str) -> str:
        if self.end_session_error:
            raise self.end_session_error
        return f"http://idp.test/logout?hint={id_token}"


class FakeRepo:
    def __init__(self) -> None:
        self.companies = {c.keycloak_group: c for c in (VN, SG)}
        self.known: list[KnownIdentity] = []
        self.users: dict[UUID, UserRecord] = {}
        self.saved: list[UUID | None] = []
        self.sessions: dict[str, SessionRecord] = {}
        self.revoked: list[UUID] = []
        self.touched: list[UUID] = []
        self.token_updates: list[SessionTokens] = []
        self.user_updates: list[tuple[str, Role]] = []
        self.idp_revoked: list[str] = []
        self.locked_override: SessionRecord | None = None

    async def find_company_by_group(self, group: str) -> CompanyRef | None:
        return self.companies.get(group)

    async def find_known_identities(self, *, issuer: str, subject: str, email: str) -> list[KnownIdentity]:
        return self.known

    async def save_signed_in_user(
        self, *, company: CompanyRef, claims: IdentityClaims, role: Role, user_id: UUID | None
    ) -> UserRecord:
        self.saved.append(user_id)
        user = UserRecord(
            id=user_id or uuid4(),
            tenant_id=company.tenant_id,
            username=claims.email,
            display_name=claims.display_name,
            role=role,
            is_active=True,
            tenant_is_active=True,
            company_name=company.name,
            idp_subject=claims.subject,
        )
        self.users[user.id] = user
        return user

    async def update_user(self, user_id: UUID, *, display_name: str, role: Role) -> None:
        self.user_updates.append((display_name, role))

    async def add_session(
        self, *, user: UserRecord, token_hash: str, expires_at: datetime, now: datetime, tokens: SessionTokens
    ) -> None:
        self.sessions[token_hash] = SessionRecord(uuid4(), user, expires_at, now, None, tokens)

    async def find_session(self, token_hash: str) -> SessionRecord | None:
        return self.sessions.get(token_hash)

    async def lock_session(self, session_id: UUID) -> SessionRecord | None:
        if self.locked_override is not None:
            return self.locked_override
        return next((s for s in self.sessions.values() if s.id == session_id), None)

    async def update_session_tokens(self, session_id: UUID, tokens: SessionTokens) -> None:
        self.token_updates.append(tokens)

    async def touch_session(self, session_id: UUID, now: datetime) -> None:
        self.touched.append(session_id)

    async def revoke_session(self, session_id: UUID, now: datetime) -> None:
        self.revoked.append(session_id)

    async def revoke_idp_sessions(self, idp_session_id: str, now: datetime) -> int:
        self.idp_revoked.append(idp_session_id)
        return 2


class World:
    def __init__(self) -> None:
        self.repo, self.provider, self.now = FakeRepo(), FakeProvider(), NOW
        policy = SessionPolicy(timedelta(minutes=30), timedelta(hours=8))
        self.auth = AuthService(self.repo, self.provider, FakeCipher(), policy, lambda: self.now)

    async def started(self, return_to: str | None = "/invoices/1") -> tuple[str, str]:
        start = await self.auth.start_sign_in(return_to)
        return start.cookie, self.provider.authorized["state"]

    async def signed_in(self) -> str:
        cookie, state = await self.started()
        result = await self.auth.complete_sign_in(code="c", state=state, error=None, cookie=cookie)
        return result.token


async def _refused(world: World, **kwargs: object) -> SignInRefusal:
    cookie, state = await world.started()
    args: dict[str, object] = {"code": "c", "state": state, "error": None, "cookie": cookie, **kwargs}
    with pytest.raises(SignInRefusedError) as caught:
        await world.auth.complete_sign_in(**args)  # type: ignore[arg-type]
    assert world.repo.sessions == {}
    return caught.value.reason


# --- Sign-in ------------------------------------------------------------------------------------------------


async def test_start_keeps_state_nonce_verifier_and_a_safe_return_path_in_the_encrypted_cookie() -> None:
    world = World()
    start = await world.auth.start_sign_in("//evil.example/x")
    payload = json.loads(start.cookie.removeprefix("enc:"))
    assert payload["returnTo"] == "/"
    assert payload["state"] == world.provider.authorized["state"]
    assert payload["nonce"] == world.provider.authorized["nonce"]
    assert world.provider.authorized["challenge"] == code_challenge(payload["verifier"])
    assert start.redirect_url.startswith("http://idp.test/auth")


def test_code_challenge_is_s256() -> None:  # RFC 7636 appendix B
    assert code_challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == (
        "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    )


async def test_sign_in_creates_the_user_and_a_session_with_encrypted_tokens() -> None:
    world = World()
    cookie, state = await world.started()
    result = await world.auth.complete_sign_in(code="the-code", state=state, error=None, cookie=cookie)
    assert result.return_to == "/invoices/1"
    assert result.user.role is Role.ACCOUNTING_MEMBER and result.user.tenant_id == VN.tenant_id
    assert world.repo.saved == [None]  # created
    code, verifier, nonce = world.provider.exchanged[0]
    assert code == "the-code" and nonce == world.provider.authorized["nonce"]
    assert code_challenge(verifier) == world.provider.authorized["challenge"]
    session = world.repo.sessions[hash_token(result.token)]
    assert result.token not in world.repo.sessions
    assert session.expires_at == NOW + timedelta(hours=8)
    assert session.tokens == SessionTokens(
        "sid-1", "enc:rt-1", "enc:id-token-of-sub-1", NOW + timedelta(seconds=300)
    )


@pytest.mark.parametrize(
    "known",
    [
        KnownIdentity(UUID(int=1), VN.tenant_id, ISSUER, "sub-1"),  # same subject
        KnownIdentity(UUID(int=1), VN.tenant_id, None, None),  # seeded demo user, same e-mail
    ],
)
async def test_an_existing_account_of_the_company_is_reused(known: KnownIdentity) -> None:
    world = World()
    world.repo.known = [known]
    await world.signed_in()
    assert world.repo.saved == [UUID(int=1)]


@pytest.mark.parametrize(
    "known",
    [
        [KnownIdentity(UUID(int=1), SG.tenant_id, None, None)],  # same e-mail in another company
        [KnownIdentity(UUID(int=1), SG.tenant_id, ISSUER, "sub-1")],  # moved to another company
        [
            KnownIdentity(UUID(int=1), VN.tenant_id, ISSUER, "other-subject")
        ],  # e-mail taken by another identity
        [
            KnownIdentity(UUID(int=1), VN.tenant_id, None, None),
            KnownIdentity(UUID(int=2), VN.tenant_id, None, None),
        ],
    ],
)
async def test_conflicting_accounts_refuse_the_sign_in(known: list[KnownIdentity]) -> None:  # EC-06
    world = World()
    world.repo.known = known
    assert await _refused(world) is SignInRefusal.NO_COMPANY
    assert world.repo.saved == []


@pytest.mark.parametrize(
    ("claims", "reason"),
    [
        (replace(CLAIMS, groups=()), SignInRefusal.NO_COMPANY),
        (replace(CLAIMS, groups=("/companies/xx",)), SignInRefusal.NO_COMPANY),
        (replace(CLAIMS, email="member1@sg.example.com"), SignInRefusal.WRONG_DOMAIN),
        (replace(CLAIMS, roles=()), SignInRefusal.NO_ROLE),
    ],
)
async def test_claims_that_break_the_rules_refuse_the_sign_in(
    claims: IdentityClaims, reason: SignInRefusal
) -> None:  # EC-03 to EC-05
    world = World()
    world.provider.exchange_result = _tokens(claims)
    assert await _refused(world) is reason


async def test_cancelled_expired_and_unavailable_sign_ins() -> None:  # EC-01, EC-02, EC-07
    world = World()
    assert await _refused(world, error="access_denied") is SignInRefusal.CANCELLED
    assert await _refused(world, cookie=None) is SignInRefusal.EXPIRED
    assert await _refused(world, cookie="old:whatever") is SignInRefusal.EXPIRED
    assert await _refused(world, cookie="enc:not json") is SignInRefusal.EXPIRED
    assert await _refused(world, cookie='enc:{"state": 1}') is SignInRefusal.EXPIRED
    assert await _refused(world, state="another-tab") is SignInRefusal.EXPIRED
    assert await _refused(world, code=None) is SignInRefusal.EXPIRED
    world.provider.exchange_result = IdentityRejectedError("invalid_grant")
    assert await _refused(world) is SignInRefusal.EXPIRED
    world.provider.exchange_result = IdentityProviderUnavailableError("down")
    assert await _refused(world) is SignInRefusal.UNAVAILABLE


# --- Requests and refresh -----------------------------------------------------------------------------------


async def test_a_fresh_session_resolves_without_a_refresh() -> None:
    world = World()
    token = await world.signed_in()
    world.now = NOW + timedelta(minutes=4)
    user = await world.auth.resolve(token)
    assert user is not None and user.username == "member1@vn.example.com"
    assert world.provider.refreshed == [] and len(world.repo.touched) == 1
    assert await world.auth.resolve("unknown") is None


async def test_an_expired_access_token_is_refreshed_and_role_changes_apply() -> None:  # BR-05
    world = World()
    token = await world.signed_in()
    world.now = NOW + timedelta(minutes=6)
    manager = replace(CLAIMS, roles=("ACCOUNTING_MANAGER",), display_name="New Name")
    world.provider.refresh_result = _tokens(manager, refresh="rt-2")
    user = await world.auth.resolve(token)
    assert user is not None and user.role is Role.ACCOUNTING_MANAGER and user.display_name == "New Name"
    assert world.provider.refreshed == ["rt-1"]
    assert world.repo.token_updates[0].refresh_token_encrypted == "enc:rt-2"  # noqa: S105  (test value)
    assert world.repo.user_updates == [("New Name", Role.ACCOUNTING_MANAGER)]


async def test_a_session_refreshed_by_a_parallel_request_is_not_refreshed_again() -> None:
    world = World()
    token = await world.signed_in()
    world.now = NOW + timedelta(minutes=6)
    session = world.repo.sessions[hash_token(token)]
    assert session.tokens is not None
    world.repo.locked_override = replace(
        session, tokens=replace(session.tokens, access_token_expires_at=world.now + timedelta(minutes=5))
    )
    assert await world.auth.resolve(token) is not None
    assert world.provider.refreshed == []


@pytest.mark.parametrize(
    "result",
    [
        IdentityRejectedError("invalid_grant"),  # EC-09: user disabled, session ended in Keycloak
        _tokens(
            replace(CLAIMS, groups=("/companies/sg",), email="member1@sg.example.com")
        ),  # company changed
        _tokens(replace(CLAIMS, roles=())),  # no role any more
        _tokens(replace(CLAIMS, subject="someone-else")),
    ],
)
async def test_a_refused_refresh_or_a_changed_company_ends_the_session(result: Tokens | Exception) -> None:
    world = World()
    token = await world.signed_in()
    world.now = NOW + timedelta(minutes=6)
    world.provider.refresh_result = result
    assert await world.auth.resolve(token) is None
    assert world.repo.revoked == [world.repo.sessions[hash_token(token)].id]


async def test_an_unreachable_identity_provider_keeps_the_session() -> None:  # EC-08
    world = World()
    token = await world.signed_in()
    world.now = NOW + timedelta(minutes=6)
    world.provider.refresh_result = IdentityProviderUnavailableError("down")
    with pytest.raises(IdentityProviderUnavailableError):
        await world.auth.resolve(token)
    assert world.repo.revoked == []


async def test_unreadable_tokens_end_the_session() -> None:
    world = World()
    token = await world.signed_in()
    session = world.repo.sessions[hash_token(token)]
    assert session.tokens is not None
    world.repo.sessions[hash_token(token)] = replace(
        session,
        tokens=replace(session.tokens, refresh_token_encrypted="old-key"),  # noqa: S106  (test value)
    )
    world.now = NOW + timedelta(minutes=6)
    assert await world.auth.resolve(token) is None
    assert world.repo.revoked == [session.id]


async def test_timeouts_inactive_users_and_sessions_without_tokens() -> None:
    world = World()
    token = await world.signed_in()
    key = hash_token(token)
    session = world.repo.sessions[key]
    world.now = NOW + timedelta(minutes=31)
    assert await world.auth.resolve(token) is None  # idle
    world.now = NOW
    world.repo.sessions[key] = replace(session, user=replace(session.user, is_active=False))
    assert await world.auth.resolve(token) is None
    world.repo.sessions[key] = replace(session, tokens=None)  # a PoC session (EC-13)
    assert await world.auth.resolve(token) is None
    world.repo.sessions[key] = session
    world.now = NOW + timedelta(minutes=6)
    world.repo.locked_override = replace(session, revoked_at=NOW)  # revoked meanwhile
    assert await world.auth.resolve(token) is None
    assert world.provider.refreshed == []


# --- Sign-out -----------------------------------------------------------------------------------------------


async def test_sign_out_revokes_and_returns_the_end_session_url() -> None:  # BR-06
    world = World()
    token = await world.signed_in()
    url = await world.auth.sign_out(token)
    assert url == "http://idp.test/logout?hint=id-token-of-sub-1"
    assert world.repo.revoked == [world.repo.sessions[hash_token(token)].id]
    assert await world.auth.sign_out("unknown") is None
    world.provider.end_session_error = IdentityProviderUnavailableError("down")
    assert await world.auth.sign_out(token) is None


async def test_backchannel_logout_revokes_the_sessions_of_the_idp_session() -> None:  # BR-07
    world = World()
    assert await world.auth.backchannel_logout("logout-token") == 2
    assert world.repo.idp_revoked == ["sid-1"]
    world.provider.logout_sid = InvalidLogoutTokenError("bad")
    with pytest.raises(InvalidLogoutTokenError):
        await world.auth.backchannel_logout("forged")
