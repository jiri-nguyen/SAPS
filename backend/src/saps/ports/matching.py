"""Persistence port of the matching use case (SAPS-19)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from saps.domain.duplicates import DuplicateCandidate
from saps.domain.invoices import ExceptionCode, InvoiceStatus, InvoiceType
from saps.domain.matching import InvoicedQuantities, InvoiceToMatch, LineResult, MatchingRules
from saps.ports.notifications import NotificationPort


@dataclass(frozen=True)
class OpenException:
    id: UUID
    code: ExceptionCode
    line_id: UUID | None


@dataclass(frozen=True)
class InvoiceForMatching:
    id: UUID
    tenant_id: UUID
    status: InvoiceStatus
    invoice_number: str | None
    vendor_name: str | None
    file_name: str
    assigned_to: UUID | None
    invoice: InvoiceToMatch
    open_exceptions: tuple[OpenException, ...]
    company_code: str = ""
    """Selects the company's ERP data (SAPS-42 BR-03)."""


@dataclass(frozen=True)
class NewException:
    code: ExceptionCode
    line_id: UUID | None
    message: str


@dataclass(frozen=True)
class MatchUpdate:
    """Everything a matching run writes, in one transaction."""

    invoice_type: InvoiceType | None
    status: InvoiceStatus
    requires_approval: bool
    rules: MatchingRules
    lines: Mapping[UUID, LineResult]
    opened: Sequence[NewException]
    resolved: Sequence[UUID]
    messages: Mapping[UUID, str]  # still open exceptions with their current message
    event_details: Mapping[str, Any]


class MatchingRepository(NotificationPort, Protocol):
    async def lock_invoice(self, invoice_id: UUID) -> InvoiceForMatching | None:
        """Read the invoice with its lines and open exceptions, locking the row (ADR-0004 S2)."""
        ...

    async def get_rules(self, tenant_id: UUID) -> MatchingRules: ...

    async def lock_po_lines(self, tenant_id: UUID, keys: Sequence[tuple[str, int]]) -> None:
        """Transaction-level lock per PO line, in a fixed order (SAPS-19 EC-02)."""
        ...

    async def already_invoiced(
        self, tenant_id: UUID, po_numbers: Sequence[str], exclude_invoice_id: UUID
    ) -> InvoicedQuantities:
        """BR-10: quantities on other invoices in PendingApproval, PendingReview or Completed, for every
        line of the POs, per PO line and per received lot (SAPS-51 BR-06)."""
        ...

    async def lock_duplicate_key(self, tenant_id: UUID, vendor_code: str, invoice_number: str) -> None:
        """Transaction-level lock per (tenant, vendor, normalized invoice number) (SAPS-23 EC-01)."""
        ...

    async def find_duplicates(
        self, tenant_id: UUID, vendor_code: str, invoice_number: str, exclude_invoice_id: UUID
    ) -> list[DuplicateCandidate]:
        """Other invoices with this vendor and normalized number in a compared status (BR-01, BR-03)."""
        ...

    async def save_match(
        self, invoice: InvoiceForMatching, update: MatchUpdate, *, actor: str, action: str, now: datetime
    ) -> None:
        """Write line results, exceptions, the invoice status and the InvoiceEvent."""
        ...
