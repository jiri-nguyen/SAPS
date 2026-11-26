"""Integration: processing calendar, On hold and its release on a real PostgreSQL (SAPS-52 TS-02 to TS-06)."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.persistence.db import dispose_engines, get_engine, session_factory
from saps.adapters.persistence.models import Invoice, InvoiceEvent, Tenant
from saps.adapters.persistence.processing_calendar_repository import (
    SqlHeldInvoiceRepository,
    SqlProcessingCalendarRepository,
)
from saps.adapters.persistence.sweeper_repository import SqlSweepUnitOfWork
from saps.application.processing_calendar import HoldReleaseService
from saps.application.sweeper import SweeperService
from saps.config import get_settings
from saps.domain.invoices import InvoiceStatus
from saps.domain.processing_calendar import CalendarRule, RuleKind
from tests.fakes import MemoryQueue
from tests.integration.api_world import Api
from tests.integration.db_urls import use_database
from tests.integration.pipeline import FIXTURES, new_tenant, new_world, process, uploaded

pytestmark = pytest.mark.integration

DS01 = FIXTURES / "ds-01/invoices/ds-01-trade-po.pdf"
DS12 = "ds-12/invoices/ds-12-price-outside-tolerance.pdf"


def _ago(**delta: float) -> datetime:
    return datetime.now(UTC) - timedelta(**delta)


def _today() -> date:
    return datetime.now(UTC).date()


def _closed_today() -> dict[str, Any]:
    return {"rules": [{"kind": "DATE", "date": _today().isoformat(), "label": "Test closure"}]}


async def _put(api: Api, who: str, body: dict[str, Any]) -> Any:
    return await api.request(who, "PUT", "/v1/processing-calendar", json=body)


async def _status(engine: AsyncEngine, invoice_id: uuid.UUID) -> InvoiceStatus:
    async with session_factory(engine)() as session:
        status = await session.scalar(select(Invoice.status).where(Invoice.id == invoice_id))
    assert status is not None
    return status


async def _actions(engine: AsyncEngine, invoice_id: uuid.UUID) -> list[tuple[str, str]]:
    async with session_factory(engine)() as session:
        rows = await session.execute(
            select(InvoiceEvent.action, InvoiceEvent.actor)
            .where(InvoiceEvent.invoice_id == invoice_id)
            .order_by(InvoiceEvent.occurred_at, InvoiceEvent.created_at)
        )
        return [(a, b) for a, b in rows]


# TS-04 / BR-07, BR-08, EC-10: the calendar API ------------------------------------------------------------


async def test_a_new_company_is_open_and_both_roles_read_the_calendar(api: Api) -> None:
    for who in ("alice", "manager"):
        body = (await api.request(who, "GET", "/v1/processing-calendar")).json()
        assert body["rules"] == [] and body["closedToday"] is False and body["openAgainOn"] is None
        assert body["timeZone"] == "UTC" and body["updatedAt"] is None and body["updatedBy"] is None


async def test_the_manager_replaces_the_rules_and_a_member_cannot(api: Api) -> None:
    rules = [
        {"kind": "MONTHLY_RANGE", "fromDay": 25, "toDay": 5, "label": "Month end"},
        {"kind": "WEEKDAY", "weekday": 6},
        {"kind": "WEEKDAY", "weekday": 7},
        {"kind": "DATE", "date": "2027-04-30", "label": "Public holiday"},
    ]
    assert (await _put(api, "alice", {"rules": rules})).status_code == 403
    response = await _put(api, "manager", {"rules": rules})
    assert response.status_code == 200, response.text
    body = response.json()
    assert [r["kind"] for r in body["rules"]] == ["MONTHLY_RANGE", "WEEKDAY", "WEEKDAY", "DATE"]  # in order
    assert body["rules"][0] == {
        "kind": "MONTHLY_RANGE",
        "fromDay": 25,
        "toDay": 5,
        "weekday": None,
        "date": None,
        "label": "Month end",
    }
    assert body["rules"][3]["date"] == "2027-04-30" and body["updatedBy"] == "Manager"
    assert (await api.request("alice", "GET", "/v1/processing-calendar")).json()["rules"] == body["rules"]

    again = await _put(api, "manager", {"rules": [rules[1]]})  # replaces all of them (BR-07)
    assert [r["kind"] for r in again.json()["rules"]] == ["WEEKDAY"]
    assert (await _put(api, "manager", {"rules": []})).json()["rules"] == []


async def test_today_closed_names_the_first_open_day(api: Api) -> None:
    body = (await _put(api, "manager", _closed_today())).json()
    assert body["closedToday"] is True and body["openAgainOn"] == (_today() + timedelta(days=1)).isoformat()
    every_day = {"rules": [{"kind": "WEEKDAY", "weekday": n} for n in range(1, 8)]}
    body = (await _put(api, "manager", every_day)).json()
    assert body["closedToday"] is True and body["openAgainOn"] is None  # until further notice (EC-05)


@pytest.mark.parametrize(
    ("rule", "field"),
    [
        ({"kind": "MONTHLY_RANGE", "fromDay": 0, "toDay": 5}, "rules[1].fromDay"),
        ({"kind": "MONTHLY_RANGE", "fromDay": 25}, "rules[1].toDay"),
        ({"kind": "WEEKDAY", "weekday": 8}, "rules[1].weekday"),
        ({"kind": "WEEKDAY"}, "rules[1].weekday"),
        ({"kind": "DATE"}, "rules[1].date"),
        ({"kind": "DATE", "date": "2027-04-30", "weekday": 1}, "rules[1]"),
    ],
)
async def test_invalid_rules_are_refused_and_nothing_is_saved(
    api: Api, rule: dict[str, Any], field: str
) -> None:
    assert (await _put(api, "manager", {"rules": [{"kind": "WEEKDAY", "weekday": 1}]})).status_code == 200
    response = await _put(api, "manager", {"rules": [{"kind": "WEEKDAY", "weekday": 2}, rule]})
    assert response.status_code == 422, response.text
    assert field in {e["field"] for e in response.json()["errors"]}
    saved = (await api.request("manager", "GET", "/v1/processing-calendar")).json()["rules"]
    assert [r["weekday"] for r in saved] == [1]  # the old calendar is still in force


async def test_malformed_bodies_are_refused(api: Api) -> None:
    for body in ({}, {"rules": [{"kind": "YEARLY"}]}, {"rules": [{"kind": "DATE", "date": "tomorrow"}]}):
        assert (await _put(api, "manager", body)).status_code == 400
    too_many = {"rules": [{"kind": "WEEKDAY", "weekday": 1}] * 101}
    assert (await _put(api, "manager", too_many)).status_code == 422


async def test_each_company_has_its_own_calendar(api: Api, engine: AsyncEngine) -> None:
    other = await new_world(engine)
    api.users["outsider_manager"] = other.manager
    await _put(api, "manager", _closed_today())
    theirs = (await api.request("outsider_manager", "GET", "/v1/processing-calendar")).json()
    assert theirs["rules"] == [] and theirs["closedToday"] is False  # row-level security


# TS-02 / BR-03, BR-06, EC-04, EC-06: the hold -------------------------------------------------------------


async def test_a_closed_day_holds_the_invoice_and_process_now_lets_it_through(
    api: Api, engine: AsyncEngine
) -> None:
    await _put(api, "manager", _closed_today())
    invoice_id = await uploaded(engine, DS01, api.world.tenant)

    outcome = await process(engine, invoice_id)
    assert outcome is not None and outcome.held and outcome.matching is None
    assert await _status(engine, invoice_id) is InvoiceStatus.ON_HOLD
    assert await _actions(engine, invoice_id) == [("HOLD", "system")]
    held = await api.get(invoice_id)
    assert held["status"] == "ON_HOLD" and held["lines"] == []  # nothing extracted

    assert (
        await api.request("alice", "POST", f"/v1/invoices/{invoice_id}/release")
    ).status_code == 403  # a member
    released = await api.request("manager", "POST", f"/v1/invoices/{invoice_id}/release")
    assert released.status_code == 200 and released.json()["status"] == "UPLOADED"
    assert api.queue.sent[-1] == invoice_id and api.queue.tenant_of[invoice_id] == api.world.tenant[0]
    assert await _actions(engine, invoice_id) == [
        ("HOLD", "system"),
        ("RELEASE_HOLD", api.world.manager.username),
    ]

    again = await api.request("manager", "POST", f"/v1/invoices/{invoice_id}/release")
    assert again.status_code == 409  # EC-07

    outcome = await process(engine, invoice_id)  # the closed day does not hold it again
    assert outcome is not None and not outcome.held and outcome.matching is not None
    assert await _status(engine, invoice_id) is InvoiceStatus.POSTING


async def test_an_open_day_processes_as_before(api: Api, engine: AsyncEngine) -> None:
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    await _put(api, "manager", {"rules": [{"kind": "DATE", "date": tomorrow}]})
    invoice_id = await uploaded(engine, DS01, api.world.tenant)
    outcome = await process(engine, invoice_id)
    assert outcome is not None and not outcome.held
    assert await _status(engine, invoice_id) is InvoiceStatus.POSTING


async def test_a_message_sent_again_does_not_change_a_held_invoice(api: Api, engine: AsyncEngine) -> None:
    await _put(api, "manager", _closed_today())
    invoice_id = await uploaded(engine, DS01, api.world.tenant)
    await process(engine, invoice_id)
    assert await process(engine, invoice_id) is None  # a stale message: the invoice is no longer Uploaded
    assert await _status(engine, invoice_id) is InvoiceStatus.ON_HOLD


async def test_process_now_is_refused_for_other_invoices_and_other_companies(
    api: Api, engine: AsyncEngine
) -> None:
    other = await new_world(engine)
    api.users["outsider_manager"] = other.manager
    await _put(api, "manager", _closed_today())
    invoice_id = await uploaded(engine, DS01, api.world.tenant)
    await process(engine, invoice_id)
    assert (
        await api.request("outsider_manager", "POST", f"/v1/invoices/{invoice_id}/release")
    ).status_code == 404
    missing = uuid.uuid4()
    assert (await api.request("manager", "POST", f"/v1/invoices/{missing}/release")).status_code == 404
    live = await api.sample(DS12, processed=False)
    assert (await api.request("manager", "POST", f"/v1/invoices/{live}/release")).status_code == 409


# TS-06 / BR-04, EC-12: the work in progress goes on -------------------------------------------------------


async def test_exception_handling_and_rematching_go_on_during_a_closed_period(api: Api) -> None:
    invoice_id = await api.sample(DS12)  # EX6, processed before the closure
    assert (await api.get(invoice_id))["status"] == "EXCEPTION"
    await _put(api, "manager", _closed_today())
    assert (await api.claim("alice", invoice_id)).status_code == 200
    assert (await api.reject("alice", invoice_id)).status_code == 200
    assert (await api.get(invoice_id))["status"] == "REJECTED"


# TS-03 / BR-05, BR-07, EC-09, EC-11: the release timer ----------------------------------------------------


async def _held_invoices(
    engine: AsyncEngine, tenant: tuple[uuid.UUID, uuid.UUID], count: int
) -> list[uuid.UUID]:
    """`count` invoices On hold, the first one the oldest."""
    ids = []
    for index in range(count):
        invoice_id = await uploaded(engine, DS01, tenant)
        async with session_factory(engine)() as session, session.begin():
            await session.execute(
                update(Invoice)
                .where(Invoice.id == invoice_id)
                .values(status=InvoiceStatus.ON_HOLD, created_at=_ago(hours=10 - index))
            )
        ids.append(invoice_id)
    return ids


async def test_the_timer_releases_open_companies_oldest_first_in_batches(
    engine: AsyncEngine, app_engine: AsyncEngine
) -> None:
    open_company, closed_company = await new_tenant(engine), await new_tenant(engine)
    open_ids = await _held_invoices(engine, open_company, 5)
    closed_ids = await _held_invoices(engine, closed_company, 2)
    async with session_factory(app_engine, closed_company[0])() as session, session.begin():
        await SqlProcessingCalendarRepository(session).replace(
            closed_company[0], [CalendarRule(RuleKind.DATE, day=_today())], "test"
        )
    queue = MemoryQueue()
    service = HoldReleaseService(SqlHeldInvoiceRepository(app_engine), queue, lambda: datetime.now(UTC), 3)

    await service.release_due()
    mine = [i for i in queue.sent if i in open_ids + closed_ids]
    assert mine == open_ids[:3]  # a batch of 3, the oldest first; the closed company waits
    assert {queue.tenant_of[i] for i in mine} == {open_company[0]}
    assert [await _status(engine, i) for i in open_ids] == [InvoiceStatus.UPLOADED] * 3 + [
        InvoiceStatus.ON_HOLD
    ] * 2
    assert [await _status(engine, i) for i in closed_ids] == [InvoiceStatus.ON_HOLD] * 2
    assert await _actions(engine, open_ids[0]) == [("RELEASE_HOLD", "system")]

    await service.release_due()
    assert [i for i in queue.sent if i in open_ids] == open_ids  # the next batch, the rest

    async with session_factory(app_engine, closed_company[0])() as session, session.begin():  # BR-07, EC-09
        await SqlProcessingCalendarRepository(session).replace(closed_company[0], [], "test")
    await service.release_due()
    assert [i for i in queue.sent if i in closed_ids] == closed_ids


async def test_a_released_invoice_is_not_released_twice_and_the_lock_serializes_ticks(
    engine: AsyncEngine, app_engine: AsyncEngine
) -> None:
    company = await new_tenant(engine)
    ids = await _held_invoices(engine, company, 3)
    repository = SqlHeldInvoiceRepository(app_engine)
    async with repository.try_lock() as first:
        async with repository.try_lock() as second:
            assert (first, second) == (True, False)  # EC-11: one process releases at a time
    queue = MemoryQueue()
    ticks = [HoldReleaseService(repository, queue, lambda: datetime.now(UTC), 10) for _ in range(3)]
    await asyncio.gather(
        *(t.release_due() for t in ticks)
    )  # even without the lock: SKIP LOCKED, no double release
    sent = [i for i in queue.sent if i in ids]
    assert sorted(sent) == sorted(ids)


async def test_only_active_companies_are_considered(engine: AsyncEngine, app_engine: AsyncEngine) -> None:
    active, inactive = await new_tenant(engine), await new_tenant(engine)
    async with session_factory(engine)() as session, session.begin():
        await session.execute(update(Tenant).where(Tenant.id == inactive[0]).values(is_active=False))
    listed = {c.tenant_id for c in await SqlHeldInvoiceRepository(app_engine).list_companies()}
    assert active[0] in listed and inactive[0] not in listed


# BR-03: On hold is not a stuck status ---------------------------------------------------------------------


async def test_the_sweeper_ignores_invoices_on_hold(engine: AsyncEngine) -> None:
    tenant = await new_tenant(engine)
    held = (await _held_invoices(engine, tenant, 1))[0]
    async with session_factory(engine)() as session, session.begin():
        await session.execute(update(Invoice).where(Invoice.id == held).values(updated_at=_ago(days=2)))
    queue = MemoryQueue()
    service = SweeperService(SqlSweepUnitOfWork(session_factory(engine)), queue, 60, 100, 3)
    await service.sweep()
    assert held not in queue.sent and held not in queue.rematch
    assert await _status(engine, held) is InvoiceStatus.ON_HOLD


# The worker: the job holds, the timer releases ------------------------------------------------------------


@pytest.fixture
async def worker_database(database_url: str, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    use_database(monkeypatch, database_url)
    try:
        yield
    finally:
        await dispose_engines()
        get_settings.cache_clear()


async def test_the_job_holds_on_a_closed_day_and_logs_it(
    api: Api, engine: AsyncEngine, worker_database: None, caplog: pytest.LogCaptureFixture
) -> None:
    from saps.worker.jobs import run_processing

    await _put(api, "manager", _closed_today())
    invoice_id = await uploaded(engine, DS01, api.world.tenant)
    caplog.set_level("INFO")
    outcome = await run_processing(invoice_id, api.world.tenant[0])
    assert outcome is not None and outcome.held
    assert "invoice_held" in [r.getMessage() for r in caplog.records]
    assert await _status(engine, invoice_id) is InvoiceStatus.ON_HOLD


async def test_the_release_tick_releases_an_open_company_and_never_raises(
    engine: AsyncEngine,
    worker_database: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from saps.worker.hold_release import run_hold_release

    company = await new_tenant(engine)
    held = (await _held_invoices(engine, company, 2))[0]
    queue = MemoryQueue()
    settings = get_settings()
    await run_hold_release(settings, queue)
    assert held in queue.sent and await _status(engine, held) is InvoiceStatus.UPLOADED

    repository = SqlHeldInvoiceRepository(get_engine(settings.app_database_url))
    queue = MemoryQueue()
    async with repository.try_lock() as got:  # another process releases now: this tick does nothing
        assert got
        await run_hold_release(settings, queue)
    assert queue.sent == []

    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+psycopg://nobody:x@127.0.0.1:1/none")
    get_settings.cache_clear()
    caplog.set_level("ERROR")
    await run_hold_release(get_settings(), queue)  # the database is not reachable: logged, not raised
    assert "hold_release_failed" in [r.getMessage() for r in caplog.records]
