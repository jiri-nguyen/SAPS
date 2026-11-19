"""SAPS-19 matching rules (TS-01 … TS-05, TS-07, TS-12)."""

from decimal import Decimal as D
from uuid import uuid4

import pytest

from saps.domain.invoices import ExceptionCode as EX
from saps.domain.invoices import InvoiceStatus, InvoiceType, MatchStatus
from saps.domain.matching import (
    GoodsReceiptLine,
    InvoiceToMatch,
    LineToMatch,
    MatchingRules,
    MatchResult,
    PurchaseOrder,
    PurchaseOrderLine,
    decide,
    derive_invoice_type,
    evaluate,
)

RULES = MatchingRules(price_tolerance=D("0.50"), approval_threshold=D("300"))
TRADE = PurchaseOrder("0100001", "V001", "USD", {1: PurchaseOrderLine(1, "Paper", D("10"), D("10.00"))})
NON_TRADE = PurchaseOrder("1100001", "V001", "USD", {1: PurchaseOrderLine(1, "Service", D("10"), D("10.00"))})
ORDERS = {o.po_number: o for o in (TRADE, NON_TRADE)}
DEFAULT_RECEIPTS = (GoodsReceiptLine("GR1", "0100001", 1, D("10")),)


def line(
    n: int = 1,
    po: str | None = "0100001",
    po_line: int | None = 1,
    qty: str | None = "2",
    price: str | None = "10.00",
):
    return LineToMatch(uuid4(), n, po, po_line, D(qty) if qty else None, D(price) if price else None)


def gr(qty: str, po: str = "0100001", po_line: int = 1, number: str = "GR1") -> GoodsReceiptLine:
    return GoodsReceiptLine(number, po, po_line, D(qty))


def run(
    *lines: LineToMatch, vendor: str = "V001", receipts=DEFAULT_RECEIPTS, invoiced=None, rules=RULES
) -> MatchResult:
    invoice = InvoiceToMatch(vendor, D("100"), lines)
    return evaluate(invoice, derive_invoice_type(invoice), rules, ORDERS, list(receipts), invoiced or {})


def codes(result: MatchResult) -> list[EX]:
    return [f.code for f in result.findings]


# TS-01 type derivation -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("po_numbers", "expected_type", "expected_codes"),
    [
        (["0100001", "0100002"], InvoiceType.TRADE_PO, []),
        (["1100001"], InvoiceType.NON_TRADE_PO, []),
        ([None, None], InvoiceType.NON_PO, [EX.EX2]),
        (["0100001", "1100001"], None, [EX.EX5]),
        (["0100001", "2100001"], InvoiceType.TRADE_PO, [EX.EX3]),  # prefix 2
        (["0100001", "010001"], InvoiceType.TRADE_PO, [EX.EX3]),  # 6 digits
        (["0100001", "01000O1"], InvoiceType.TRADE_PO, [EX.EX3]),  # not digits
        (["0100001", None], InvoiceType.TRADE_PO, [EX.EX3]),  # EC-04: line without PO number
        (["0100001", "  "], InvoiceType.TRADE_PO, [EX.EX3]),
        (["2100001"], None, [EX.EX3]),
    ],
)
def test_invoice_type_from_po_numbers(
    po_numbers: list[str | None], expected_type: InvoiceType | None, expected_codes: list[EX]
) -> None:
    invoice = InvoiceToMatch("V001", D("1"), [line(i + 1, po) for i, po in enumerate(po_numbers)])
    derivation = derive_invoice_type(invoice)
    assert derivation.invoice_type is expected_type
    assert [f.code for f in derivation.findings] == expected_codes


def test_ex5_is_one_header_exception_and_no_line_is_checked() -> None:
    result = run(line(1, "0100001"), line(2, "1100001"))
    assert codes(result) == [EX.EX5] and result.findings[0].line_id is None
    assert {r.match_status for r in result.lines.values()} == {MatchStatus.NOT_MATCHED}


def test_ex3_lines_are_mismatched_and_other_lines_are_still_checked() -> None:
    bad, good = line(1, "2100001"), line(2, "0100001")
    result = run(bad, good)
    assert codes(result) == [EX.EX3]
    assert result.lines[bad.id].match_status is MatchStatus.MISMATCH
    assert result.lines[good.id].match_status is MatchStatus.MATCHED


def test_invoice_without_lines_raises_ex1() -> None:  # EC-06
    result = run()
    assert codes(result) == [EX.EX1] and result.invoice_type is None


# TS-02 non-PO ---------------------------------------------------------------------------------------------


def test_non_po_invoice_raises_only_ex2_and_lines_are_not_applicable() -> None:
    result = run(line(1, None), line(2, None))
    assert codes(result) == [EX.EX2]
    assert {r.match_status for r in result.lines.values()} == {MatchStatus.NOT_APPLICABLE}


