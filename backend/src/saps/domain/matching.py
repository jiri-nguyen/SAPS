"""Invoice matching rules (SAPS-19). Pure domain code: no framework imports (ADR-0001).

All arithmetic uses Decimal (SAPS-19 §3.3). Every line is checked and every finding is collected, so the
Accounting Member sees all problems at once (SAPS-19 §6).
"""

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from saps.domain.invoices import ExceptionCode, InvoiceStatus, InvoiceType, MatchStatus

PoLineKey = tuple[str, int]
"""(PO number, PO line number)."""

_VALID_PO_NUMBER = re.compile(r"[01]\d{6}")  # DEC-005: 7 digits, prefix 0 (trade) or 1 (non-trade)
_EX = ExceptionCode


# --- ERP data (data model §4.2), read through the ERP Data Port -------------------------------------------


@dataclass(frozen=True)
class PurchaseOrderLine:
    po_line_number: int
    description: str
    ordered_quantity: Decimal
    unit_price: Decimal


@dataclass(frozen=True)
class PurchaseOrder:
    po_number: str
    vendor_code: str
    currency: str
    lines: Mapping[int, PurchaseOrderLine]


@dataclass(frozen=True)
class GoodsReceiptLine:
    gr_number: str
    po_number: str
    po_line_number: int
    received_quantity: Decimal


# --- Input and result ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class LineToMatch:
    id: UUID
    line_number: int
    po_number: str | None
    po_line_number: int | None
    quantity: Decimal | None
    unit_price: Decimal | None


@dataclass(frozen=True)
class InvoiceToMatch:
    vendor_code: str | None
    total_amount: Decimal | None
    lines: Sequence[LineToMatch]


@dataclass(frozen=True)
class MatchingRules:
    """Snapshot of the tenant's MatchingSettings taken at the start of a run (BR-11)."""

    price_tolerance: Decimal
    approval_threshold: Decimal


def settings_errors(rules: MatchingRules) -> dict[str, str]:
    """SAPS-28 BR-03 (DEC-045): both settings are 0 USD or more. Keys are the API field names."""
    errors: dict[str, str] = {}
    if rules.price_tolerance < 0:
        errors["priceToleranceUsd"] = "The price tolerance must be 0 or more."
    if rules.approval_threshold < 0:
        errors["approvalThresholdUsd"] = "The approval threshold must be 0 or more."
    return errors


@dataclass(frozen=True)
class Finding:
    """An exception found by matching; `line_id` is None for header-level codes (EX1, EX2, EX5)."""

    code: ExceptionCode
    line_id: UUID | None
    message: str


@dataclass(frozen=True)
class LineResult:
    match_status: MatchStatus
    po_unit_price: Decimal | None = None
    expected_quantity: Decimal | None = None


@dataclass(frozen=True)
class TypeDerivation:
    """Invoice type and PO-number findings (BR-01 to BR-04); `po_lines` are checked against the ERP data."""

    invoice_type: InvoiceType | None
    findings: tuple[Finding, ...]
    po_lines: tuple[LineToMatch, ...] = ()

    @property
    def po_numbers(self) -> list[str]:
        return sorted({line.po_number for line in self.po_lines if line.po_number})

    @property
    def po_line_keys(self) -> list[PoLineKey]:
        return sorted(
            {
                (line.po_number, line.po_line_number)
                for line in self.po_lines
                if line.po_number and line.po_line_number is not None
            }
        )


@dataclass(frozen=True)
class MatchResult:
    invoice_type: InvoiceType | None
    lines: Mapping[UUID, LineResult]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class Decision:
    status: InvoiceStatus
    requires_approval: bool


# --- Rules -----------------------------------------------------------------------------------------------


def _fmt(value: Decimal) -> str:
    """Readable decimal without trailing zeros or exponent: 10.5000 → 10.5, 300.00 → 300."""
    return format(value.normalize(), "f")


def _has_po(line: LineToMatch) -> bool:
    return bool(line.po_number and line.po_number.strip())


