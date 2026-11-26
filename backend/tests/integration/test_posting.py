"""Integration: SAPS-49 posting on a real PostgreSQL (TS-04, TS-07, TS-09; ADR-0013)."""

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.erp.mock_posting import MockErpPostingAdapter
from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.models import Invoice, InvoiceEvent, ProcessingCalendarRule
from saps.adapters.persistence.posting_repository import SqlPostingUnitOfWork
from saps.adapters.persistence.processing_calendar_repository import SqlHeldInvoiceRepository
from saps.application.posting import PostingService
from saps.application.processing_calendar import HoldReleaseService
from saps.config import get_settings
from saps.domain.invoices import InvoiceStatus
from saps.domain.processing_calendar import RuleKind
from saps.ports.erp_posting import PostingRequest, PostingResult
from tests.fakes import MemoryQueue
from tests.integration.db_urls import use_database
from tests.integration.pipeline import ERP, FIXTURES, new_tenant, process, uploaded

pytestmark = pytest.mark.integration

DS01 = FIXTURES / "ds-01/invoices/ds-01-trade-po.pdf"
FRIDAY = datetime(2027, 3, 5, 10, 0, tzinfo=UTC)
SATURDAY = datetime(2027, 3, 6, 10, 0, tzinfo=UTC)


class RecordingPort:
    def __init__(self) -> None:
        self.requests: list[PostingRequest] = []
        self._mock = MockErpPostingAdapter()

    async def post(self, request: PostingRequest) -> PostingResult:
        self.requests.append(request)
        await asyncio.sleep(0.05)  # lets a parallel job overlap with this call
        return await self._mock.post(request)


async def _posting_invoice(engine: AsyncEngine) -> tuple[uuid.UUID, uuid.UUID]:
    """DS-01 processed in a tenant of its own: matching ends in Posting (SAPS-49 BR-01)."""
    tenant = await new_tenant(engine)
    invoice_id = await uploaded(engine, DS01, tenant)
    outcome = await process(engine, invoice_id)
    assert outcome is not None and outcome.matching is not None
    assert outcome.matching.status is InvoiceStatus.POSTING
    return invoice_id, tenant[0]


def _service(engine: AsyncEngine, port: RecordingPort, now: datetime = FRIDAY) -> PostingService:
    return PostingService(SqlPostingUnitOfWork(session_factory(engine)), port, lambda: now)


async def _invoice(engine: AsyncEngine, invoice_id: uuid.UUID) -> Invoice:
    async with session_factory(engine)() as session:
        return await session.get_one(Invoice, invoice_id)


async def _events(engine: AsyncEngine, invoice_id: uuid.UUID, action: str) -> list[InvoiceEvent]:
    async with session_factory(engine)() as session:
        rows = await session.execute(
            select(InvoiceEvent).where(InvoiceEvent.invoice_id == invoice_id, InvoiceEvent.action == action)
        )
        return list(rows.scalars())


async def test_an_invoice_in_posting_is_posted_once(engine: AsyncEngine) -> None:  # BR-02, EC-01
    invoice_id, _ = await _posting_invoice(engine)
    port = RecordingPort()
    outcome = await _service(engine, port).post(invoice_id)
    assert outcome is not None and not outcome.held and outcome.document_number is not None
    invoice = await _invoice(engine, invoice_id)
    assert invoice.status is InvoiceStatus.POSTED and invoice.posted_at == FRIDAY
    assert invoice.erp_document_number == outcome.document_number
    assert invoice.erp_document_number.startswith("MOCK-") and invoice.posting_held_at is None
    [request] = port.requests
    assert (
        request.invoice_id == invoice_id
        and request.company_code
        and request.invoice_number == "AOS-2026-1001"
    )
    assert [(line.po_number, line.po_line_number, line.do_number) for line in request.lines] == [
        ("0100001", 1, "DO-5000001"),
        ("0100001", 2, "DO-5000001"),
    ]
    [event] = await _events(engine, invoice_id, "POST")
    assert (event.status_from, event.status_to, event.actor) == (
        InvoiceStatus.POSTING,
        InvoiceStatus.POSTED,
        "system",
    )
    assert event.details == {"documentNumber": invoice.erp_document_number}
    assert await _service(engine, port).post(invoice_id) is None  # a second message changes nothing
    assert len(port.requests) == 1


async def test_two_jobs_at_once_post_one_invoice_once(engine: AsyncEngine) -> None:  # EC-01
    invoice_id, _ = await _posting_invoice(engine)
    port = RecordingPort()
    outcomes = await asyncio.gather(
        _service(engine, port).post(invoice_id), _service(engine, port).post(invoice_id)
    )
    assert len([o for o in outcomes if o is not None]) == 1
    assert len(await _events(engine, invoice_id, "POST")) == 1
    documents = {r.invoice_id for r in port.requests}
    assert documents == {invoice_id}  # the port was asked for the same key, however often (ADR-0013)


