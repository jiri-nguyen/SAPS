"""Duplicate invoice rules (SAPS-23). Pure domain code: no framework imports (ADR-0001)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from saps.domain.invoices import ExceptionCode, InvoiceStatus
from saps.domain.matching import Finding

# BR-03 (DEC-039, DEC-043): Uploaded / Matching have no data yet; a Rejected one may be uploaded again.
COMPARED_STATUSES = (
    InvoiceStatus.EXCEPTION,
    InvoiceStatus.PENDING_APPROVAL,
    InvoiceStatus.PENDING_REVIEW,
    InvoiceStatus.COMPLETED,
)

STATUS_LABEL = {
    InvoiceStatus.UPLOADED: "Uploaded",
    InvoiceStatus.MATCHING: "Matching",
    InvoiceStatus.EXCEPTION: "Exception",
    InvoiceStatus.PENDING_APPROVAL: "Pending approval",
    InvoiceStatus.PENDING_REVIEW: "Pending review",
    InvoiceStatus.COMPLETED: "Completed",
    InvoiceStatus.REJECTED: "Rejected",
}

_IGNORED = re.compile(r"[\s\-./]")


@dataclass(frozen=True)
class DuplicateCandidate:
    """Another invoice of the same tenant with the same vendor and normalized invoice number."""

    id: UUID
    invoice_number: str | None
    status: InvoiceStatus


def normalize_invoice_number(number: str | None) -> str | None:
    """BR-02 (DEC-042): ignore case, spaces, `-`, `.` and `/`; keep leading zeros. "INV-0001" = "inv 0001"."""
    if number is None:
        return None
    normalized = _IGNORED.sub("", number).casefold()
    return normalized or None


def duplicate_finding(candidates: Sequence[DuplicateCandidate]) -> Finding:
    """BR-04: one EX9 on the invoice being processed, naming the other invoice(s) (EC-05: all of them)."""
    names = ", ".join(f"{c.invoice_number} ({STATUS_LABEL[c.status]})" for c in candidates)
    noun = "invoice" if len(candidates) == 1 else "invoices"
    return Finding(ExceptionCode.EX9, None, f"Duplicate of {noun} {names}.")