def derive_invoice_type(invoice: InvoiceToMatch) -> TypeDerivation:
    """BR-01 to BR-04, EC-04, EC-06."""
    if not invoice.lines:
        return TypeDerivation(None, (Finding(_EX.EX1, None, "The invoice has no lines."),))
    if not any(_has_po(line) for line in invoice.lines):
        return TypeDerivation(
            InvoiceType.NON_PO, (Finding(_EX.EX2, None, "Non-PO invoice: manual review is required."),)
        )

    findings: list[Finding] = []
    valid: list[LineToMatch] = []
    for line in invoice.lines:
        if not _has_po(line):
            findings.append(Finding(_EX.EX3, line.id, f"Line {line.line_number} has no PO number."))
        elif not _VALID_PO_NUMBER.fullmatch(line.po_number or ""):
            findings.append(
                Finding(
                    _EX.EX3,
                    line.id,
                    f"Line {line.line_number}: PO number {line.po_number} is not valid "
                    "(7 digits starting with 0 or 1).",
                )
            )
        else:
            valid.append(line)

    prefixes = {line.po_number[0] for line in valid if line.po_number}
    if prefixes == {"0", "1"}:
        findings.append(
            Finding(_EX.EX5, None, "The invoice refers to trade (0…) and non-trade (1…) purchase orders.")
        )
        return TypeDerivation(None, tuple(findings))
    if not prefixes:
        return TypeDerivation(None, tuple(findings))
    invoice_type = InvoiceType.TRADE_PO if prefixes == {"0"} else InvoiceType.NON_TRADE_PO
    return TypeDerivation(invoice_type, tuple(findings), tuple(valid))


@dataclass
class _LineState:
    findings: list[Finding] = field(default_factory=list)
    po_unit_price: Decimal | None = None
    expected_quantity: Decimal | None = None


def evaluate(
    invoice: InvoiceToMatch,
    derivation: TypeDerivation,
    rules: MatchingRules,
    purchase_orders: Mapping[str, PurchaseOrder],
    receipts: Sequence[GoodsReceiptLine],
    already_invoiced: Mapping[PoLineKey, Decimal],
) -> MatchResult:
    """Line checks (BR-05 to BR-10, BR-15, EC-01): PO line, vendor, unit price, quantity."""
    states = {line.id: _LineState() for line in invoice.lines}
    for finding in derivation.findings:
        if finding.line_id is not None:
            states[finding.line_id].findings.append(finding)

    groups: dict[PoLineKey, list[LineToMatch]] = defaultdict(list)
    for line in derivation.po_lines:
        po_line = _check_po_line(invoice, line, purchase_orders, rules, states[line.id])
        if po_line is not None:
            groups[(line.po_number or "", line.po_line_number or 0)].append(line)

    received: dict[PoLineKey, Decimal] = defaultdict(Decimal)
    for receipt in receipts:
        received[(receipt.po_number, receipt.po_line_number)] += receipt.received_quantity

    for key, lines in groups.items():
        _check_quantity(
            key, lines, derivation.invoice_type, purchase_orders, received, already_invoiced, states
        )

    checked = {line.id for line in derivation.po_lines}
    results: dict[UUID, LineResult] = {}
    for line in invoice.lines:
        state = states[line.id]
        if derivation.invoice_type is InvoiceType.NON_PO:
            status = MatchStatus.NOT_APPLICABLE
        elif state.findings:
            status = MatchStatus.MISMATCH
        elif line.id in checked:
            status = MatchStatus.MATCHED
        else:
            status = MatchStatus.NOT_MATCHED  # not checked: EX5 on the invoice
        results[line.id] = LineResult(status, state.po_unit_price, state.expected_quantity)

    findings = [f for f in derivation.findings if f.line_id is None]
    for line in invoice.lines:
        findings.extend(states[line.id].findings)
    return MatchResult(derivation.invoice_type, results, tuple(findings))


