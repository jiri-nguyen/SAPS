"""Integration: Single Sign-On through the SAPS API on a real PostgreSQL (SAPS-44 TS-02 to TS-07).

The Identity Provider is a fake behind the `identity_provider` dependency; the OpenID Connect adapter
itself is tested in test_oidc_provider, the real Keycloak in the compose smoke test (TS-09).
"""

import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from saps.adapters.persistence.db import dispose_engines, session_factory
from saps.adapters.persistence.models import Tenant, UserAccount, UserSession
from saps.api.deps import identity_provider, token_cipher
from saps.api.main import create_app
from saps.application.auth import hash_token
from saps.config import get_settings
from saps.domain.identity import IdentityClaims
from saps.domain.users import Role
from saps.ports.identity import (
    IdentityProviderUnavailableError,
    IdentityRejectedError,
    InvalidLogoutTokenError,
    Tokens,
)
from saps.seed import _run as run_seed
from tests.integration.conftest import alembic
from tests.integration.db_urls import use_database

pytestmark = pytest.mark.integration

ORIGIN = "http://localhost:5173"
ISSUER = "http://idp.test/realms/saps"


def _claims(email: str = "member1@vn.example.com", **overrides: object) -> IdentityClaims:
    company = email.rpartition("@")[2].split(".")[0]
    claims = IdentityClaims(
        issuer=ISSUER,
        subject=f"sub-{email}",
        email=email,
        display_name=f"SSO {email}",
        groups=(f"/companies/{company}",),
        roles=("ACCOUNTING_MEMBER",),
        session_id=f"sid-{email}",
    )
    return replace(claims, **overrides)  # type: ignore[arg-type]


@dataclass
class FakeIdp:
    """Answers with the claims the test sets for the next code exchange or refresh."""

    next_claims: IdentityClaims = field(default_factory=_claims)
    refresh_error: Exception | None = None
    logout_sid: str | Exception = "sid"
    refreshed: list[str] = field(default_factory=list)

    def _tokens(self, refresh_token: str) -> Tokens:
        expires = datetime.now(UTC) + timedelta(minutes=5)
        return Tokens(self.next_claims, refresh_token, f"id-token-{self.next_claims.subject}", expires)

    async def authorization_url(self, *, state: str, nonce: str, code_challenge: str) -> str:
        return f"{ISSUER}/auth?state={state}"

    async def exchange_code(self, *, code: str, code_verifier: str, nonce: str) -> Tokens:
        if code == "bad":
            raise IdentityRejectedError("invalid_grant")
        return self._tokens(f"rt-{uuid.uuid4().hex}")

    async def refresh(self, refresh_token: str) -> Tokens:
        self.refreshed.append(refresh_token)
        if self.refresh_error is not None:
            raise self.refresh_error
        return self._tokens(refresh_token)

    async def logout_session_id(self, logout_token: str) -> str:
        if isinstance(self.logout_sid, Exception):
            raise self.logout_sid
        return self.logout_sid

    async def end_session_url(self, *, id_token: str) -> str:
        return f"{ISSUER}/logout?id_token_hint={id_token}"


@dataclass
class Sso:
    app: FastAPI
    idp: FakeIdp
    clients: list[AsyncClient] = field(default_factory=list)

    def client(self, *, origin: bool = True) -> AsyncClient:
        headers = {"Origin": ORIGIN} if origin else {}
        client = AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test", headers=headers)
        self.clients.append(client)
        return client

    async def sign_in(self, claims: IdentityClaims, *, return_to: str = "/invoices") -> AsyncClient:
        self.idp.next_claims = claims
        client = self.client()
        location = await self.callback(client, return_to=return_to)
        assert location == return_to, location
        return client

    async def callback(self, client: AsyncClient, *, return_to: str = "/", code: str = "code") -> str:
        start = await client.get("/v1/session/sign-in", params={"returnTo": return_to})
        assert start.status_code == 302
        state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
        done = await client.get("/v1/session/callback", params={"code": code, "state": state})
        assert done.status_code == 302
        return str(done.headers["location"])


