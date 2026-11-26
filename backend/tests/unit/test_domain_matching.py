"""SAPS-19 matching rules (TS-01 … TS-05, TS-07, TS-12)."""

from datetime import date
from decimal import Decimal as D
from uuid import uuid4

import pytest

from saps.domain.invoices import ExceptionCode as EX
from saps.domain.invoices import InvoiceStatus, InvoiceType, MatchStatus
from saps.domain.matching import (
    GoodsReceiptLine,
    InvoicedQuantities,
    InvoiceToMatch,
    LineToMatch,
    MatchingRules,
    MatchResult,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchasingInfoRecord,
    decide,
    derive_invoice_type,
    evaluate,
)

RULES = MatchingRules(price_tolerance=D("0.50"), approval_threshold=D("300"))
TRADE = PurchaseOrder(
    "0100001", "V001", "USD", {1: PurchaseOrderLine(1, "Paper", D("10"), D("10.00"), "MAT1")}
)
PIRS = (PurchasingInfoRecord("V001", "MAT1", D("10.00"), date(2026, 1, 1)),)
INVOICE_DATE = date(2026, 12, 1)
NON_TRADE = PurchaseOrder("1100001", "V001", "USD", {1: PurchaseOrderLine(1, "Service", D("10"), D("10.00"))})
ORDERS = {o.po_number: o for o in (TRADE, NON_TRADE)}
DEFAULT_RECEIPTS = (GoodsReceiptLine("GR1", "0100001", 1, D("10"), "DO1"),)


def line(
    n: int = 1,
    po: str | None = "0100001",
    po_line: int | None = 1,
    qty: str | None = "2",
    price: str | None = "10.00",
    do: str | None = None,
):
    return LineToMatch(uuid4(), n, po, po_line, D(qty) if qty else None, D(price) if price else None, do)


def gr(
    qty: str, po: str = "0100001", po_line: int = 1, number: str = "GR1", do: str = "DO1"
) -> GoodsReceiptLine:
    return GoodsReceiptLine(number, po, po_line, D(qty), do)


def run(
    *lines: LineToMatch,
    vendor: str = "V001",
    receipts=DEFAULT_RECEIPTS,
    invoiced=None,
    rules=RULES,
    pirs=PIRS,
    orders=ORDERS,
    on: date | None = INVOICE_DATE,
) -> MatchResult:
    invoice = InvoiceToMatch(vendor, D("100"), lines, on)
    if not isinstance(invoiced, InvoicedQuantities):
        invoiced = InvoicedQuantities(invoiced or {})
    return evaluate(
        invoice, derive_invoice_type(invoice), rules, orders, list(receipts), invoiced, list(pirs)
    )


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
        "Line 1: unit price 10.6 USD differs from the purchasing info record price 10 USD by 0.6 USD "
        "(tolerance 0.5 USD)."
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
    result = run(item, invoiced=InvoicedQuantities({("0100001", 1): D("4")}, {("0100001", 1, "do1"): D("4")}))
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


# SAPS-51 TS-01 … TS-05: received lot, PIR price, open PO --------------------------------------------------

TWO_LOTS = [gr("6", number="GR1", do="DO-A"), gr("4", number="GR2", do="DO-B")]


def test_one_lot_is_matched_without_a_do_number() -> None:  # EC-01
    item = line(qty="3")
    result = run(item)
    assert codes(result) == [] and result.lines[item.id].matched_do_number == "DO1"


def test_one_lot_rejects_another_do_number() -> None:  # EC-02, MTG-20270301-9 R13
    result = run(line(do="DO-9"))
    assert codes(result) == [EX.EX13] and "DO-9" in result.findings[0].message
    assert "DO1" in result.findings[0].message


def test_one_lot_accepts_its_own_do_number() -> None:
    item = line(do="do 1")  # normalized like invoice numbers (BR-04, EC-08)
    assert codes(run(item)) == []


def test_several_lots_need_a_do_number() -> None:
    result = run(line(), receipts=TWO_LOTS)
    assert codes(result) == [EX.EX11]


def test_several_lots_reject_an_unknown_do_number() -> None:
    result = run(line(do="DO-X"), receipts=TWO_LOTS)
    assert codes(result) == [EX.EX13] and "DO-A, DO-B" in result.findings[0].message


