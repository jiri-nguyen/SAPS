"""Integration: SAPS-37 sweeper on a real PostgreSQL (TS-02 … TS-06, TS-09)."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.models import Invoice, InvoiceEvent
from saps.adapters.persistence.sweeper_repository import SWEEPER_LOCK_KEY, SqlSweepUnitOfWork
from saps.application.sweeper import SweeperService, SweepResult
from saps.domain.invoices import InvoiceStatus
from tests.fakes import MemoryQueue
from tests.integration.api_world import Api
from tests.integration.pipeline import FIXTURES, new_tenant, process, uploaded

pytestmark = pytest.mark.integration

DS01 = FIXTURES / "ds-01/invoices/ds-01-trade-po.pdf"
DS12 = "ds-12/invoices/ds-12-price-outside-tolerance.pdf"
STUCK_AFTER = 3600  # the test invoices are a day old, the invoices of other tests are minutes old


@pytest.fixture(autouse=True)
async def calm_database(engine: AsyncEngine) -> AsyncIterator[None]:
    """Invoices that other tests left stuck must not be swept here."""
    async with session_factory(engine)() as session, session.begin():
        await session.execute(
            update(Invoice)
            .where(
                Invoice.status.in_([InvoiceStatus.UPLOADED, InvoiceStatus.MATCHING]),
                Invoice.updated_at < datetime.now(UTC) - timedelta(seconds=STUCK_AFTER),
            )
            .values(updated_at=datetime.now(UTC))
        )
    yield


async def _invoice(
    engine: AsyncEngine, status: InvoiceStatus = InvoiceStatus.UPLOADED, age: timedelta = timedelta(days=1)
) -> uuid.UUID:
    invoice_id = await uploaded(engine, DS01)
    async with session_factory(engine)() as session, session.begin():
        await session.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(status=status, updated_at=datetime.now(UTC) - age)
        )
    return invoice_id


async def _sweep_result(
    engine: AsyncEngine, queue: MemoryQueue, limit: int = 100, max_resends: int = 3
) -> SweepResult | None:
    service = SweeperService(
        SqlSweepUnitOfWork(session_factory(engine)), queue, STUCK_AFTER, limit, max_resends
    )
    return await service.sweep()


async def _sweep(engine: AsyncEngine, queue: MemoryQueue, limit: int = 100) -> list[uuid.UUID] | None:
    result = await _sweep_result(engine, queue, limit)
    return None if result is None else [item.invoice_id for item in result.resent]


async def _events(engine: AsyncEngine, invoice_id: uuid.UUID, action: str = "RESEND") -> list[InvoiceEvent]:
    async with session_factory(engine)() as session:
        rows = await session.execute(
            select(InvoiceEvent).where(InvoiceEvent.invoice_id == invoice_id, InvoiceEvent.action == action)
        )
        return list(rows.scalars())


async def _age(engine: AsyncEngine, invoice_id: uuid.UUID) -> None:
    async with session_factory(engine)() as session, session.begin():
        await session.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(updated_at=datetime.now(UTC) - timedelta(days=1))
        )


async def _updated_at(engine: AsyncEngine, invoice_id: uuid.UUID) -> datetime:
    async with session_factory(engine)() as session:
        value = await session.scalar(select(Invoice.updated_at).where(Invoice.id == invoice_id))
    assert value is not None
    return value


async def _status(engine: AsyncEngine, invoice_id: uuid.UUID) -> InvoiceStatus:
    async with session_factory(engine)() as session:
        value = await session.scalar(select(Invoice.status).where(Invoice.id == invoice_id))
    assert value is not None
    return value


# TS-02 -----------------------------------------------------------------------------------------------


async def test_only_stuck_uploaded_and_matching_invoices_are_sent_again(engine: AsyncEngine) -> None:
    uploaded_old = await _invoice(engine)
    matching_old = await _invoice(engine, InvoiceStatus.MATCHING)
    fresh = await _invoice(engine, age=timedelta(seconds=5))
    handled = [
        await _invoice(engine, status) for status in (InvoiceStatus.EXCEPTION, InvoiceStatus.COMPLETED)
    ]
    queue = MemoryQueue()

    resent = await _sweep(engine, queue)

    assert resent is not None and set(resent) == {uploaded_old, matching_old}  # BR-01, BR-02
    assert (queue.sent, queue.rematch) == ([uploaded_old], [matching_old])
    for invoice_id, message in ((uploaded_old, "process_invoice"), (matching_old, "rematch_invoice")):
        [event] = await _events(engine, invoice_id)  # BR-04
        assert (event.actor, event.status_from, event.status_to, event.details) == (
            "system",
            event.status_to,
            event.status_to,
            {"message": message},
        )
        assert await _updated_at(engine, invoice_id) > datetime.now(UTC) - timedelta(minutes=1)
    for untouched in (fresh, *handled):
        assert await _events(engine, untouched) == []

    assert await _sweep(engine, queue) == []  # the next tick waits another stuck period
    assert (queue.sent, queue.rematch) == ([uploaded_old], [matching_old])


async def test_a_resent_invoice_is_processed_to_pending_review(engine: AsyncEngine) -> None:
    invoice_id = await _invoice(engine)  # the message of the upload was lost (SAPS-17 EC-06)
    queue = MemoryQueue()
    await _sweep(engine, queue)
    assert queue.sent == [invoice_id]
    await process(engine, invoice_id)  # what the SAPS Worker does with the message
    assert await _status(engine, invoice_id) is InvoiceStatus.PENDING_REVIEW


# TS-03 -----------------------------------------------------------------------------------------------


async def test_an_invoice_whose_job_is_running_is_skipped(engine: AsyncEngine) -> None:
    invoice_id = await _invoice(engine)
    queue = MemoryQueue()
    async with session_factory(engine)() as session, session.begin():
        await session.execute(select(Invoice.id).where(Invoice.id == invoice_id).with_for_update())
        assert await _sweep(engine, queue) == []  # row-locked by the running job
    assert queue.sent == []
    assert await _sweep(engine, queue) == [invoice_id]  # the job ended and the invoice is still stuck
    assert queue.sent == [invoice_id]


# TS-04 -----------------------------------------------------------------------------------------------


async def test_only_one_sweeper_sweeps_at_a_time(engine: AsyncEngine) -> None:
    invoice_id = await _invoice(engine)
    queue = MemoryQueue()
    async with session_factory(engine)() as session, session.begin():
        await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SWEEPER_LOCK_KEY})
        assert await _sweep(engine, queue) is None  # another SAPS Worker process is sweeping
    assert queue.sent == []
    assert await _sweep(engine, queue) == [invoice_id]


# TS-05 -----------------------------------------------------------------------------------------------


async def test_a_failing_send_rolls_the_tick_back(engine: AsyncEngine) -> None:
    invoice_id = await _invoice(engine)
    before = await _updated_at(engine, invoice_id)
    with pytest.raises(ConnectionError):
        await _sweep(engine, MemoryQueue(fail=True))
    assert await _events(engine, invoice_id) == []
    assert await _updated_at(engine, invoice_id) == before
    queue = MemoryQueue()
    assert await _sweep(engine, queue) == [invoice_id]  # the next tick tries again
    assert queue.sent == [invoice_id]


# TS-06 -----------------------------------------------------------------------------------------------


async def test_the_oldest_invoices_go_first_when_the_batch_is_full(engine: AsyncEngine) -> None:
    newest = await _invoice(engine, age=timedelta(days=1))
    middle = await _invoice(engine, age=timedelta(days=2))
    oldest = await _invoice(engine, age=timedelta(days=3))
    queue = MemoryQueue()
    assert await _sweep(engine, queue, limit=2) == [oldest, middle]
    assert await _sweep(engine, queue, limit=2) == [newest]  # the rest at the next tick


# TS-09 -----------------------------------------------------------------------------------------------


async def test_a_lost_rematch_message_after_a_correction_is_recovered(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    line = {"lineNumber": 1, "description": "USB keyboard", "poNumber": "0100012", "poLineNumber": 1}
    fix = {"lines": [{**line, "quantity": "4", "unitPrice": "20.00", "lineAmount": "80.00"}]}
    assert (await api.update("alice", invoice_id, fix)).status_code == 202  # the message is never delivered
    assert await _status(api.engine, invoice_id) is InvoiceStatus.MATCHING
    async with session_factory(api.engine)() as session, session.begin():
        await session.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(updated_at=datetime.now(UTC) - timedelta(days=1))
        )

    queue = MemoryQueue()
    assert await _sweep(api.engine, queue) == [invoice_id]
    assert queue.rematch == [invoice_id]
    await api.rematch(invoice_id)  # what the SAPS Worker does with the message
    assert (await api.get(invoice_id))["status"] == "PENDING_REVIEW"


async def test_invoices_of_every_tenant_are_swept(engine: AsyncEngine) -> None:  # BR-05
    first, second = await _invoice(engine), await _invoice(engine)
    other_tenant = await new_tenant(engine)
    third = await uploaded(engine, DS01, other_tenant)
    async with session_factory(engine)() as session, session.begin():
        await session.execute(
            update(Invoice)
            .where(Invoice.id == third)
            .values(updated_at=datetime.now(UTC) - timedelta(days=1))
        )
    resent = await _sweep(engine, MemoryQueue())
    assert resent is not None and {first, second, third} <= set(resent)


# SAPS-38 BR-05 / TS-05 ---------------------------------------------------------------------------------


async def test_the_sweeper_gives_up_on_an_uploaded_invoice_after_the_limit(engine: AsyncEngine) -> None:
    invoice_id = await _invoice(engine)
    queue = MemoryQueue()
    for _ in range(3):  # three re-sends, each after another stuck period
        result = await _sweep_result(engine, queue)
        assert result is not None and [r.invoice_id for r in result.resent] == [invoice_id]
        await _age(engine, invoice_id)
    assert queue.sent == [invoice_id] * 3
    assert len(await _events(engine, invoice_id)) == 3

    result = await _sweep_result(engine, queue)  # the fourth time: give up
    assert result is not None and result.resent == []
    assert [(g.invoice_id, g.resends) for g in result.gave_up] == [(invoice_id, 3)]
    assert queue.sent == [invoice_id] * 3
    [limit] = await _events(engine, invoice_id, "RESEND_LIMIT")
    assert (limit.actor, limit.details) == ("system", {"resends": 3})
    assert await _status(engine, invoice_id) is InvoiceStatus.UPLOADED  # no EX1 from the sweeper

    await _age(engine, invoice_id)
    again = await _sweep_result(engine, queue)  # never selected again, logged once
    assert again is not None and again.resent == [] and again.gave_up == []
    assert len(await _events(engine, invoice_id, "RESEND_LIMIT")) == 1


async def test_a_matching_invoice_is_re_sent_however_often(engine: AsyncEngine) -> None:
    invoice_id = await _invoice(engine, InvoiceStatus.MATCHING)
    queue = MemoryQueue()
    for _ in range(5):
        assert await _sweep(engine, queue) == [invoice_id]
        await _age(engine, invoice_id)
    assert queue.rematch == [invoice_id] * 5
    assert await _events(engine, invoice_id, "RESEND_LIMIT") == []
