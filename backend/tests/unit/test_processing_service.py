"""SAPS-18 process_invoice use case with in-memory ports."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from decimal import Decimal as D
from uuid import UUID, uuid4

import pytest

from saps.application.processing import NOT_IN_SAMPLE_SET, ProcessInvoiceService
from saps.domain.extraction import ExtractedInvoice, ExtractedLine
from saps.domain.invoices import InvoiceStatus, NotificationType
from saps.domain.processing_calendar import CalendarRule, RuleKind
from saps.domain.users import Role
from saps.ports.extraction import StoredFile
from saps.ports.processing import InvoiceToProcess
from saps.ports.processing_calendar import CalendarSnapshot
from tests.fakes import NOW

MEMBERS = [uuid4(), uuid4()]
EXTRACTED = ExtractedInvoice(
    "V001",
    "Alpha",
    "INV-1",
    None,
    "USD",
    D("20"),
    D("2"),
    D("22"),
    [ExtractedLine(1, "x", "0100001", 1, D("2"), D("10"), D("20"))],
)


def _invoice(status: InvoiceStatus = InvoiceStatus.UPLOADED) -> InvoiceToProcess:
    return InvoiceToProcess(
        uuid4(), uuid4(), status, StoredFile("a" * 64, "k", "application/pdf"), "scan.pdf", None
    )


class FakeRepo:
    def __init__(self, invoice: InvoiceToProcess | None, calendar: CalendarSnapshot | None = None) -> None:
        self.invoice = invoice
        self.calendar = calendar or CalendarSnapshot((), "UTC")
        self.held = False
        self.saved: ExtractedInvoice | None = None
        self.unreadable: str | None = None
        self.notified: list[tuple[list[UUID], NotificationType, str]] = []

    async def lock_invoice(self, invoice_id: UUID) -> InvoiceToProcess | None:
        return self.invoice

    async def calendar_of(self, tenant_id: UUID) -> CalendarSnapshot:
        return self.calendar

    async def hold(self, invoice: InvoiceToProcess, *, actor: str, now: datetime) -> None:
        assert actor == "system"
        self.held = True

    async def save_extraction(
        self, invoice: InvoiceToProcess, extracted: ExtractedInvoice, *, actor: str, now: datetime
    ) -> None:
        assert actor == "system"
        self.saved = extracted

    async def raise_unreadable(
        self, invoice: InvoiceToProcess, reason: str, *, actor: str, now: datetime
    ) -> None:
        self.unreadable = reason

    async def active_user_ids(self, tenant_id: UUID, role: Role) -> list[UUID]:
        assert role is Role.ACCOUNTING_MEMBER
        return MEMBERS

    async def add_notifications(
        self,
        tenant_id: UUID,
        invoice_id: UUID,
        recipients: Sequence[UUID],
        kind: NotificationType,
        message: str,
    ) -> None:
        self.notified.append((list(recipients), kind, message))


class FakeExtraction:
    def __init__(self, result: ExtractedInvoice | None) -> None:
        self.result = result
        self.calls = 0

    async def extract(self, file: StoredFile) -> ExtractedInvoice | None:
        self.calls += 1
        return self.result


class FakeMatching:
    def __init__(self) -> None:
        self.matched: list[UUID] = []

    async def match(self, invoice_id: UUID) -> str:
        self.matched.append(invoice_id)
        return "matched"


def _service(repo: FakeRepo, extraction: FakeExtraction, matching: FakeMatching) -> ProcessInvoiceService:
    return ProcessInvoiceService(repo, extraction, matching, lambda: NOW)  # type: ignore[arg-type]


async def test_known_file_is_saved_and_matched() -> None:  # BR-01, BR-05
    repo, matching = FakeRepo(_invoice()), FakeMatching()
    outcome = await _service(repo, FakeExtraction(EXTRACTED), matching).process(uuid4())
    assert outcome is not None and outcome.found and outcome.line_count == 1
    assert repo.saved == EXTRACTED and repo.unreadable is None
    assert matching.matched == [repo.invoice.id]  # type: ignore[union-attr]
    assert outcome.matching == "matched"
    assert repo.notified == []  # matching notifies about its own result


@pytest.mark.parametrize(
    ("result", "reason", "found"),
    [
        (None, NOT_IN_SAMPLE_SET, False),
        (
            ExtractedInvoice(None, None, None, None, "EUR", None, None, None, EXTRACTED.lines),
            "The currency EUR is not supported (USD only).",
            True,
        ),
    ],
)
async def test_unknown_or_unusable_result_raises_ex1_and_notifies_members(
    result: ExtractedInvoice | None, reason: str, found: bool
) -> None:  # BR-03, BR-04
    repo, matching = FakeRepo(_invoice()), FakeMatching()
    outcome = await _service(repo, FakeExtraction(result), matching).process(uuid4())
    assert outcome is not None and outcome.unreadable_reason == reason and outcome.found is found
    assert repo.unreadable == reason and repo.saved is None and matching.matched == []
    assert repo.notified == [
        (MEMBERS, NotificationType.EXCEPTION_RAISED, "Invoice file scan.pdf has exceptions: EX1.")
    ]


@pytest.mark.parametrize(
    "invoice", [None, _invoice(InvoiceStatus.MATCHING), _invoice(InvoiceStatus.EXCEPTION)]
)
async def test_missing_or_already_processed_invoice_is_skipped(invoice: InvoiceToProcess | None) -> None:
    extraction = FakeExtraction(EXTRACTED)
    assert await _service(FakeRepo(invoice), extraction, FakeMatching()).process(uuid4()) is None
    assert extraction.calls == 0


# SAPS-52: the processing calendar ----------------------------------------

TUESDAY = CalendarRule(RuleKind.WEEKDAY, weekday=2)  # NOW is Tuesday 2026-12-15 09:00 UTC
SINGAPORE = "Asia/Singapore"  # 17:00 there


async def test_a_closed_day_holds_the_invoice_without_extraction() -> None:  # BR-03
    repo = FakeRepo(_invoice(), CalendarSnapshot((TUESDAY,), "UTC"))
    extraction, matching = FakeExtraction(EXTRACTED), FakeMatching()
    outcome = await _service(repo, extraction, matching).process(uuid4())
    assert outcome is not None and outcome.held and not outcome.found
    assert repo.held and repo.saved is None and extraction.calls == 0 and matching.matched == []


async def test_an_open_day_processes_as_before() -> None:
    repo = FakeRepo(_invoice(), CalendarSnapshot((CalendarRule(RuleKind.WEEKDAY, weekday=3),), "UTC"))
    outcome = await _service(repo, FakeExtraction(EXTRACTED), FakeMatching()).process(uuid4())
    assert outcome is not None and not outcome.held and repo.saved == EXTRACTED and not repo.held


async def test_the_day_is_a_day_of_the_company_time_zone() -> None:  # EC-04
    friday = CalendarRule(RuleKind.WEEKDAY, weekday=5)  # NOW is Tuesday in UTC and in Singapore
    assert (await _held(CalendarSnapshot((friday,), SINGAPORE))) is False
    late = datetime(2026, 12, 15, 17, 30, tzinfo=NOW.tzinfo)  # 01:30 on Wednesday in Singapore
    wednesday = CalendarRule(RuleKind.WEEKDAY, weekday=3)
    assert (await _held(CalendarSnapshot((wednesday,), SINGAPORE), late)) is True
    assert (await _held(CalendarSnapshot((wednesday,), "UTC"), late)) is False


async def test_an_invoice_released_by_a_manager_is_not_held_again() -> None:  # BR-06, EC-06
    invoice = replace(_invoice(), released_from_hold_at=NOW)
    repo = FakeRepo(invoice, CalendarSnapshot((TUESDAY,), "UTC"))
    outcome = await _service(repo, FakeExtraction(EXTRACTED), FakeMatching()).process(uuid4())
    assert outcome is not None and not outcome.held and repo.saved == EXTRACTED


async def _held(calendar: CalendarSnapshot, now: datetime = NOW) -> bool:
    repo = FakeRepo(_invoice(), calendar)
    service = ProcessInvoiceService(repo, FakeExtraction(EXTRACTED), FakeMatching(), lambda: now)  # type: ignore[arg-type]
    await service.process(uuid4())
    return repo.held
