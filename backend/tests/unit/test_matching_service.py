"""SAPS-19 matching use case with in-memory ports: status check, re-match reconciliation, notifications."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal as D
from uuid import UUID, uuid4

import pytest

from saps.application.matching import MatchingService
from saps.domain.duplicates import DuplicateCandidate
from saps.domain.invoices import ExceptionCode as EX
from saps.domain.invoices import (
    InvalidTransitionError,
    InvoiceStatus,
    InvoiceType,
    MatchStatus,
    NotificationType,
)
from saps.domain.matching import (
    GoodsReceiptLine,
    InvoicedQuantities,
    InvoiceToMatch,
    LineToMatch,
    MatchingRules,
    PoLineKey,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchasingInfoRecord,
)
from saps.domain.users import Role
from saps.ports.matching import InvoiceForMatching, MatchUpdate, OpenException

NOW = datetime(2026, 12, 15, 10, 0, tzinfo=UTC)
MEMBERS = [uuid4(), uuid4()]
OTHER = DuplicateCandidate(uuid4(), "INV 1", InvoiceStatus.PENDING_REVIEW)
MANAGERS = [uuid4()]
LINE = LineToMatch(uuid4(), 1, "0100001", 1, D("2"), D("10.00"))


class FakeErp:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.companies: list[str] = []
        self.pir_keys: list[tuple[str, str]] = []

    async def get_purchase_orders(
        self, company_code: str, po_numbers: Sequence[str]
    ) -> dict[str, PurchaseOrder]:
        self.calls.append("orders")
        self.companies.append(company_code)
        lines = {1: PurchaseOrderLine(1, "Paper", D("10"), D("10.00"), "MAT1")}
        return {n: PurchaseOrder(n, "V001", "USD", lines) for n in po_numbers if n != "0199999"}

    async def get_goods_receipt_lines(
        self, company_code: str, po_numbers: Sequence[str]
    ) -> list[GoodsReceiptLine]:
        self.calls.append("receipts")
        return [GoodsReceiptLine("GR1", n, 1, D("10"), "DO1") for n in po_numbers]

    async def get_purchasing_info_records(
        self, company_code: str, keys: Sequence[tuple[str, str]]
    ) -> list[PurchasingInfoRecord]:
        self.calls.append("pirs")
        self.pir_keys.extend(keys)
        return [PurchasingInfoRecord(v, m, D("10.00"), date(2026, 1, 1)) for v, m in keys]


class FakeRepo:
    def __init__(self, invoice: InvoiceForMatching | None) -> None:
        self.invoice = invoice
        self.locked: list[PoLineKey] = []
        self.saved: MatchUpdate | None = None
        self.notifications: list[tuple[list[UUID], NotificationType, str]] = []
        self.duplicates: list[DuplicateCandidate] = []
        self.duplicate_keys: list[tuple[str, str]] = []

    async def lock_duplicate_key(self, tenant_id: UUID, vendor_code: str, invoice_number: str) -> None:
        self.duplicate_keys.append((vendor_code, invoice_number))

    async def find_duplicates(
        self, tenant_id: UUID, vendor_code: str, invoice_number: str, exclude_invoice_id: UUID
    ) -> list[DuplicateCandidate]:
        return [d for d in self.duplicates if d.id != exclude_invoice_id]

    async def lock_invoice(self, invoice_id: UUID) -> InvoiceForMatching | None:
        return self.invoice

    async def get_rules(self, tenant_id: UUID) -> MatchingRules:
        return MatchingRules(D("0.5"), D("300"))

    async def lock_po_lines(self, tenant_id: UUID, keys: Sequence[PoLineKey]) -> None:
        self.locked.extend(keys)

    async def already_invoiced(
        self, tenant_id: UUID, po_numbers: Sequence[str], exclude_invoice_id: UUID
    ) -> InvoicedQuantities:
        self.invoiced_for = list(po_numbers)
        return InvoicedQuantities()

    async def save_match(
        self, invoice: InvoiceForMatching, update: MatchUpdate, *, actor: str, action: str, now: datetime
    ) -> None:
        assert (actor, action, now) == ("system", "MATCH", NOW)
        self.saved = update

    async def active_user_ids(self, tenant_id: UUID, role: Role) -> list[UUID]:
        return MEMBERS if role is Role.ACCOUNTING_MEMBER else MANAGERS

    async def add_notifications(
        self,
        tenant_id: UUID,
        invoice_id: UUID,
        recipients: Sequence[UUID],
        kind: NotificationType,
        message: str,
    ) -> None:
        self.notifications.append((list(recipients), kind, message))


def _invoice(*lines: LineToMatch, total: str = "20", **changes: object) -> InvoiceForMatching:
    base = InvoiceForMatching(
        id=uuid4(),
        tenant_id=uuid4(),
        status=InvoiceStatus.MATCHING,
        invoice_number="INV-1",
        vendor_name="Alpha Supplies",
        file_name="inv.pdf",
        assigned_to=None,
        invoice=InvoiceToMatch("V001", D(total), lines or (LINE,), date(2026, 12, 1)),
        open_exceptions=(),
        company_code="sg",
    )
    return replace(base, **changes)  # type: ignore[arg-type]


async def _match(
    invoice: InvoiceForMatching | None,
    erp: FakeErp | None = None,
    duplicates: Sequence[DuplicateCandidate] = (),
) -> tuple[FakeRepo, object]:
    repo = FakeRepo(invoice)
    repo.duplicates = list(duplicates)
    outcome = await MatchingService(repo, erp or FakeErp(), lambda: NOW).match(uuid4())
    return repo, outcome


@pytest.mark.parametrize("status", [InvoiceStatus.UPLOADED, InvoiceStatus.EXCEPTION, InvoiceStatus.COMPLETED])
async def test_stale_or_duplicate_message_changes_nothing(status: InvoiceStatus) -> None:  # EC-03
    repo, outcome = await _match(_invoice(status=status))
    assert outcome is None and repo.saved is None and repo.notifications == []


async def test_unknown_invoice_is_skipped() -> None:
    _, outcome = await _match(None)
    assert outcome is None


async def test_matched_invoice_below_threshold_goes_to_review_and_notifies_members() -> None:
    erp = FakeErp()
    repo, outcome = await _match(_invoice(), erp)
    assert outcome is not None and outcome.status is InvoiceStatus.PENDING_REVIEW
    assert outcome.invoice_type is InvoiceType.TRADE_PO
    assert erp.calls == ["orders", "receipts", "pirs"] and repo.locked == [("0100001", 1)]
    assert erp.pir_keys == [("V001", "MAT1")] and repo.invoiced_for == [
        "0100001"
    ]  # one call each (NFR-SCAL-001)
    assert erp.companies == ["sg"]  # the ERP data of the invoice's company (SAPS-42 BR-03)
    assert repo.saved is not None
    assert repo.saved.lines[LINE.id].match_status is MatchStatus.MATCHED
    assert repo.saved.requires_approval is False
    assert repo.saved.event_details == {
        "invoiceType": "TRADE_PO",
        "opened": [],
        "resolved": [],
        "priceTolerance": "0.5",
        "approvalThreshold": "300",
    }
    assert repo.notifications == [
        (
            MEMBERS,
            NotificationType.REVIEW_REQUESTED,
            "Invoice INV-1 from Alpha Supplies is ready for final review.",
        )
    ]


async def test_matched_invoice_above_threshold_notifies_managers() -> None:
    repo, outcome = await _match(_invoice(total="300.01"))
    assert outcome is not None and outcome.status is InvoiceStatus.PENDING_APPROVAL
    assert repo.notifications == [
        (MANAGERS, NotificationType.APPROVAL_REQUESTED, "Invoice INV-1 from Alpha Supplies needs approval.")
    ]


async def test_non_po_invoice_does_not_call_the_erp() -> None:
    erp = FakeErp()
    repo, outcome = await _match(_invoice(replace(LINE, po_number=None), invoice_number=None), erp)
    assert outcome is not None and outcome.open_codes == (EX.EX2,)
    assert erp.calls == [] and repo.locked == []
    assert repo.notifications == [
        (MEMBERS, NotificationType.EXCEPTION_RAISED, "Invoice file inv.pdf has exceptions: EX2.")
    ]


async def test_non_trade_invoice_reads_no_goods_receipts() -> None:
    erp = FakeErp()
    await _match(_invoice(replace(LINE, po_number="1100001")), erp)
    assert erp.calls == ["orders"]  # 2-way: no goods receipts, no purchasing info records


async def test_rematch_resolves_fixed_keeps_ex9_and_opens_new() -> None:  # BR-14, SAPS-23 BR-06
    fixed = OpenException(uuid4(), EX.EX6, LINE.id)  # price now within tolerance
    duplicate = OpenException(uuid4(), EX.EX9, None)  # the other invoice still exists
    still = OpenException(uuid4(), EX.EX7, LINE.id)
    line = replace(LINE, quantity=D("11"))  # EX7 again; and a new EX4 on line 2
    new_line = LineToMatch(uuid4(), 2, "0199999", 1, D("1"), D("1"))
    repo, outcome = await _match(
        _invoice(
            line,
            new_line,
            invoice_number="INV-9",
            vendor_name=None,
            open_exceptions=(fixed, duplicate, still),
        ),
        duplicates=[OTHER],
    )
    assert outcome is not None and outcome.status is InvoiceStatus.EXCEPTION
    assert outcome.open_codes == (EX.EX4, EX.EX7, EX.EX9)
    assert outcome.opened == (EX.EX4,) and outcome.resolved == (EX.EX6,)
    assert repo.saved is not None
    assert repo.saved.resolved == [fixed.id]
    assert [(e.code, e.line_id) for e in repo.saved.opened] == [(EX.EX4, new_line.id)]
    assert set(repo.saved.messages) == {still.id, duplicate.id}
    assert repo.notifications[0][2] == "Invoice INV-9 has exceptions: EX4, EX7, EX9."


async def test_claimed_invoice_in_exception_notifies_only_the_claimant() -> None:  # SAPS-20 BR-10
    claimant = uuid4()
    repo, _ = await _match(_invoice(replace(LINE, unit_price=D("11")), assigned_to=claimant))
    assert repo.notifications[0][:2] == ([claimant], NotificationType.EXCEPTION_RAISED)


async def test_no_notification_without_recipients() -> None:
    repo = FakeRepo(_invoice(total="400"))
    MANAGERS_BACKUP = list(MANAGERS)
    MANAGERS.clear()
    try:
        await MatchingService(repo, FakeErp(), lambda: NOW).match(uuid4())
    finally:
        MANAGERS.extend(MANAGERS_BACKUP)
    assert repo.notifications == []


async def test_lifecycle_guard_is_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    import saps.application.matching as module

    def refuse(current: InvoiceStatus, target: InvoiceStatus) -> None:
        raise InvalidTransitionError(f"{current} -> {target}")

    monkeypatch.setattr(module, "ensure_transition", refuse)
    with pytest.raises(InvalidTransitionError):
        await _match(_invoice())


# SAPS-23 duplicate check inside the matching run -------------------------------------------------------


async def test_duplicate_raises_ex9_even_when_matching_is_clean() -> None:  # BR-04, BR-05
    repo, outcome = await _match(_invoice(invoice_number=" inv-1 "), duplicates=[OTHER])
    assert outcome is not None and outcome.status is InvoiceStatus.EXCEPTION
    assert outcome.open_codes == (EX.EX9,) and outcome.duplicate_of == (OTHER.id,)
    assert repo.duplicate_keys == [("V001", "inv1")]  # locked by the normalized key (BR-02, EC-01)
    assert repo.saved is not None
    [ex9] = repo.saved.opened
    assert (ex9.code, ex9.line_id, ex9.message) == (
        EX.EX9,
        None,
        "Duplicate of invoice INV 1 (Pending review).",
    )


async def test_duplicate_gets_its_matching_exceptions_too() -> None:  # TS-05
    _, outcome = await _match(_invoice(replace(LINE, unit_price=D("11"))), duplicates=[OTHER])
    assert outcome is not None and outcome.open_codes == (EX.EX6, EX.EX9)


async def test_ex9_is_resolved_when_the_duplicate_is_gone() -> None:  # EC-04
    open_ex9 = OpenException(uuid4(), EX.EX9, None)
    repo, outcome = await _match(_invoice(open_exceptions=(open_ex9,)))
    assert outcome is not None and outcome.status is InvoiceStatus.PENDING_REVIEW
    assert outcome.resolved == (EX.EX9,) and repo.saved is not None and repo.saved.resolved == [open_ex9.id]


@pytest.mark.parametrize("changes", [{"invoice_number": None}, {"invoice_number": " - "}])
async def test_no_check_without_invoice_number(changes: dict[str, object]) -> None:  # EC-06, EC-08
    open_ex9 = OpenException(uuid4(), EX.EX9, None)
    repo, outcome = await _match(_invoice(open_exceptions=(open_ex9,), **changes), duplicates=[OTHER])
    assert repo.duplicate_keys == []
    assert outcome is not None and outcome.resolved == (EX.EX9,)


async def test_no_check_without_vendor_code() -> None:  # EC-06
    invoice = _invoice()
    invoice = replace(invoice, invoice=replace(invoice.invoice, vendor_code=None))
    repo, _ = await _match(invoice, duplicates=[OTHER])
    assert repo.duplicate_keys == []
