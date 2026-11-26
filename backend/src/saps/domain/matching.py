"""Invoice matching rules (SAPS-19). Pure domain code: no framework imports (ADR-0001).

All arithmetic uses Decimal (SAPS-19 §3.3). Every line is checked and every finding is collected, so the
Accounting Member sees all problems at once (SAPS-19 §6).
"""

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from saps.domain.invoices import ExceptionCode, InvoiceStatus, InvoiceType, MatchStatus
from saps.domain.references import normalize_reference

PoLineKey = tuple[str, int]
"""(PO number, PO line number)."""

LotKey = tuple[str, int, str]
"""(PO number, PO line number, normalized DO number): a received lot (DEC-065)."""

_VALID_PO_NUMBER = re.compile(r"[01]\d{6}")  # DEC-005: 7 digits, prefix 0 (trade) or 1 (non-trade)
_EX = ExceptionCode


# --- ERP data (data model §4.2), read through the ERP Data Port -------------------------------------------


@dataclass(frozen=True)
class PurchaseOrderLine:
    po_line_number: int
    description: str
    ordered_quantity: Decimal
    unit_price: Decimal
    material_number: str | None = None
    """Identifies the purchasing info record of a trade PO line (DEC-066)."""


@dataclass(frozen=True)
class PurchaseOrder:
    po_number: str
    vendor_code: str
    currency: str
    lines: Mapping[int, PurchaseOrderLine]
    is_open: bool = True
    """False when the ERP marks the PO closed (DEC-067)."""


@dataclass(frozen=True)
class GoodsReceiptLine:
    gr_number: str
    po_number: str
    po_line_number: int
    received_quantity: Decimal
    do_number: str = ""
    """Delivery order number recorded on the goods receipt (DEC-065)."""


@dataclass(frozen=True)
class PurchasingInfoRecord:
    """Agreed price of a material for a vendor, valid in a period (DEC-066)."""

    vendor_code: str
    material_number: str
    unit_price: Decimal
    valid_from: date
    valid_to: date | None = None

    def valid_on(self, day: date) -> bool:
        return self.valid_from <= day and (self.valid_to is None or day <= self.valid_to)


@dataclass(frozen=True)
class InvoicedQuantities:
    """Already invoiced quantities on other invoices (DEC-023), for the PO lines of an invoice's POs."""

    per_line: Mapping[PoLineKey, Decimal] = field(default_factory=dict)
    per_lot: Mapping[LotKey, Decimal] = field(default_factory=dict)


# --- Input and result ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class LineToMatch:
    id: UUID
    line_number: int
    po_number: str | None
    po_line_number: int | None
    quantity: Decimal | None
    unit_price: Decimal | None
    do_number: str | None = None


@dataclass(frozen=True)
class InvoiceToMatch:
    vendor_code: str | None
    total_amount: Decimal | None
    lines: Sequence[LineToMatch]
    invoice_date: date | None = None
    invoice_number: str | None = None


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
    matched_do_number: str | None = None
    pir_unit_price: Decimal | None = None


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
    matched_do_number: str | None = None
    pir_unit_price: Decimal | None = None

    def has(self, code: ExceptionCode) -> bool:
        return any(f.code is code for f in self.findings)


@dataclass
class _Lot:
    do_number: str
    quantity: Decimal


def evaluate(
    invoice: InvoiceToMatch,
    derivation: TypeDerivation,
    rules: MatchingRules,
    purchase_orders: Mapping[str, PurchaseOrder],
    receipts: Sequence[GoodsReceiptLine],
    already_invoiced: InvoicedQuantities,
    pirs: Sequence[PurchasingInfoRecord] = (),
) -> MatchResult:
    """Line checks in the order of SAPS-51 BR-11: open PO and vendor, price, received lot, quantity."""
    states = {line.id: _LineState() for line in invoice.lines}
    for finding in derivation.findings:
        if finding.line_id is not None:
            states[finding.line_id].findings.append(finding)

    trade = derivation.invoice_type is InvoiceType.TRADE_PO
    groups: dict[PoLineKey, list[LineToMatch]] = defaultdict(list)
    for line in derivation.po_lines:
        po_line = _check_po_line(
            invoice, line, purchase_orders, rules, already_invoiced, pirs, trade, states[line.id]
        )
        if po_line is not None:
            groups[(line.po_number or "", line.po_line_number or 0)].append(line)

    lots: dict[PoLineKey, dict[str, _Lot]] = defaultdict(dict)
    for receipt in receipts:
        reference = normalize_reference(receipt.do_number) or ""
        lot = lots[(receipt.po_number, receipt.po_line_number)].setdefault(
            reference, _Lot(receipt.do_number, Decimal(0))
        )
        lot.quantity += receipt.received_quantity

    for key, lines in groups.items():
        if trade:
            _check_trade_lots(key, lines, lots.get(key, {}), already_invoiced, states)
        else:
            _check_non_trade_quantity(key, lines, purchase_orders, already_invoiced, states)

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
        results[line.id] = LineResult(
            status,
            state.po_unit_price,
            state.expected_quantity,
            state.matched_do_number,
            state.pir_unit_price,
        )

    findings = [f for f in derivation.findings if f.line_id is None]
    for line in invoice.lines:
        findings.extend(states[line.id].findings)
    return MatchResult(derivation.invoice_type, results, tuple(findings))


