"""Extraction results (SAPS-18, data model §4.2). Pure domain code: no framework imports (ADR-0001)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ExtractedLine:
    line_number: int
    description: str | None
    po_number: str | None
    po_line_number: int | None
    quantity: Decimal | None
    unit_price: Decimal | None
    line_amount: Decimal | None
    do_number: str | None = None
    """Delivery order number on the invoice line (SAPS-51)."""


@dataclass(frozen=True)
class ExtractedInvoice:
    vendor_code: str | None
    vendor_name: str | None
    invoice_number: str | None
    invoice_date: date | None
    currency: str
    subtotal_amount: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None
    lines: Sequence[ExtractedLine]


# Column sizes of the data model (Invoice, InvoiceLine): (max length) and (total digits, decimal places).
_TEXT_LIMITS = {
    "vendor code": 20,
    "vendor name": 200,
    "invoice number": 50,
    "description": 500,
    "PO number": 20,
    "DO number": 50,
}
_AMOUNT = (18, 2)
_QUANTITY = (18, 3)
_UNIT_PRICE = (18, 4)


def _fits(value: Decimal | None, digits: int, places: int) -> bool:
    if value is None:
        return True
    if not value.is_finite():
        return False
    exponent = value.as_tuple().exponent
    assert isinstance(exponent, int)  # finite values have an int exponent
    if -exponent > places:
        return False
    return abs(value) < Decimal(10) ** (digits - places)


def _text_problem(label: str, value: str | None) -> str | None:
    if value is not None and len(value) > _TEXT_LIMITS[label]:
        return f"The {label} is longer than {_TEXT_LIMITS[label]} characters."
    return None


def unusable_reason(invoice: ExtractedInvoice) -> str | None:
    """BR-04: why an extraction result cannot become invoice data, or None when it can (EX1 otherwise)."""
    if invoice.currency != "USD":
        return f"The currency {invoice.currency} is not supported (USD only)."
    if not invoice.lines:
        return "The extraction result has no lines."
    problems = [
        _text_problem("vendor code", invoice.vendor_code),
        _text_problem("vendor name", invoice.vendor_name),
        _text_problem("invoice number", invoice.invoice_number),
    ]
    for amount in (invoice.subtotal_amount, invoice.tax_amount, invoice.total_amount):
        if not _fits(amount, *_AMOUNT):
            problems.append("An invoice amount does not fit 18 digits with 2 decimals.")
    numbers = [line.line_number for line in invoice.lines]
    if len(set(numbers)) != len(numbers) or min(numbers) < 1:
        problems.append("Line numbers must be unique and start at 1 or above.")
    for line in invoice.lines:
        problems.append(_text_problem("description", line.description))
        problems.append(_text_problem("PO number", line.po_number))
        problems.append(_text_problem("DO number", line.do_number))
        if line.po_line_number is not None and line.po_line_number < 1:
            problems.append(f"Line {line.line_number} has an invalid PO line number.")
        if line.quantity is not None and line.quantity < 0:
            problems.append(f"Line {line.line_number} has a negative quantity.")
        checks = ((line.quantity, _QUANTITY, "quantity"), (line.unit_price, _UNIT_PRICE, "unit price"))
        for value, size, label in (*checks, (line.line_amount, _AMOUNT, "line amount")):
            if not _fits(value, *size):
                problems.append(f"Line {line.line_number}: the {label} does not fit the data model.")
    return next((p for p in problems if p is not None), None)
