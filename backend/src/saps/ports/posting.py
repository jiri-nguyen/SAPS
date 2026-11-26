"""Persistence port of the `post_invoice` job (SAPS-49, ADR-0013)."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from saps.domain.invoices import InvoiceStatus
from saps.ports.erp_posting import PostingRequest
from saps.ports.processing_calendar import CalendarSnapshot


@dataclass(frozen=True)
class InvoiceToPost:
    id: UUID
    tenant_id: UUID
    status: InvoiceStatus
    posting_held_at: datetime | None
    request: PostingRequest


class PostingRepository(Protocol):
    async def lock_invoice(self, invoice_id: UUID) -> InvoiceToPost | None:
        """Read the invoice with its lines and lock its row for the rest of the transaction."""
        ...

    async def calendar_of(self, tenant_id: UUID) -> CalendarSnapshot:
        """The processing calendar of the company (DEC-070)."""
        ...

    async def hold(self, invoice: InvoiceToPost, *, now: datetime) -> bool:
        """Set `posting_held_at` and record `POSTING_HOLD`; False when it was already held (DEC-070)."""
        ...

    async def mark_posted(self, invoice: InvoiceToPost, document_number: str, *, now: datetime) -> None:
        """Status Posted with the document number and the posting time; record `POST` (BR-02)."""
        ...


PostingUnitOfWork = Callable[[], AbstractAsyncContextManager[PostingRepository]]
"""Starts a transaction and gives its repository; commits when the block ends, rolls back on an error."""