def _is_open(order: PurchaseOrder, invoiced: InvoicedQuantities) -> bool:
    """BR-01: not closed in the ERP and at least one line not fully invoiced."""
    if not order.is_open:
        return False
    return any(
        line.ordered_quantity > invoiced.per_line.get((order.po_number, number), Decimal(0))
        for number, line in order.lines.items()
    )


def _check_po_line(
    invoice: InvoiceToMatch,
    line: LineToMatch,
    purchase_orders: Mapping[str, PurchaseOrder],
    rules: MatchingRules,
    invoiced: InvoicedQuantities,
    pirs: Sequence[PurchasingInfoRecord],
    trade: bool,
    state: _LineState,
) -> PurchaseOrderLine | None:
    """BR-05, BR-06, BR-15, SAPS-51 BR-01, BR-08, BR-09. Returns the PO line when the quantity checks run."""
    order = purchase_orders.get(line.po_number or "")
    po_line = order.lines.get(line.po_line_number) if order and line.po_line_number is not None else None
    if order is None or po_line is None:
        what = f"PO {line.po_number}" if order is None else f"PO {line.po_number} line {line.po_line_number}"
        state.findings.append(Finding(_EX.EX4, line.id, f"Line {line.line_number}: {what} was not found."))
        return None
    if not _is_open(order, invoiced):
        state.findings.append(
            Finding(_EX.EX4, line.id, f"Line {line.line_number}: PO {order.po_number} is not open.")
        )
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
    if trade:
        reference = _pir_price(invoice, line, order, po_line, pirs, state)
        source = "the purchasing info record price"
    else:
        reference = po_line.unit_price
        source = "the PO unit price"
    if reference is None:
        return po_line
    if line.unit_price is None:
        state.findings.append(Finding(_EX.EX6, line.id, f"Line {line.line_number} has no unit price."))
    else:
        difference = abs(line.unit_price - reference)
        if difference > rules.price_tolerance:  # inclusive bound (BR-06, EC-07)
            state.findings.append(
                Finding(
                    _EX.EX6,
                    line.id,
                    f"Line {line.line_number}: unit price {_fmt(line.unit_price)} USD differs from "
                    f"{source} {_fmt(reference)} USD by {_fmt(difference)} USD "
                    f"(tolerance {_fmt(rules.price_tolerance)} USD).",
                )
            )
    return po_line


def _pir_price(
    invoice: InvoiceToMatch,
    line: LineToMatch,
    order: PurchaseOrder,
    po_line: PurchaseOrderLine,
    pirs: Sequence[PurchasingInfoRecord],
    state: _LineState,
) -> Decimal | None:
    """SAPS-51 BR-08, BR-09: the price of the PIR valid on the invoice date, or EX12 and None."""
    prefix = f"Line {line.line_number}"
    reason: str | None = None
    if invoice.invoice_date is None:
        reason = "the invoice has no date to select the purchasing info record"
    elif not po_line.material_number:
        reason = f"PO {order.po_number} line {po_line.po_line_number} has no material number"
    else:
        valid = [
            pir
            for pir in pirs
            if pir.vendor_code == order.vendor_code
            and pir.material_number == po_line.material_number
            and pir.valid_on(invoice.invoice_date)
        ]
        if valid:
            best = max(valid, key=lambda pir: pir.valid_from)
            state.pir_unit_price = best.unit_price
            return best.unit_price
        reason = (
            f"no purchasing info record for vendor {order.vendor_code} and material "
            f"{po_line.material_number} is valid on {invoice.invoice_date.isoformat()}"
        )
    state.findings.append(Finding(_EX.EX12, line.id, f"{prefix}: {reason}."))
    return None