@asynccontextmanager
async def _sso(database_url: str, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Sso]:
    use_database(monkeypatch, database_url)
    monkeypatch.setenv("WEB_APP_ORIGIN", ORIGIN)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")  # the test client talks plain HTTP
    monkeypatch.setenv("SESSION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    get_settings.cache_clear()
    token_cipher.cache_clear()
    app = create_app()
    sso = Sso(app, FakeIdp())
    app.dependency_overrides[identity_provider] = lambda: sso.idp
    try:
        yield sso
    finally:
        for client in sso.clients:
            await client.aclose()
        await dispose_engines()
        get_settings.cache_clear()
        token_cipher.cache_clear()


@pytest.fixture
async def sso(database_url: str, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Sso]:
    await run_seed(database_url)
    async with _sso(database_url, monkeypatch) as sso_:
        yield sso_


@pytest.fixture
async def db(database_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(database_url)
    try:
        async with session_factory(engine)() as session:
            yield session
    finally:
        await engine.dispose()


async def _user(db: AsyncSession, username: str) -> UserAccount:
    db.expire_all()
    user = (await db.execute(select(UserAccount).where(UserAccount.username == username))).scalar_one()
    return user


async def _expire_access_token(db: AsyncSession, client: AsyncClient) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.token_hash == hash_token(client.cookies["saps_session"]))
        .values(access_token_expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    await db.commit()


# TS-02 / BR-03, BR-04 ---------------------------------------------------------------------------------------


async def test_seed_keeps_no_password(database_url: str, db: AsyncSession) -> None:
    await run_seed(database_url)
    await run_seed(database_url)  # idempotent
    columns = {
        row.column_name
        for row in await db.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'user_account'")
        )
    }
    assert "password_hash" not in columns and {"email", "idp_issuer", "idp_subject"} <= columns
    member = await _user(db, "member1@sg.example.com")
    assert member.email == "member1@sg.example.com"


async def test_sign_in_links_the_seeded_user_and_starts_a_session(sso: Sso, db: AsyncSession) -> None:
    seeded = await _user(db, "manager1@vn.example.com")
    claims = _claims("manager1@vn.example.com", roles=("ACCOUNTING_MANAGER", "offline_access"))
    client = sso.client()
    start = await client.get("/v1/session/sign-in", params={"returnTo": "/invoices?status=Exception"})
    assert start.status_code == 302 and start.headers["location"].startswith(f"{ISSUER}/auth")
    cookie_header = start.headers["set-cookie"]
    assert (
        "saps_sign_in=" in cookie_header
        and "HttpOnly" in cookie_header
        and "Path=/v1/session" in cookie_header
    )

    sso.idp.next_claims = claims
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    done = await client.get("/v1/session/callback", params={"code": "c", "state": state})
    assert done.status_code == 302 and done.headers["location"] == "/invoices?status=Exception"
    set_cookies = done.headers.get_list("set-cookie")
    session_cookie = next(c for c in set_cookies if c.startswith("saps_session="))
    assert "HttpOnly" in session_cookie and "SameSite=lax" in session_cookie
    assert any(c.startswith('saps_sign_in=""') for c in set_cookies)  # cleared

    me = (await client.get("/v1/session")).json()
    assert me == {
        "id": str(seeded.id),  # same account as before: history and claims are kept (BR-03)
        "username": "manager1@vn.example.com",
        "displayName": "SSO manager1@vn.example.com",
        "role": "ACCOUNTING_MANAGER",
        "companyName": "Demo Vietnam",
    }
    linked = await _user(db, "manager1@vn.example.com")
    assert (linked.idp_issuer, linked.idp_subject) == (ISSUER, claims.subject)
    stored = (
        await db.execute(
            select(UserSession).where(UserSession.token_hash == hash_token(client.cookies["saps_session"]))
        )
    ).scalar_one()
    assert stored.idp_session_id == claims.session_id
    assert stored.refresh_token_encrypted and "rt-" not in stored.refresh_token_encrypted  # encrypted at rest
    assert stored.id_token_encrypted and "id-token" not in stored.id_token_encrypted

    again = await sso.sign_in(claims)  # second sign-in: same account by subject
    assert (await again.get("/v1/session")).json()["id"] == str(seeded.id)


async def test_a_new_user_of_a_company_is_created(sso: Sso, db: AsyncSession) -> None:
    email = f"new-{uuid.uuid4().hex[:6]}@sg.example.com"
    client = await sso.sign_in(_claims(email))
    me = (await client.get("/v1/session")).json()
    assert me["username"] == email and me["companyName"] == "Demo Singapore"
    created = await _user(db, email)
    sg = (await db.execute(select(Tenant).where(Tenant.code == "sg"))).scalar_one()
    assert created.tenant_id == sg.id and created.role is Role.ACCOUNTING_MEMBER


# TS-03 / EC-01 to EC-06, EC-10 ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("claims", "reason"),
    [
        (_claims(groups=()), "no_company"),
        (_claims(groups=("/companies/vn", "/companies/sg")), "no_company"),
        (_claims(groups=("/companies/unknown",)), "no_company"),
        (_claims("member1@sg.example.com", groups=("/companies/vn",)), "wrong_domain"),
        (_claims(roles=("ACCOUNTING_MEMBER", "ACCOUNTING_MANAGER")), "no_role"),
    ],
)
async def test_refused_sign_ins_redirect_with_the_reason(
    sso: Sso, db: AsyncSession, claims: IdentityClaims, reason: str
) -> None:
    sso.idp.next_claims = claims
    client = sso.client()
    assert await sso.callback(client) == f"/?signIn={reason}"
    assert "saps_session" not in client.cookies
    assert (await client.get("/v1/session")).status_code == 401


