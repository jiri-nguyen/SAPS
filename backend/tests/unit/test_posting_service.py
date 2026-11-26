"""SAPS-49 `post_invoice` use case with in-memory ports (TS-04) and the mock adapter (BR-03)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from saps.adapters.erp.mock_posting import MockErpPostingAdapter
from saps.application.posting import PostingService
from saps.domain.invoices import InvoiceStatus
from saps.domain.processing_calendar import CalendarRule, RuleKind
from saps.ports.erp_posting import PostingRequest, PostingResult
from saps.ports.posting import InvoiceToPost
from saps.ports.processing_calendar import CalendarSnapshot

TENANT = uuid4()
FRIDAY = datetime(2027, 3, 5, 10, 0, tzinfo=UTC)
CLOSED_ON_FRIDAY = CalendarSnapshot((CalendarRule(kind=RuleKind.WEEKDAY, weekday=5),), "UTC")
OPEN = CalendarSnapshot((), "UTC")


def _request(invoice_id=None) -> PostingRequest:  # type: ignore[no-untyped-def]
    return PostingRequest(
        invoice_id or uuid4(), "vn", "V001", "INV-1", date(2027, 3, 1), "USD", None, None, None, []
    )


class Repo:
    def __init__(self, invoice: InvoiceToPost | None, calendar: CalendarSnapshot = OPEN) -> None:
        self.invoice, self.calendar = invoice, calendar
        self.held = 0
        self.posted: list[str] = []
        self.locks = 0

    async def lock_invoice(self, invoice_id):  # type: ignore[no-untyped-def]
        self.locks += 1
        return self.invoice

    async def calendar_of(self, tenant_id):  # type: ignore[no-untyped-def]
        return self.calendar

    async def hold(self, invoice, *, now):  # type: ignore[no-untyped-def]
        self.held += 1
        return True

    async def mark_posted(self, invoice, document_number, *, now):  # type: ignore[no-untyped-def]
        self.posted.append(document_number)
        assert self.invoice is not None
        self.invoice = replace(self.invoice, status=InvoiceStatus.POSTED)


class Port:
    def __init__(self, fail: bool = False) -> None:
        self.requests: list[PostingRequest] = []
        self.fail = fail

    async def post(self, request: PostingRequest) -> PostingResult:
        if self.fail:
            raise ConnectionError("ERP unavailable")
        self.requests.append(request)
        return PostingResult("DOC-1")


def _invoice(status: InvoiceStatus = InvoiceStatus.POSTING) -> InvoiceToPost:
    request = _request()
    return InvoiceToPost(request.invoice_id, TENANT, status, None, request)


def _service(repo: Repo, port: Port) -> PostingService:
    @asynccontextmanager
    async def uow() -> AsyncIterator[Repo]:
        yield repo

    return PostingService(uow, port, lambda: FRIDAY)  # type: ignore[arg-type]


async def test_an_invoice_in_posting_is_posted_with_its_invoice_id_as_key() -> None:  # BR-02
    invoice = _invoice()
    repo, port = Repo(invoice), Port()
    outcome = await _service(repo, port).post(invoice.id)
    assert outcome is not None and (outcome.held, outcome.document_number) == (False, "DOC-1")
    assert [r.invoice_id for r in port.requests] == [invoice.id] and repo.posted == ["DOC-1"]
    assert repo.locks == 2  # locked before and after the call to the ERP (ADR-0013)


@pytest.mark.parametrize("status", [s for s in InvoiceStatus if s is not InvoiceStatus.POSTING])
async def test_any_other_status_is_left_alone(status: InvoiceStatus) -> None:  # EC-01
    repo, port = Repo(_invoice(status)), Port()
    assert await _service(repo, port).post(uuid4()) is None
    assert port.requests == [] and repo.posted == []


async def test_an_unknown_invoice_is_skipped() -> None:
    assert await _service(Repo(None), Port()).post(uuid4()) is None


async def test_a_closed_day_holds_the_posting() -> None:  # DEC-070, EC-12
    repo, port = Repo(_invoice(), CLOSED_ON_FRIDAY), Port()
    outcome = await _service(repo, port).post(uuid4())
    assert outcome is not None and outcome.held and outcome.document_number is None
    assert repo.held == 1 and port.requests == [] and repo.posted == []


async def test_a_failing_port_raises_and_posts_nothing() -> None:  # EC-03: Dramatiq retries
    repo = Repo(_invoice())
    with pytest.raises(ConnectionError):
        await _service(repo, Port(fail=True)).post(uuid4())
    assert repo.posted == []


async def test_an_invoice_that_moved_on_during_the_call_is_not_posted_twice() -> None:  # EC-01
    invoice = _invoice()
    repo = Repo(invoice)

    class Racing(Port):
        async def post(self, request: PostingRequest) -> PostingResult:
            repo.invoice = replace(invoice, status=InvoiceStatus.POSTED)  # another job was faster
            return await super().post(request)

    assert await _service(repo, Racing()).post(uuid4()) is None and repo.posted == []


async def test_the_mock_adapter_gives_the_same_document_for_the_same_invoice() -> None:  # BR-03
    adapter, request = MockErpPostingAdapter(), _request()
    first, second = await adapter.post(request), await adapter.post(request)
    assert first == second and first.document_number.startswith("MOCK-") and len(first.document_number) == 15
    assert (await adapter.post(_request())).document_number != first.document_number
