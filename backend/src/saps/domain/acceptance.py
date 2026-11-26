"""Accepted exceptions stay accepted while their values are unchanged (SAPS-49 BR-05). Pure domain code."""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from saps.domain.references import normalize_reference


@dataclass(frozen=True)
class FingerprintLine:
    """The values of one invoice line that an exception depends on (SAPS-49 BR-05)."""

    id: UUID
    line_number: int
    po_number: str | None
    po_line_number: int | None
    do_number: str | None
    quantity: Decimal | None
    unit_price: Decimal | None


def _number(value: Decimal | None) -> str:
    return "" if value is None else format(value.normalize(), "f")


def _line_values(line: FingerprintLine) -> str:
    return "|".join(
        (
            str(line.line_number),
            (line.po_number or "").strip(),
            "" if line.po_line_number is None else str(line.po_line_number),
            normalize_reference(line.do_number) or "",
            _number(line.quantity),
            _number(line.unit_price),
        )
    )


def fingerprint(
    line_id: UUID | None,
    vendor_code: str | None,
    invoice_number: str | None,
    lines: Sequence[FingerprintLine],
) -> str:
    """SHA-256 hex of the values an exception was raised on.

    A line-level exception (`line_id` set) depends on its line's values; a header-level one (EX2, EX5, EX9 …)
    on the vendor, the normalized invoice number and every line. An unknown line gives the header form.
    """
    own = next((line for line in lines if line.id == line_id), None) if line_id is not None else None
    if own is not None:
        text = f"line:{_line_values(own)}"
    else:
        header = f"{vendor_code or ''}|{normalize_reference(invoice_number) or ''}"
        text = f"header:{header}#" + "#".join(
            _line_values(line) for line in sorted(lines, key=lambda x: x.line_number)
        )
    return hashlib.sha256(text.encode()).hexdigest()
