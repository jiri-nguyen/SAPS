"""Integration: seed and the sign-in flow on a real PostgreSQL (SAPS-27 TS-01..TS-09)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from saps.adapters.persistence.db import dispose_engines, session_factory
from saps.adapters.persistence.models import MatchingSettings, Tenant, UserAccount, UserSession
from saps.adapters.security.argon2_hasher import Argon2PasswordHasher
from saps.api.main import create_app
from saps.application.auth import hash_token
from saps.config import get_settings
from saps.seed import DEMO_TENANT
from saps.seed import _run as run_seed
from tests.integration.db_urls import use_database

pytestmark = pytest.mark.integration

ORIGIN = "http://localhost:5173"
PASSWORD = "integration-test-pw"  # noqa: S105  (test-only, throwaway container)


@pytest.fixture
async def db(database_url: str) -> AsyncIterator[AsyncSession]:
    await run_seed(database_url, PASSWORD)
    engine = create_async_engine(database_url)
    try:
        async with session_factory(engine)() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture
async def client(database_url: str, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncClient]:
    use_database(monkeypatch, database_url)
    monkeypatch.setenv("WEB_APP_ORIGIN", ORIGIN)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")  # the test client talks plain HTTP
    get_settings.cache_clear()
    transport = ASGITransport(app=create_app())
    try:
        async with AsyncClient(transport=transport, base_url="http://test", headers={"Origin": ORIGIN}) as c:
            yield c
    finally:
        await dispose_engines()
        get_settings.cache_clear()


async def _sign_in(client: AsyncClient, username: str = "member1", password: str = PASSWORD) -> str:
    response = await client.post("/v1/session", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.cookies["saps_session"]


async def test_seed_is_idempotent(database_url: str, db: AsyncSession) -> None:
    await run_seed(database_url, PASSWORD)
    # Other tests add their own tenants; the seed owns only the demo tenant.
    tenants = (await db.execute(select(Tenant).where(Tenant.name == DEMO_TENANT))).scalars().all()
    assert len(tenants) == 1
    tenant_id = tenants[0].id
    settings = (
        select(func.count()).select_from(MatchingSettings).where(MatchingSettings.tenant_id == tenant_id)
    )
    assert await db.scalar(settings) == 1
    users = (
        (
            await db.execute(
                select(UserAccount).where(UserAccount.tenant_id == tenant_id).order_by(UserAccount.username)
            )
        )
        .scalars()
        .all()
    )
    assert [u.username for u in users] == ["manager1", "manager2", "member1", "member2"]
    assert all(u.password_hash.startswith("$argon2id$") for u in users)
    assert Argon2PasswordHasher().verify(users[0].password_hash, PASSWORD)


async def test_sign_in_get_session_and_sign_out(client: AsyncClient, db: AsyncSession) -> None:
    response = await client.post("/v1/session", json={"username": "manager1", "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "manager1"
    assert body["displayName"] == "Accounting Manager 1"
    assert body["role"] == "ACCOUNTING_MANAGER"
    cookie = response.headers["set-cookie"]
    assert "saps_session=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert "Max-Age=28800" in cookie

    token = response.cookies["saps_session"]
    stored = await db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    assert stored is not None  # only the SHA-256 hash is stored, never the token
    assert (
        await db.scalar(select(func.count()).select_from(UserSession).where(UserSession.token_hash == token))
        == 0
    )

    me = await client.get("/v1/session")
    assert me.status_code == 200 and me.json()["role"] == "ACCOUNTING_MANAGER"

    out = await client.delete("/v1/session")
    assert out.status_code == 204
    client.cookies.set("saps_session", token)  # replaying the old cookie must fail
    assert (await client.get("/v1/session")).status_code == 401


@pytest.mark.parametrize("username", ["member1", "nobody"])
async def test_wrong_password_and_unknown_user_look_the_same(
    client: AsyncClient, db: AsyncSession, username: str
) -> None:
    response = await client.post("/v1/session", json={"username": username, "password": "wrong"})
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "Invalid username or password."
    assert "set-cookie" not in response.headers


async def test_inactive_user_cannot_sign_in_and_loses_open_sessions(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _sign_in(client, "member2")
    await db.execute(update(UserAccount).where(UserAccount.username == "member2").values(is_active=False))
    await db.commit()
    assert (await client.get("/v1/session")).status_code == 401
    response = await client.post("/v1/session", json={"username": "member2", "password": PASSWORD})
    assert response.status_code == 401
    # the next test's seed re-activates member2


async def test_idle_and_absolute_timeouts(client: AsyncClient, db: AsyncSession) -> None:
    now = datetime.now(UTC)
    token = await _sign_in(client)
    await db.execute(
        update(UserSession)
        .where(UserSession.token_hash == hash_token(token))
        .values(last_seen_at=now - timedelta(minutes=31))
    )
    await db.commit()
    assert (await client.get("/v1/session")).status_code == 401

    token = await _sign_in(client)
    await db.execute(
        update(UserSession)
        .where(UserSession.token_hash == hash_token(token))
        .values(expires_at=now - timedelta(seconds=1))
    )
    await db.commit()
    assert (await client.get("/v1/session")).status_code == 401


async def test_requests_without_session_or_from_another_origin_are_refused(client: AsyncClient) -> None:
    assert (await client.get("/v1/session")).status_code == 401
    client.cookies.set("saps_session", "not-a-real-token")
    assert (await client.get("/v1/session")).status_code == 401
    foreign = await client.post(
        "/v1/session",
        json={"username": "member1", "password": PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert foreign.status_code == 403


async def test_invalid_body_is_a_400_problem(client: AsyncClient) -> None:
    response = await client.post("/v1/session", json={"username": "", "password": PASSWORD})
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "username"
