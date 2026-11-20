"""Exception handling rules (SAPS-20). Pure domain code: no framework imports (ADR-0001)."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields, replace
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from saps.domain.invoices import ExceptionCode, InvoiceStatus
from saps.domain.matching import MatchingRules, decide
from saps.domain.users import AccessDeniedError, CurrentUser, Role

# BR-06 (DEC-035): exceptions a member may accept as is; the others need corrected data or a rejection.
ACCEPTABLE_AS_IS = frozenset({ExceptionCode.EX2, ExceptionCode.EX6, ExceptionCode.EX7, ExceptionCode.EX9})

# BR-05 (DEC-024): a change to one of these sends the invoice to re-matching.
MATCHING_HEADER_FIELDS = frozenset({"vendor_code", "invoice_number"})
MATCHING_LINE_FIELDS = ("po_number", "po_line_number", "quantity", "unit_price")

HEADER_FIELDS = (
    "vendor_code",
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "subtotal_amount",
    "tax_amount",
    "total_amount",
)


class UpdateRefusedError(Exception):
    """The requested correction is not valid (answers 422)."""


@dataclass(frozen=True)
class LineData:
    line_number: int
    description: str | None = None
    po_number: str | None = None
    po_line_number: int | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    line_amount: Decimal | None = None


@dataclass(frozen=True)
class InvoiceData:
    """The editable part of an invoice (header fields and lines)."""

    vendor_code: str | None
    vendor_name: str | None
    invoice_number: str | None
    invoice_date: date | None
    subtotal_amount: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None
    lines: tuple[LineData, ...]


@dataclass(frozen=True)
class InvoiceChange:
    """What an update changes: header fields (old, new), the lines (old, new) when they differ, and whether it
    touches a matching field."""

    data: InvoiceData
    header: Mapping[str, tuple[Any, Any]]
    lines: tuple[tuple[LineData, ...], tuple[LineData, ...]] | None
    matching: bool

    @property
    def is_empty(self) -> bool:
        return not self.header and self.lines is None


def refused_codes(open_codes: Iterable[ExceptionCode]) -> list[ExceptionCode]:
    """EC-04: the open exception codes that may not be accepted as is, in code order."""
    refused = {code for code in open_codes if code not in ACCEPTABLE_AS_IS}
    return sorted(refused, key=lambda code: int(code.value[2:]))


def _matching_key(line: LineData) -> tuple[object, ...]:
    return (line.line_number, *(getattr(line, name) for name in MATCHING_LINE_FIELDS))


def apply_update(
    current: InvoiceData, header: Mapping[str, Any], lines: Sequence[LineData] | None
) -> InvoiceChange:
    """BR-04, EC-08: fields not sent stay unchanged; `lines`, when sent, replaces all lines.

    A value equal to the current one is not a change; an update without any real change saves nothing.
    """
    unknown = set(header) - set(HEADER_FIELDS)
    if unknown:
        raise ValueError(f"Not editable: {sorted(unknown)}")
    changed = {
        name: (getattr(current, name), value)
        for name, value in header.items()
        if getattr(current, name) != value
    }
    data = replace(current, **{name: new for name, (_, new) in changed.items()})
    matching = bool(MATCHING_HEADER_FIELDS & set(changed))

    lines_change = None
    if lines is not None:
        numbers = [line.line_number for line in lines]
        if not numbers or len(set(numbers)) != len(numbers) or min(numbers) < 1:
            raise UpdateRefusedError("Lines need unique line numbers starting at 1, and at least one line.")
        new_lines = tuple(sorted(lines, key=lambda line: line.line_number))
        old_lines = tuple(sorted(current.lines, key=lambda line: line.line_number))
        if new_lines != old_lines:
            lines_change = (old_lines, new_lines)
            data = replace(data, lines=new_lines)
            matching = matching or [_matching_key(line) for line in new_lines] != [
                _matching_key(line) for line in old_lines
            ]
    return InvoiceChange(data, changed, lines_change, matching)


def status_after_acceptance(
    total_amount: Decimal | None, approval_threshold: Decimal
) -> tuple[InvoiceStatus, bool]:
    """BR-06 (DEC-013): PendingApproval above the approval threshold, else PendingReview, and the flag.

    A missing total amount counts as above the threshold, like in matching (SAPS-19 EC-11).
    """
    decision = decide(False, total_amount, MatchingRules(Decimal(0), approval_threshold))
    return decision.status, decision.requires_approval


def ensure_can_release(user: CurrentUser, assigned_to: UUID | None) -> bool:
    """BR-03 (DEC-036): the claimant, or any Accounting Manager; False when nobody claimed the invoice."""
    if assigned_to is None:
        return False
    if user.role is not Role.ACCOUNTING_MANAGER and assigned_to != user.user_id:
        raise AccessDeniedError(
            "Only the member who claimed the invoice, or an Accounting Manager, can release it."
        )
    return True


def change_details(change: InvoiceChange) -> dict[str, Any]:
    """InvoiceEvent `UPDATE_FIELDS` details: changed fields and lines with old and new values (BR-11)."""

    def text(value: object) -> object:
        return None if value is None else str(value)

    def line(data: LineData) -> dict[str, object]:
        return {
            _camel(f.name): text(getattr(data, f.name)) if f.name != "line_number" else data.line_number
            for f in fields(data)
        }

    details: dict[str, Any] = {
        "fields": {
            _camel(name): {"old": text(old), "new": text(new)} for name, (old, new) in change.header.items()
        },
        "rematch": change.matching,
    }
    if change.lines is not None:
        old_lines, new_lines = change.lines
        details["lines"] = {"old": [line(d) for d in old_lines], "new": [line(d) for d in new_lines]}
    return details


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.capitalize() for part in rest)