async def test_an_email_of_another_identity_is_a_conflict(sso: Sso) -> None:  # EC-06
    email = f"twin-{uuid.uuid4().hex[:6]}@vn.example.com"
    await sso.sign_in(_claims(email))
    sso.idp.next_claims = _claims(email, subject="another-subject")
    assert await sso.callback(sso.client()) == "/?signIn=no_company"


async def test_cancelled_expired_and_foreign_return_paths(sso: Sso) -> None:  # EC-01, EC-02, EC-10
    client = sso.client()
    cancelled = await client.get("/v1/session/callback", params={"error": "access_denied", "state": "x"})
    assert cancelled.headers["location"] == "/?signIn=cancelled"
    no_cookie = await client.get("/v1/session/callback", params={"code": "c", "state": "x"})
    assert no_cookie.headers["location"] == "/?signIn=expired"
    await client.get("/v1/session/sign-in")
    wrong_state = await client.get("/v1/session/callback", params={"code": "c", "state": "other-tab"})
    assert wrong_state.headers["location"] == "/?signIn=expired"
    assert await sso.callback(sso.client(), code="bad") == "/?signIn=expired"
    assert await sso.callback(sso.client(), return_to="//evil.example/x") == "/"


async def test_an_unreachable_identity_provider_at_sign_in(sso: Sso) -> None:  # EC-07
    async def down(**_: str) -> str:
        raise IdentityProviderUnavailableError("down")

    sso.idp.authorization_url = down  # type: ignore[method-assign]
    response = await sso.client().get("/v1/session/sign-in")
    assert response.status_code == 302 and response.headers["location"] == "/?signIn=unavailable"


# TS-04 / BR-05, EC-08, EC-09 --------------------------------------------------------------------------------