# TS-03 PO or PO line not found ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("po", "po_line", "text"),
    [("0199999", 1, "PO 0199999 was"), ("0100001", 9, "line 9 was"), ("0100001", None, "line None")],
)
def test_unknown_po_or_po_line_raises_ex4(po: str, po_line: int | None, text: str) -> None:
    result = run(line(1, po, po_line))
    assert codes(result) == [EX.EX4] and text in result.findings[0].message


# TS-04 unit price tolerance (inclusive) -------------------------------------------------------------


@pytest.mark.parametrize(
    ("price", "tolerance", "expected"),
    [
        ("10.40", "0.50", []),
        ("10.50", "0.50", []),
        ("9.50", "0.50", []),
        ("10.60", "0.50", [EX.EX6]),
        ("10.80", "1.00", []),
    ],
)
def test_unit_price_tolerance(price: str, tolerance: str, expected: list[EX]) -> None:
    item = line(price=price)
    result = run(item, rules=MatchingRules(D(tolerance), D("300")))
    assert codes(result) == expected
    assert result.lines[item.id].po_unit_price == D("10.00")


def test_price_message_is_readable() -> None:
    result = run(line(price="10.60"))
    assert result.findings[0].message == (
        "Line 1: unit price 10.6 USD differs from the PO unit price 10 USD by 0.6 USD (tolerance 0.5 USD)."
    )


def test_missing_unit_price_raises_ex6() -> None:
    assert codes(run(line(price=None))) == [EX.EX6]


def test_ex6_line_is_still_checked_for_quantity() -> None:
    result = run(line(price="11.00", qty="12"))
    assert codes(result) == [EX.EX6, EX.EX7]


# TS-05 three-way: goods receipts --------------------------------------------------------------------------


def test_trade_po_sums_goods_receipts() -> None:
    item = line(qty="7")
    result = run(item, receipts=[gr("4", number="GR1"), gr("3", number="GR2")])
    assert codes(result) == []
    assert result.lines[item.id].expected_quantity == D("7")


def test_trade_po_without_goods_receipt_raises_ex8() -> None:
    item = line()
    result = run(item, receipts=[gr("5", po_line=2)])
    assert codes(result) == [EX.EX8]
    assert result.lines[item.id].expected_quantity is None


# TS-06 quantity -------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("qty", "expected"), [("5", []), ("6", []), ("7", [EX.EX7])])
def test_quantity_must_not_exceed_received_minus_invoiced(qty: str, expected: list[EX]) -> None:
    item = line(qty=qty)
    result = run(item, invoiced={("0100001", 1): D("4")})
    assert codes(result) == expected
    assert result.lines[item.id].expected_quantity == D("6")


def test_non_trade_quantity_is_ordered_minus_invoiced_and_needs_no_receipt() -> None:
    item = line(po="1100001", qty="3")
    result = run(item, receipts=[], invoiced={("1100001", 1): D("8")})
    assert codes(result) == [EX.EX7]
    assert result.lines[item.id].expected_quantity == D("2")
    assert "ordered and not yet invoiced" in result.findings[0].message


def test_missing_quantity_raises_ex7() -> None:
    result = run(line(qty=None))
    assert codes(result) == [EX.EX7] and "invoiced no quantity" in result.findings[0].message


# TS-07 two lines on the same PO line (EC-01) --------------------------------------------------------------


def test_lines_on_the_same_po_line_are_added_up() -> None:
    first, second = line(1, qty="6"), line(2, qty="5")
    result = run(first, second)
    assert codes(result) == [EX.EX7, EX.EX7]
    assert {f.line_id for f in result.findings} == {first.id, second.id}
    assert result.findings[0].message.startswith("Lines 1, 2 together: invoiced 11, expected at most 10")
    assert codes(run(line(1, qty="6"), line(2, qty="4"))) == []


# TS-12 vendor (BR-15, EC-05) ------------------------------------------------------------------------------


def test_vendor_mismatch_raises_ex10_and_skips_price_and_quantity() -> None:
    item = line(price="99.00", qty="99")
    result = run(item, vendor="V002")
    assert codes(result) == [EX.EX10]
    assert result.lines[item.id].po_unit_price is None and result.lines[item.id].expected_quantity is None


# BR-12 decision -------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("open_exceptions", "total", "status", "approval"),
    [
        (True, "100", InvoiceStatus.EXCEPTION, False),
        (False, "300.00", InvoiceStatus.PENDING_REVIEW, False),
        (False, "300.01", InvoiceStatus.PENDING_APPROVAL, True),
        (False, None, InvoiceStatus.PENDING_APPROVAL, True),
    ],
)
def test_decision(open_exceptions: bool, total: str | None, status: InvoiceStatus, approval: bool) -> None:
    decision = decide(open_exceptions, D(total) if total else None, RULES)
    assert decision.status is status and decision.requires_approval is approval