def _check_trade_lots(
    key: PoLineKey,
    lines: Sequence[LineToMatch],
    lots: Mapping[str, _Lot],
    invoiced: InvoicedQuantities,
    states: Mapping[UUID, _LineState],
) -> None:
    """SAPS-51 BR-02 to BR-07: select the received lot of each line, then check the quantities."""
    po_number, po_line_number = key
    where = f"PO {po_number} line {po_line_number}"
    if not lots:
        for line in lines:
            states[line.id].findings.append(
                Finding(_EX.EX8, line.id, f"Line {line.line_number}: no goods receipt for {where}.")
            )
        return

    by_lot: dict[str, list[LineToMatch]] = defaultdict(list)
    for line in lines:
        given = normalize_reference(line.do_number)
        if len(lots) == 1:
            reference = next(iter(lots))
            wrong = given is not None and given != reference
        else:
            reference = given or ""
            if given is None:
                states[line.id].findings.append(
                    Finding(
                        _EX.EX11,
                        line.id,
                        f"Line {line.line_number}: {where} has several goods receipts; "
                        "the DO number is required.",
                    )
                )
                continue
            wrong = given not in lots
        if wrong:
            known = ", ".join(sorted(lot.do_number for lot in lots.values()))
            states[line.id].findings.append(
                Finding(
                    _EX.EX13,
                    line.id,
                    f"Line {line.line_number}: DO number {line.do_number} is not on a goods receipt of "
                    f"{where} (known: {known}).",
                )
            )
            continue
        by_lot[reference].append(line)
        states[line.id].matched_do_number = lots[reference].do_number

    for reference, lot_lines in by_lot.items():
        lot = lots[reference]
        expected = lot.quantity - invoiced.per_lot.get((po_number, po_line_number, reference), Decimal(0))
        for line in lot_lines:
            states[line.id].expected_quantity = expected
        _flag_quantity(
            lot_lines, expected, f"received lot {lot.do_number} and not yet invoiced", where, states
        )

    matched = [line for lot_lines in by_lot.values() for line in lot_lines]
    received = sum((lot.quantity for lot in lots.values()), Decimal(0))
    expected_total = received - invoiced.per_line.get(key, Decimal(0))
    _flag_quantity(matched, expected_total, "received and not yet invoiced", where, states)


def _check_non_trade_quantity(
    key: PoLineKey,
    lines: Sequence[LineToMatch],
    purchase_orders: Mapping[str, PurchaseOrder],
    invoiced: InvoicedQuantities,
    states: Mapping[UUID, _LineState],
) -> None:
    """BR-08, BR-09, EC-01: 2-way; lines on the same PO line are added up."""
    po_number, po_line_number = key
    expected = purchase_orders[po_number].lines[po_line_number].ordered_quantity - invoiced.per_line.get(
        key, Decimal(0)
    )
    for line in lines:
        states[line.id].expected_quantity = expected
    _flag_quantity(
        lines, expected, "ordered and not yet invoiced", f"PO {po_number} line {po_line_number}", states
    )


def _flag_quantity(
    lines: Sequence[LineToMatch],
    expected: Decimal,
    basis: str,
    where: str,
    states: Mapping[UUID, _LineState],
) -> None:
    """EX7 on the lines whose summed quantity exceeds the expected quantity; at most one EX7 per line."""
    if not lines:
        return
    quantities = [line.quantity for line in lines]
    total = sum((q for q in quantities if q is not None), Decimal(0))
    if None not in quantities and total <= expected:
        return  # a smaller quantity passes: partial invoicing (BR-09)

    flagged = [line for line in lines if not states[line.id].has(_EX.EX7)]
    if not flagged:
        return
    numbers = ", ".join(str(line.line_number) for line in lines)
    invoiced_text = "no quantity" if None in quantities else _fmt(total)
    label = f"Line {numbers}" if len(lines) == 1 else f"Lines {numbers} together"
    for line in flagged:
        states[line.id].findings.append(
            Finding(
                _EX.EX7,
                line.id,
                f"{label}: invoiced {invoiced_text}, expected at most {_fmt(expected)} "
                f"({basis}) for {where}.",
            )
        )


def decide(has_open_exceptions: bool, total_amount: Decimal | None, rules: MatchingRules) -> Decision:
    """BR-12. A missing total amount is treated as above the threshold (the Accounting Manager decides)."""
    requires_approval = total_amount is None or total_amount > rules.approval_threshold
    if has_open_exceptions:
        return Decision(InvoiceStatus.EXCEPTION, requires_approval)
    status = InvoiceStatus.PENDING_APPROVAL if requires_approval else InvoiceStatus.POSTING  # SAPS-49 BR-01
    return Decision(status, requires_approval)