async def test_an_expired_access_token_is_refreshed_under_row_level_security(
    sso: Sso, db: AsyncSession
) -> None:
    claims = _claims("member2@vn.example.com")
    client = await sso.sign_in(claims)
    await _expire_access_token(db, client)
    sso.idp.next_claims = replace(claims, roles=("ACCOUNTING_MANAGER",))  # role changed in Keycloak
    me = await client.get("/v1/session")
    assert me.status_code == 200 and me.json()["role"] == "ACCOUNTING_MANAGER"
    assert len(sso.idp.refreshed) == 1
    assert (await _user(db, "member2@vn.example.com")).role is Role.ACCOUNTING_MANAGER
    assert (await client.get("/v1/session")).status_code == 200
    assert len(sso.idp.refreshed) == 1  # the new access token is valid for 5 minutes


@pytest.mark.parametrize(
    "change",
    [
        lambda idp: setattr(idp, "refresh_error", IdentityRejectedError("invalid_grant")),
        lambda idp: setattr(
            idp, "next_claims", _claims("member1@sg.example.com", subject=idp.next_claims.subject)
        ),
    ],
    ids=["refresh-refused", "company-changed"],
)
async def test_a_refused_refresh_or_a_new_company_ends_the_session(
    sso: Sso, db: AsyncSession, change: Callable[[FakeIdp], None]
) -> None:
    client = await sso.sign_in(_claims(f"m-{uuid.uuid4().hex[:6]}@vn.example.com"))
    await _expire_access_token(db, client)
    change(sso.idp)
    assert (await client.get("/v1/session")).status_code == 401
    sso.idp.refresh_error = None
    assert (await client.get("/v1/session")).status_code == 401  # revoked, not only refused once


async def test_an_unreachable_identity_provider_keeps_the_session(sso: Sso, db: AsyncSession) -> None:
    client = await sso.sign_in(_claims(f"m-{uuid.uuid4().hex[:6]}@vn.example.com"))
    await _expire_access_token(db, client)
    sso.idp.refresh_error = IdentityProviderUnavailableError("down")
    response = await client.get("/v1/session")
    assert response.status_code == 503
    sso.idp.refresh_error = None
    assert (await client.get("/v1/session")).status_code == 200


async def test_timeouts_and_inactive_users(sso: Sso, db: AsyncSession) -> None:
    email = f"m-{uuid.uuid4().hex[:6]}@vn.example.com"
    client = await sso.sign_in(_claims(email))
    token = hash_token(client.cookies["saps_session"])
    now = datetime.now(UTC)
    await db.execute(
        update(UserSession)
        .where(UserSession.token_hash == token)
        .values(last_seen_at=now - timedelta(minutes=31))
    )
    await db.commit()
    assert (await client.get("/v1/session")).status_code == 401

    client = await sso.sign_in(_claims(email))
    await db.execute(update(UserAccount).where(UserAccount.username == email).values(is_active=False))
    await db.commit()
    assert (await client.get("/v1/session")).status_code == 401


# TS-05, TS-06 / BR-06, BR-07 --------------------------------------------------------------------------------


async def test_sign_out_returns_the_end_session_url(sso: Sso) -> None:
    client = await sso.sign_in(_claims("member1@my.example.com"))
    assert (await sso.client(origin=False).delete("/v1/session")).status_code == 403  # Origin check stays
    out = await client.delete("/v1/session")
    assert out.status_code == 200
    assert out.json()["logoutUrl"] == f"{ISSUER}/logout?id_token_hint=id-token-sub-member1@my.example.com"
    assert (await client.get("/v1/session")).status_code == 401