def test_several_lots_match_the_lot_of_the_do_number() -> None:
    item = line(qty="4", do="DO-B")
    result = run(item, receipts=TWO_LOTS)
    assert codes(result) == []
    assert result.lines[item.id].matched_do_number == "DO-B"
    assert result.lines[item.id].expected_quantity == D("4")


def test_the_quantity_is_checked_against_the_lot_not_the_whole_po_line() -> None:
    result = run(line(qty="5", do="DO-B"), receipts=TWO_LOTS)
    assert codes(result) == [EX.EX7] and "received lot DO-B" in result.findings[0].message


def test_already_invoiced_quantity_of_the_lot_is_deducted() -> None:
    invoiced = InvoicedQuantities({("0100001", 1): D("3")}, {("0100001", 1, "dob"): D("3")})
    assert codes(run(line(qty="1", do="DO-B"), receipts=TWO_LOTS, invoiced=invoiced)) == []
    assert codes(run(line(qty="2", do="DO-B"), receipts=TWO_LOTS, invoiced=invoiced)) == [EX.EX7]


def test_two_goods_receipts_with_the_same_do_number_are_one_lot() -> None:  # EC-07
    receipts = [
        gr("4", number="GR1", do="DO-A"),
        gr("3", number="GR2", do="DO-A"),
        gr("5", number="GR3", do="DO-B"),
    ]
    item = line(qty="7", do="DO-A")
    result = run(item, receipts=receipts)
    assert codes(result) == [] and result.lines[item.id].expected_quantity == D("7")


def test_lines_on_the_same_lot_are_added_up() -> None:  # EC-04
    result = run(line(1, qty="3", do="DO-A"), line(2, qty="4", do="DO-A"), receipts=TWO_LOTS)
    assert codes(result) == [EX.EX7, EX.EX7]
    assert "Lines 1, 2 together" in result.findings[0].message


def test_lines_on_two_lots_are_checked_per_lot_and_per_po_line() -> None:  # EC-05
    ok = run(line(1, qty="6", do="DO-A"), line(2, qty="4", do="DO-B"), receipts=TWO_LOTS)
    assert codes(ok) == []
    older = InvoicedQuantities({("0100001", 1): D("2")})  # an invoice matched before SAPS-51: no lot
    result = run(line(1, qty="6", do="DO-A"), line(2, qty="4", do="DO-B"), receipts=TWO_LOTS, invoiced=older)
    assert codes(result) == [EX.EX7, EX.EX7]  # the PO line check, one EX7 per line


def test_a_line_with_ex7_on_its_lot_gets_no_second_ex7() -> None:
    result = run(
        line(qty="5", do="DO-B"), receipts=TWO_LOTS, invoiced=InvoicedQuantities({("0100001", 1): D("9")})
    )
    assert codes(result) == [EX.EX7]


def test_a_trade_line_without_goods_receipt_skips_the_lot_checks() -> None:
    result = run(line(do="DO-9"), receipts=[])
    assert codes(result) == [EX.EX8]


def test_non_trade_lines_ignore_the_do_number() -> None:  # BR-10
    item = line(po="1100001", do="whatever")
    result = run(item, receipts=[])
    assert codes(result) == [] and result.lines[item.id].matched_do_number is None


def test_trade_price_is_checked_against_the_pir_not_the_po() -> None:
    pirs = [PurchasingInfoRecord("V001", "MAT1", D("12.00"), date(2026, 1, 1))]
    item = line(price="10.00")  # equals the PO price, 2 USD under the PIR
    result = run(item, pirs=pirs)
    assert codes(result) == [EX.EX6]
    assert result.lines[item.id].pir_unit_price == D("12.00")
    assert result.lines[item.id].po_unit_price == D("10.00")
    assert codes(run(line(price="11.60"), pirs=pirs)) == []


