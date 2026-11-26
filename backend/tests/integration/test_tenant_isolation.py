"""Integration: SAPS-41 tenant isolation with row-level security on a real PostgreSQL (TS-01 … TS-07)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.persistence.db import dispose_engines, session_factory
from saps.adapters.persistence.models import Approval, InvoiceEvent, UserSession
from saps.adapters.persistence.sweeper_repository import SqlSweepUnitOfWork
from saps.application.sweeper import SweeperService
from saps.config import get_settings
from saps.domain.invoices import ApprovalDecision, InvoiceStatus, NotificationType
from tests.fakes import MemoryQueue
from tests.integration.api_world import Api
from tests.integration.db_urls import use_database
from tests.integration.pipeline import ERP, FIXTURES, World, new_world, process, uploaded

pytestmark = pytest.mark.integration

TENANT_TABLES = (
    "user_account",
    "user_session",
    "matching_settings",
    "invoice",
    "invoice_line",
    "invoice_exception",
    "approval",
    "invoice_event",
    "notification",
)
# `inbound_mail` (SAPS-45) and `processing_calendar_rule` (SAPS-52) are not filled by these scenarios;
# test_mail_intake and test_processing_calendar check them.
CATALOG_TABLES = (*TENANT_TABLES, "inbound_mail", "processing_calendar_rule")
DS03 = FIXTURES / "ds-03/invoices/ds-03-above-threshold.pdf"  # Pending approval
DS12 = FIXTURES / "ds-12/invoices/ds-12-price-outside-tolerance.pdf"  # Exception EX6


@dataclass
class Company:
    world: World
    exception_invoice: uuid.UUID
    waiting_invoice: uuid.UUID

    @property
    def id(self) -> uuid.UUID:
        return self.world.tenant[0]


async def _company(engine: AsyncEngine) -> Company:
    """A company with rows in every tenant-owned table (set up as the owner)."""
    world = await new_world(engine)
    exception_invoice = await uploaded(engine, DS12, world.tenant)
    await process(engine, exception_invoice)
    waiting = await uploaded(engine, DS03, world.tenant)
    await process(engine, waiting)
    now = datetime.now(UTC)
    async with session_factory(engine)() as session, session.begin():
        session.add(
            UserSession(
                tenant_id=world.tenant[0], user_account_id=world.alice.user_id,
                token_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                expires_at=now + timedelta(hours=1), last_seen_at=now,
            )
        )  # fmt: skip
        session.add(
            Approval(
                tenant_id=world.tenant[0], invoice_id=waiting, decided_by=world.manager.user_id,
                decision=ApprovalDecision.APPROVED, decided_at=now,
            )
        )  # fmt: skip
    return Company(world, exception_invoice, waiting)


@pytest.fixture
async def companies(engine: AsyncEngine) -> tuple[Company, Company]:
    return await _company(engine), await _company(engine)


async def _count(engine: AsyncEngine, table: str, tenant: uuid.UUID, as_tenant: uuid.UUID | None) -> int:
    async with session_factory(engine, as_tenant)() as session:
        count: int = (
            await session.execute(text(f"SELECT count(*) FROM {table} WHERE tenant_id = :t"), {"t": tenant})  # noqa: S608
        ).scalar_one()
    return count


# TS-01 / BR-01, BR-03, EC-01 ------------------------------------------------------------------------------


@pytest.mark.parametrize("table", TENANT_TABLES)
async def test_a_company_sees_only_its_own_rows(
    engine: AsyncEngine, app_engine: AsyncEngine, companies: tuple[Company, Company], table: str
) -> None:
    a, b = companies
    assert await _count(engine, table, b.id, None) > 0  # the owner (superuser) sees B's rows
    assert await _count(app_engine, table, a.id, a.id) > 0
    assert await _count(app_engine, table, b.id, a.id) == 0  # even with an explicit filter on B


@pytest.mark.parametrize("table", TENANT_TABLES)
async def test_a_company_cannot_change_rows_of_another(
    app_engine: AsyncEngine, companies: tuple[Company, Company], table: str
) -> None:
    a, b = companies
    async with session_factory(app_engine, a.id)() as session, session.begin():
        changed = await session.execute(
            text(f"UPDATE {table} SET updated_by = 'intruder' WHERE tenant_id = :t"),  # noqa: S608
            {"t": b.id},
        )
    assert changed.rowcount == 0  # type: ignore[attr-defined]


async def test_writing_a_row_for_another_company_is_refused(
    app_engine: AsyncEngine, companies: tuple[Company, Company]
) -> None:  # EC-03
    a, b = companies
    with pytest.raises(DBAPIError, match="row-level security"):
        async with session_factory(app_engine, a.id)() as session, session.begin():
            session.add(
                InvoiceEvent(
                    tenant_id=b.id, invoice_id=b.exception_invoice, status_to=InvoiceStatus.EXCEPTION,
                    action="INTRUDE", actor="intruder",
                )
            )  # fmt: skip
    with pytest.raises(DBAPIError, match="row-level security"):
        async with session_factory(app_engine, a.id)() as session, session.begin():
            await session.execute(
                text("UPDATE invoice SET tenant_id = :b WHERE id = :id"),
                {"b": b.id, "id": a.exception_invoice},
            )


# TS-02 / BR-02, EC-02 ------------------------------------------------------------------------------------


@pytest.mark.parametrize("table", TENANT_TABLES)
async def test_without_a_company_nothing_is_visible(
    app_engine: AsyncEngine, companies: tuple[Company, Company], table: str
) -> None:
    a, _ = companies
    assert await _count(app_engine, table, a.id, None) == 0


async def test_without_a_company_nothing_can_be_written(
    app_engine: AsyncEngine, companies: tuple[Company, Company]
) -> None:
    a, _ = companies
    with pytest.raises(DBAPIError, match="row-level security"):
        async with session_factory(app_engine)() as session, session.begin():
            session.add(
                InvoiceEvent(
                    tenant_id=a.id, invoice_id=a.exception_invoice, status_to=InvoiceStatus.EXCEPTION,
                    action="NO_COMPANY", actor="nobody",
                )
            )  # fmt: skip


# TS-03 / EC-07: catalog check ----------------------------------------------------------------------------


async def test_every_table_with_a_tenant_column_has_row_level_security(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    """
                    SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
                           EXISTS (SELECT 1 FROM pg_policies p
                                   WHERE p.tablename = c.relname
                                     AND p.policyname = 'tenant_isolation') AS has_policy
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
                    WHERE c.relkind = 'r'
                      AND EXISTS (SELECT 1 FROM information_schema.columns col
                                  WHERE col.table_schema = 'public' AND col.table_name = c.relname
                                    AND col.column_name = 'tenant_id')
                    """
                )
            )
        ).all()
    assert sorted(r.relname for r in rows) == sorted(CATALOG_TABLES)
    missing = [r.relname for r in rows if not (r.relrowsecurity and r.relforcerowsecurity and r.has_policy)]
    assert missing == []


async def test_the_application_roles_cannot_bypass_and_only_the_system_role_can(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        roles = dict(
            (
                await conn.execute(
                    text(
                        "SELECT rolname, rolbypassrls FROM pg_roles "
                        "WHERE rolname IN ('saps_app', 'saps_system')"
                    )
                )
            ).all()
        )
    assert roles == {"saps_app": False, "saps_system": True}


# TS-04 / BR-05: lookups before the company is known -------------------------------------------------------


async def test_the_lookup_functions_return_one_row_with_its_company(
    engine: AsyncEngine, app_engine: AsyncEngine, companies: tuple[Company, Company]
) -> None:
    a, b = companies
    async with engine.connect() as conn:
        token_hash = (
            await conn.execute(text("SELECT token_hash FROM user_session WHERE tenant_id = :t"), {"t": b.id})
        ).scalar_one()
    async with app_engine.connect() as conn:  # no company set
        session_row = (
            await conn.execute(text("SELECT * FROM saps_find_session(:h)"), {"h": token_hash})
        ).one()
        user_row = (
            await conn.execute(
                text("SELECT * FROM saps_find_user_for_sign_in('iss', 'sub', :u)"),
                {"u": a.world.alice.username},
            )
        ).one()
        assert (await conn.execute(text("SELECT * FROM saps_find_session('nope')"))).first() is None
    assert session_row.tenant_id == b.id
    assert (user_row.user_id, user_row.tenant_id) == (a.world.alice.user_id, a.id)


async def test_only_the_application_role_may_run_the_lookups(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        grantees = {
            row.grantee
            for row in await conn.execute(
                text(
                    "SELECT grantee FROM information_schema.routine_privileges "
                    "WHERE routine_name IN "
                    "('saps_find_session', 'saps_find_user_for_sign_in', 'saps_find_idp_sessions') "
                    "AND privilege_type = 'EXECUTE'"
                )
            )
        }
    assert "PUBLIC" not in grantees and "saps_app" in grantees


# TS-05 / BR-01, EC-04: two companies through the API --------------------------------------------------------


async def test_two_companies_through_the_api(api: Api, engine: AsyncEngine) -> None:
    other = await _company(engine)
    api.users["outsider_member"] = other.world.alice
    api.users["outsider_manager"] = other.world.manager
    mine = await api.sample("ds-12/invoices/ds-12-price-outside-tolerance.pdf")

    for who, foreign in (("alice", other.exception_invoice), ("manager", other.waiting_invoice)):
        assert (await api.request(who, "GET", f"/v1/invoices/{foreign}")).status_code == 404
        assert (await api.request(who, "GET", f"/v1/invoices/{foreign}/events")).status_code == 404
        listed = {
            i["id"] for i in (await api.request(who, "GET", "/v1/invoices?pageSize=100")).json()["items"]
        }
        assert str(foreign) not in listed
    assert (await api.claim("alice", other.exception_invoice)).status_code == 404

    outsider_list = (await api.request("outsider_member", "GET", "/v1/invoices?pageSize=100")).json()["items"]
    assert str(mine) not in {i["id"] for i in outsider_list}
    outsider_notes = (await api.request("outsider_member", "GET", "/v1/notifications?pageSize=100")).json()
    assert {n["invoiceId"] for n in outsider_notes["items"]}.isdisjoint({str(mine)})

    assert (
        await api.request(
            "manager",
            "PUT",
            "/v1/matching-settings",
            json={"priceToleranceUsd": "1.00", "approvalThresholdUsd": "300"},
        )
    ).status_code == 200
    theirs = (await api.request("outsider_manager", "GET", "/v1/matching-settings")).json()
    assert theirs["priceToleranceUsd"] in {
        "0.5",
        "0.5000",
        "0.50",
    }  # the other company's settings are untouched


async def test_an_upload_stores_the_file_under_the_company_and_queues_it(api: Api) -> None:  # BR-06
    pdf = (FIXTURES / "ds-01/invoices/ds-01-trade-po.pdf").read_bytes()
    response = await api.request(
        "alice",
        "POST",
        "/v1/invoices",
        headers={"Idempotency-Key": uuid.uuid4().hex},
        files={"file": ("ds-01.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 202, response.text
    invoice_id = uuid.UUID(response.json()["id"])
    key = await api.storage_key(invoice_id)
    assert key.startswith(f"tenants/{api.world.tenant[0]}/invoices/{invoice_id}/")
    assert api.queue.tenant_of[invoice_id] == api.world.tenant[0]


# TS-06 / BR-06, EC-05, EC-06: the worker ----------------------------------------------------------------


async def test_worker_jobs_run_as_the_company_of_the_message(
    engine: AsyncEngine, database_url: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from saps.worker import jobs
    from saps.worker.jobs import run_processing

    monkeypatch.setattr(
        jobs, "erp_adapter", lambda name, fixtures_dir: ERP
    )  # test companies use the vn catalogue

    a, b = await _company(engine), await _company(engine)
    with_company = await uploaded(
        engine, FIXTURES / "ds-17/invoices/ds-17-rejected-at-review.pdf", a.world.tenant
    )
    old_message = await uploaded(engine, FIXTURES / "ds-02/invoices/ds-02-non-trade-po.jpg", a.world.tenant)
    wrong_company = await uploaded(
        engine, FIXTURES / "ds-06/invoices/ds-06-price-within-tolerance.pdf", a.world.tenant
    )
    use_database(monkeypatch, database_url)
    caplog.set_level("INFO")
    try:
        outcome = await run_processing(with_company, a.id)
        assert outcome is not None and outcome.matching is not None
        assert outcome.matching.status is InvoiceStatus.POSTING

        outcome = await run_processing(old_message)  # sent before SAPS-41: no company (EC-05)
        assert outcome is not None and outcome.tenant_id == a.id
        assert "message_without_tenant" in [r.getMessage() for r in caplog.records]

        assert await run_processing(wrong_company, b.id) is None  # invisible to company B (EC-06)
        assert await run_processing(uuid.uuid4()) is None  # unknown invoice
    finally:
        await dispose_engines()
        get_settings.cache_clear()
    async with engine.connect() as conn:
        status = (
            await conn.execute(text("SELECT status FROM invoice WHERE id = :id"), {"id": wrong_company})
        ).scalar_one()
    assert status == "UPLOADED"


# TS-07 / BR-04: the sweeper sees every company -------------------------------------------------------------


async def test_the_sweeper_sees_every_company_and_sends_each_company(
    system_engine: AsyncEngine, engine: AsyncEngine
) -> None:
    a, b = await _company(engine), await _company(engine)
    stuck = {}
    for company in (a, b):
        invoice_id = await uploaded(
            engine, FIXTURES / "ds-05/invoices/ds-05-two-pos.pdf", company.world.tenant
        )
        async with session_factory(engine)() as session, session.begin():
            await session.execute(
                text("UPDATE invoice SET updated_at = now() - interval '2 days' WHERE id = :id"),
                {"id": invoice_id},
            )
        stuck[invoice_id] = company.id
    queue = MemoryQueue()
    result = await SweeperService(SqlSweepUnitOfWork(session_factory(system_engine)), queue, 3600).sweep()
    assert result is not None and set(stuck) <= {r.invoice_id for r in result.resent}
    assert {i: queue.tenant_of[i] for i in stuck} == stuck


async def test_notifications_stay_inside_the_company(api: Api, engine: AsyncEngine) -> None:
    other = await _company(engine)
    api.users["outsider_member"] = other.world.alice
    await api.sample("ds-12/invoices/ds-12-price-outside-tolerance.pdf")
    mine = (await api.request("alice", "GET", "/v1/notifications?pageSize=100")).json()["items"]
    theirs = (await api.request("outsider_member", "GET", "/v1/notifications?pageSize=100")).json()["items"]
    assert {n["type"] for n in mine} == {NotificationType.EXCEPTION_RAISED.value}
    assert {n["id"] for n in mine}.isdisjoint({n["id"] for n in theirs})
    foreign = theirs[0]["id"]
    assert (await api.request("alice", "POST", f"/v1/notifications/{foreign}/read")).status_code == 404
