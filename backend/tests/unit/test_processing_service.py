"""SAPS-18 process_invoice use case with in-memory ports."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal as D
from uuid import UUID, uuid4

import pytest

from saps.application.processing import NOT_IN_SAMPLE_SET, ProcessInvoiceService
from saps.domain.extraction import ExtractedInvoice, ExtractedLine
from saps.domain.invoices import InvoiceStatus, NotificationType
from saps.domain.users import Role
from saps.ports.extraction import StoredFile
from saps.ports.processing import InvoiceToProcess
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
    def __init__(self, invoice: InvoiceToProcess | None) -> None:
        self.invoice = invoice
        self.saved: ExtractedInvoice | None = None
        self.unreadable: str | None = None
        self.notified: list[tuple[list[UUID], NotificationType, str]] = []

    async def lock_invoice(self, invoice_id: UUID) -> InvoiceToProcess | None:
        return self.invoice

    async def save_extraction(
        self, invoice: InvoiceToProcess, extracted: ExtractedInvoice, *, actor: str, now: datetime
    ) -> None:
        assert (actor, now) == ("system", NOW)
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
