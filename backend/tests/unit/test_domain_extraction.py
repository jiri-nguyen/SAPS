"""SAPS-18 BR-04: when an extraction result is unusable (TS-03)."""

from dataclasses import replace
from decimal import Decimal as D

import pytest

from saps.domain.extraction import ExtractedInvoice, ExtractedLine, unusable_reason

LINE = ExtractedLine(1, "Paper", "0100001", 1, D("2"), D("10.00"), D("20.00"))
INVOICE = ExtractedInvoice("V001", "Alpha", "INV-1", None, "USD", D("20.00"), D("2.00"), D("22.00"), [LINE])


def test_a_complete_result_is_usable() -> None:
    assert unusable_reason(INVOICE) is None


def test_missing_values_are_still_usable() -> None:  # matching raises its own exceptions for them
    sparse = ExtractedLine(1, None, None, None, None, None, None)
    assert (
        unusable_reason(ExtractedInvoice(None, None, None, None, "USD", None, None, None, [sparse])) is None
    )


@pytest.mark.parametrize(
    ("invoice", "reason"),
    [
        (replace(INVOICE, lines=[]), "The extraction result has no lines."),
        (replace(INVOICE, currency="EUR"), "The currency EUR is not supported (USD only)."),
        (replace(INVOICE, vendor_code="V" * 21), "The vendor code is longer than 20 characters."),
        (replace(INVOICE, invoice_number="N" * 51), "The invoice number is longer than 50 characters."),
        (
            replace(INVOICE, total_amount=D("22.001")),
            "An invoice amount does not fit 18 digits with 2 decimals.",
        ),
        (
            replace(INVOICE, total_amount=D("1E+17")),
            "An invoice amount does not fit 18 digits with 2 decimals.",
        ),
        (
            replace(INVOICE, total_amount=D("NaN")),
            "An invoice amount does not fit 18 digits with 2 decimals.",
        ),
        (replace(INVOICE, lines=[LINE, LINE]), "Line numbers must be unique and start at 1 or above."),
        (
            replace(INVOICE, lines=[replace(LINE, line_number=0)]),
            "Line numbers must be unique and start at 1 or above.",
        ),
        (
            replace(INVOICE, lines=[replace(LINE, po_number="P" * 21)]),
            "The PO number is longer than 20 characters.",
        ),
        (
            replace(INVOICE, lines=[replace(LINE, description="d" * 501)]),
            "The description is longer than 500 characters.",
        ),
        (replace(INVOICE, lines=[replace(LINE, po_line_number=0)]), "Line 1 has an invalid PO line number."),
        (replace(INVOICE, lines=[replace(LINE, quantity=D("-1"))]), "Line 1 has a negative quantity."),
        (
            replace(INVOICE, lines=[replace(LINE, quantity=D("1.0001"))]),
            "Line 1: the quantity does not fit the data model.",
        ),
        (
            replace(INVOICE, lines=[replace(LINE, unit_price=D("1.00001"))]),
            "Line 1: the unit price does not fit the data model.",
        ),
        (
            replace(INVOICE, lines=[replace(LINE, line_amount=D("1.001"))]),
            "Line 1: the line amount does not fit the data model.",
        ),
    ],
)
def test_unusable_results(invoice: ExtractedInvoice, reason: str) -> None:
    assert unusable_reason(invoice) == reason