async def test_backchannel_logout_ends_the_sessions_of_that_idp_session(sso: Sso) -> None:
    vn = await sso.sign_in(_claims(f"bc-{uuid.uuid4().hex[:6]}@vn.example.com"))
    vn_again = await sso.sign_in(sso.idp.next_claims)  # a second session of the same Keycloak session
    sg = await sso.sign_in(_claims(f"bc-{uuid.uuid4().hex[:6]}@sg.example.com"))
    keycloak = sso.client(origin=False)  # no browser: exempt from the Origin check

    sso.idp.logout_sid = vn_again_sid = f"sid-{(await vn.get('/v1/session')).json()['username']}"
    response = await keycloak.post("/v1/session/backchannel-logout", data={"logout_token": "signed"})
    assert response.status_code == 200, (response.text, vn_again_sid)
    assert (await vn.get("/v1/session")).status_code == 401
    assert (await vn_again.get("/v1/session")).status_code == 401
    assert (await sg.get("/v1/session")).status_code == 200  # another company, another session

    sso.idp.logout_sid = "unknown-sid"
    assert (
        await keycloak.post("/v1/session/backchannel-logout", data={"logout_token": "t"})
    ).status_code == 200
    sso.idp.logout_sid = InvalidLogoutTokenError("forged")
    assert (
        await keycloak.post("/v1/session/backchannel-logout", data={"logout_token": "t"})
    ).status_code == 400
    sso.idp.logout_sid = IdentityProviderUnavailableError("keys")
    assert (
        await keycloak.post("/v1/session/backchannel-logout", data={"logout_token": "t"})
    ).status_code == 503
    assert (await keycloak.post("/v1/session/backchannel-logout", data={})).status_code == 400


# TS-07 / EC-13: migration on a PoC database -----------------------------------------------------------------


async def test_migration_0008_drops_passwords_and_revokes_poc_sessions(database_url: str) -> None:
    """On a database of its own, so that later migrations and the data of other tests do not interfere."""
    name = f"migration_{uuid.uuid4().hex[:8]}"
    admin = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = make_url(database_url).set(database=name).render_as_string(hide_password=False)
    engine = create_async_engine(url)
    try:
        up = alembic(url, "upgrade", "0007")  # the PoC schema with passwords
        assert up.returncode == 0, up.stderr
        suffix = uuid.uuid4().hex[:6]
        tenant = uuid.uuid4()
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO tenant (id, name, code, is_active, created_by, updated_by) "
                    "VALUES (:t, :n, :c, true, 'test', 'test')"
                ),
                {"t": tenant, "n": f"PoC {suffix}", "c": f"p{suffix}"},
            )
            await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant)})
            for username in (f"member1@{suffix}.example.com", f"manager2-{suffix}"):
                await conn.execute(
                    text(
                        "INSERT INTO user_account (id, tenant_id, username, display_name, password_hash, "
                        "role, is_active, created_by, updated_by) "
                        "VALUES (gen_random_uuid(), :t, :u, :u, '$argon2id$x', "
                        "'ACCOUNTING_MEMBER', true, 'test', 'test')"
                    ),
                    {"t": tenant, "u": username},
                )
            await conn.execute(
                text(
                    "INSERT INTO user_session (id, tenant_id, user_account_id, token_hash, expires_at, "
                    "last_seen_at, created_by, updated_by) "
                    "SELECT gen_random_uuid(), :t, id, :h, now() + interval '1 hour', now(), "
                    "'test', 'test' FROM user_account WHERE username = :u"
                ),
                {"t": tenant, "h": uuid.uuid4().hex, "u": f"member1@{suffix}.example.com"},
            )

        up = alembic(url, "upgrade", "0008")
        assert up.returncode == 0, up.stderr

        async with engine.begin() as conn:
            await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant)})
            users = dict((await conn.execute(text("SELECT username, email FROM user_account"))).all())
            open_sessions = (
                await conn.execute(text("SELECT count(*) FROM user_session WHERE revoked_at IS NULL"))
            ).scalar_one()
        assert users == {
            f"member1@{suffix}.example.com": f"member1@{suffix}.example.com",
            f"manager2-{suffix}": None,
        }
        assert open_sessions == 0
    finally:
        await engine.dispose()
        async with admin.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await admin.dispose()