@pytest.mark.parametrize(
    ("valid_from", "valid_to", "expected"),
    [
        (date(2026, 12, 1), None, []),  # first day
        (date(2026, 1, 1), date(2026, 12, 1), []),  # last day
        (date(2026, 12, 2), None, [EX.EX12]),
        (date(2026, 1, 1), date(2026, 11, 30), [EX.EX12]),
    ],
)
def test_the_pir_must_be_valid_on_the_invoice_date(valid_from, valid_to, expected) -> None:
    pirs = [PurchasingInfoRecord("V001", "MAT1", D("10.00"), valid_from, valid_to)]
    assert codes(run(line(), pirs=pirs)) == expected


def test_the_pir_valid_on_the_date_wins_over_an_older_one() -> None:
    pirs = [
        PurchasingInfoRecord("V001", "MAT1", D("5.00"), date(2026, 1, 1), date(2026, 6, 30)),
        PurchasingInfoRecord("V001", "MAT1", D("10.00"), date(2026, 7, 1)),
    ]
    item = line(price="10.00")
    result = run(item, pirs=pirs)
    assert codes(result) == [] and result.lines[item.id].pir_unit_price == D("10.00")


def test_pirs_of_another_vendor_or_material_do_not_count() -> None:
    pirs = [
        PurchasingInfoRecord("V002", "MAT1", D("10.00"), date(2026, 1, 1)),
        PurchasingInfoRecord("V001", "MAT2", D("10.00"), date(2026, 1, 1)),
    ]
    result = run(line(), pirs=pirs)
    assert codes(result) == [EX.EX12] and "vendor V001 and material MAT1" in result.findings[0].message


def test_no_invoice_date_raises_ex12() -> None:  # BR-09
    result = run(line(), on=None)
    assert codes(result) == [EX.EX12] and "no date" in result.findings[0].message


def test_a_trade_po_line_without_material_number_raises_ex12() -> None:
    order = PurchaseOrder("0100001", "V001", "USD", {1: PurchaseOrderLine(1, "Paper", D("10"), D("10.00"))})
    result = run(line(), orders={"0100001": order})
    assert codes(result) == [EX.EX12] and "no material number" in result.findings[0].message


def test_ex12_does_not_skip_the_lot_and_quantity_checks() -> None:  # BR-11
    result = run(line(qty="11"), pirs=[])
    assert codes(result) == [EX.EX12, EX.EX7]


def test_the_non_trade_price_still_comes_from_the_po() -> None:
    item = line(po="1100001", price="10.60")
    result = run(item, receipts=[], pirs=[])
    assert codes(result) == [EX.EX6] and "the PO unit price" in result.findings[0].message
    assert result.lines[item.id].pir_unit_price is None


def test_a_po_closed_in_the_erp_is_not_open() -> None:  # BR-01
    closed = PurchaseOrder("0100001", "V001", "USD", TRADE.lines, is_open=False)
    result = run(line(do="DO-9"), orders={"0100001": closed})
    assert codes(result) == [EX.EX4] and "PO 0100001 is not open" in result.findings[0].message


def test_a_po_with_every_line_fully_invoiced_is_not_open() -> None:  # EC-13
    invoiced = InvoicedQuantities({("0100001", 1): D("10")})
    assert codes(run(line(qty="1"), invoiced=invoiced)) == [EX.EX4]
    non_trade = run(
        line(po="1100001", qty="1"), receipts=[], invoiced=InvoicedQuantities({("1100001", 1): D("10")})
    )
    assert codes(non_trade) == [EX.EX4]


def test_a_po_stays_open_while_one_line_has_quantity_left() -> None:
    two_lines = PurchaseOrder(
        "0100001",
        "V001",
        "USD",
        {
            1: PurchaseOrderLine(1, "Paper", D("10"), D("10.00"), "MAT1"),
            2: PurchaseOrderLine(2, "Ink", D("5"), D("10.00"), "MAT1"),
        },
    )
    invoiced = InvoicedQuantities({("0100001", 1): D("10")})
    result = run(
        line(2, qty="1", po_line=2),
        orders={"0100001": two_lines},
        invoiced=invoiced,
        receipts=[gr("5", po_line=2)],
    )
    assert codes(result) == []


def test_ex4_skips_the_later_checks_and_a_vendor_mismatch_comes_after_it() -> None:  # BR-11
    closed = PurchaseOrder("0100001", "V002", "USD", TRADE.lines, is_open=False)
    assert codes(run(line(), orders={"0100001": closed})) == [EX.EX4]  # not EX10