def _check_po_line(
    invoice: InvoiceToMatch,
    line: LineToMatch,
    purchase_orders: Mapping[str, PurchaseOrder],
    rules: MatchingRules,
    state: _LineState,
) -> PurchaseOrderLine | None:
    """BR-05, BR-15, BR-06. Returns the PO line when the quantity check should run."""
    order = purchase_orders.get(line.po_number or "")
    po_line = order.lines.get(line.po_line_number) if order and line.po_line_number is not None else None
    if order is None or po_line is None:
        what = f"PO {line.po_number}" if order is None else f"PO {line.po_number} line {line.po_line_number}"
        state.findings.append(Finding(_EX.EX4, line.id, f"Line {line.line_number}: {what} was not found."))
        return None
    if order.vendor_code != invoice.vendor_code:
        state.findings.append(
            Finding(
                _EX.EX10,
                line.id,
                f"Line {line.line_number}: the invoice vendor {invoice.vendor_code} does not match "
                f"vendor {order.vendor_code} of PO {order.po_number}.",
            )
        )
        return None

    state.po_unit_price = po_line.unit_price
    if line.unit_price is None:
        state.findings.append(Finding(_EX.EX6, line.id, f"Line {line.line_number} has no unit price."))
    else:
        difference = abs(line.unit_price - po_line.unit_price)
        if difference > rules.price_tolerance:  # inclusive bound (BR-06, EC-07)
            state.findings.append(
                Finding(
                    _EX.EX6,
                    line.id,
                    f"Line {line.line_number}: unit price {_fmt(line.unit_price)} USD differs from "
                    f"the PO unit price {_fmt(po_line.unit_price)} USD by {_fmt(difference)} USD "
                    f"(tolerance {_fmt(rules.price_tolerance)} USD).",
                )
            )
    return po_line


def _check_quantity(
    key: PoLineKey,
    lines: Sequence[LineToMatch],
    invoice_type: InvoiceType | None,
    purchase_orders: Mapping[str, PurchaseOrder],
    received: Mapping[PoLineKey, Decimal],
    already_invoiced: Mapping[PoLineKey, Decimal],
    states: Mapping[UUID, _LineState],
) -> None:
    """BR-07 to BR-10 and EC-01: lines on the same PO line are added up."""
    po_number, po_line_number = key
    invoiced = already_invoiced.get(key, Decimal(0))
    if invoice_type is InvoiceType.TRADE_PO:
        if key not in received:
            for line in lines:
                states[line.id].findings.append(
                    Finding(
                        _EX.EX8,
                        line.id,
                        f"Line {line.line_number}: no goods receipt for "
                        f"PO {po_number} line {po_line_number}.",
                    )
                )
            return
        expected = received[key] - invoiced
        basis = "received and not yet invoiced"
    else:
        expected = purchase_orders[po_number].lines[po_line_number].ordered_quantity - invoiced
        basis = "ordered and not yet invoiced"

    for line in lines:
        states[line.id].expected_quantity = expected
    quantities = [line.quantity for line in lines]
    total = sum((q for q in quantities if q is not None), Decimal(0))
    if None not in quantities and total <= expected:
        return  # a smaller quantity passes: partial invoicing (BR-09)

    numbers = ", ".join(str(line.line_number) for line in lines)
    invoiced_text = "no quantity" if None in quantities else _fmt(total)
    label = f"Line {numbers}" if len(lines) == 1 else f"Lines {numbers} together"
    for line in lines:
        states[line.id].findings.append(
            Finding(
                _EX.EX7,
                line.id,
                f"{label}: invoiced {invoiced_text}, expected at most {_fmt(expected)} "
                f"({basis}) for PO {po_number} line {po_line_number}.",
            )
        )


def decide(has_open_exceptions: bool, total_amount: Decimal | None, rules: MatchingRules) -> Decision:
    """BR-12. A missing total amount is treated as above the threshold (the Accounting Manager decides)."""
    requires_approval = total_amount is None or total_amount > rules.approval_threshold
    if has_open_exceptions:
        return Decision(InvoiceStatus.EXCEPTION, requires_approval)
    status = InvoiceStatus.PENDING_APPROVAL if requires_approval else InvoiceStatus.PENDING_REVIEW
    return Decision(status, requires_approval)
