"""ERP Posting Port (ADR-0013): posts an invoice to the ERP. Mock in Phase 2, MuleSoft later (SAPS-48)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PostingLine:
    line_number: int
    po_number: str | None
    po_line_number: int | None
    do_number: str | None
    """The received lot the line was matched against (SAPS-51), None for other lines."""
    quantity: Decimal | None
    unit_price: Decimal | None
    line_amount: Decimal | None


@dataclass(frozen=True)
class PostingRequest:
    invoice_id: UUID
    """The idempotency key: posting the same invoice twice must give the same ERP document (ADR-0013)."""
    company_code: str
    vendor_code: str | None
    invoice_number: str | None
    invoice_date: date | None
    currency: str
    subtotal_amount: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None
    lines: Sequence[PostingLine]


@dataclass(frozen=True)
class PostingResult:
    document_number: str


class ErpPostingPort(Protocol):
    async def post(self, request: PostingRequest) -> PostingResult:
        """Post the invoice; returns the ERP document. A failure raises (the job is retried)."""
        ...