async def test_a_closed_day_holds_the_posting_and_the_timer_releases_it(
    engine: AsyncEngine,
) -> None:  # DEC-070
    invoice_id, tenant_id = await _posting_invoice(engine)
    async with session_factory(engine)() as session, session.begin():
        session.add(ProcessingCalendarRule(tenant_id=tenant_id, position=0, kind=RuleKind.WEEKDAY, weekday=5))
    port = RecordingPort()
    outcome = await _service(engine, port).post(invoice_id)
    assert outcome is not None and outcome.held and port.requests == []
    invoice = await _invoice(engine, invoice_id)
    assert invoice.status is InvoiceStatus.POSTING and invoice.posting_held_at == FRIDAY
    assert (await _service(engine, port).post(invoice_id)).held  # type: ignore[union-attr]
    assert len(await _events(engine, invoice_id, "POSTING_HOLD")) == 1  # held once, not on every message

    held = SqlHeldInvoiceRepository(engine)
    friday_queue = MemoryQueue()
    await HoldReleaseService(held, friday_queue, lambda: FRIDAY, 10).release_due()
    assert invoice_id not in friday_queue.posting  # still a closed day: the timer leaves it
    assert (await _invoice(engine, invoice_id)).posting_held_at == FRIDAY

    queue = MemoryQueue()
    await HoldReleaseService(held, queue, lambda: SATURDAY, 10).release_due()  # the next day is open
    assert invoice_id in queue.posting and queue.tenant_of[invoice_id] == tenant_id
    released = await _invoice(engine, invoice_id)
    assert released.posting_held_at is None and released.status is InvoiceStatus.POSTING
    event = (await _events(engine, invoice_id, "RELEASE_HOLD"))[-1]
    assert event.details == {"by": "calendar", "step": "posting"}
    outcome = await _service(engine, port, SATURDAY).post(invoice_id)  # open again: posted
    assert outcome is not None and not outcome.held
    assert (await _invoice(engine, invoice_id)).status is InvoiceStatus.POSTED


async def test_posting_counts_as_invoiced_and_as_a_duplicate(engine: AsyncEngine) -> None:  # BR-09, TS-09
    invoice_id, tenant_id = await _posting_invoice(engine)
    tenant = (tenant_id, (await _invoice(engine, invoice_id)).uploaded_by)
    second = await uploaded(engine, DS01, tenant)  # the same invoice again: DS-01 took the whole PO
    outcome = await process(engine, second)
    assert outcome is not None and outcome.matching is not None
    assert {c.value for c in outcome.matching.open_codes} == {"EX4", "EX9"}
    await _service(engine, RecordingPort()).post(invoice_id)  # Posted keeps counting
    third = await uploaded(engine, DS01, tenant)
    again = await process(engine, third)
    assert again is not None and again.matching is not None
    assert {c.value for c in again.matching.open_codes} == {"EX4", "EX9"}


async def test_the_worker_jobs_send_the_posting_and_post_as_the_company(
    engine: AsyncEngine, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:  # BR-01, EC-04: run_processing → post_invoice → run_posting, on the saps_app role
    from saps.adapters.persistence.db import dispose_engines
    from saps.worker import jobs
    from saps.worker.jobs import run_posting, run_processing

    tenant = await new_tenant(engine)
    invoice_id = await uploaded(engine, DS01, tenant)
    use_database(monkeypatch, database_url)
    monkeypatch.setattr(
        jobs, "erp_adapter", lambda name, fixtures_dir: ERP
    )  # the test company has no ERP data
    get_settings.cache_clear()
    queue = MemoryQueue()
    try:
        outcome = await run_processing(invoice_id, tenant[0], queue)
        assert outcome is not None and outcome.matching is not None
        assert outcome.matching.status is InvoiceStatus.POSTING and queue.posting == [invoice_id]
        posted = await run_posting(invoice_id, tenant[0])
        assert posted is not None and posted.document_number is not None
        assert await run_posting(invoice_id, tenant[0]) is None  # a duplicate message
        await run_posting(invoice_id, None)  # sent without a company (EC-05): read with the system role
        failing = MemoryQueue(fail=True)  # a failed send does not fail the job (the sweeper recovers it)
        second = await uploaded(engine, FIXTURES / "ds-12/invoices/ds-12-price-outside-tolerance.pdf", tenant)
        assert await run_processing(second, tenant[0], failing) is not None
    finally:
        await dispose_engines()
        get_settings.cache_clear()
    assert (await _invoice(engine, invoice_id)).status is InvoiceStatus.POSTED
