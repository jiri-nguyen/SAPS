"""Persistence port of the `process_invoice` job, extraction part (SAPS-18)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from saps.domain.extraction import ExtractedInvoice
from saps.domain.invoices import InvoiceStatus
from saps.ports.extraction import StoredFile
from saps.ports.notifications import NotificationPort
from saps.ports.processing_calendar import CalendarSnapshot


@dataclass(frozen=True)
class InvoiceToProcess:
    id: UUID
    tenant_id: UUID
    status: InvoiceStatus
    file: StoredFile
    file_name: str
    assigned_to: UUID | None
    invoice_number: str | None = None
    vendor_name: str | None = None
    released_from_hold_at: datetime | None = None  # a manager let it through a closed period (SAPS-52 BR-06)


class ProcessingRepository(NotificationPort, Protocol):
    async def lock_invoice(self, invoice_id: UUID) -> InvoiceToProcess | None:
        """Read the invoice and lock its row for the rest of the job (ADR-0004 S2)."""
        ...

    async def calendar_of(self, tenant_id: UUID) -> CalendarSnapshot:
        """The processing calendar of the company (SAPS-52 BR-03)."""
        ...

    async def hold(self, invoice: InvoiceToProcess, *, actor: str, now: datetime) -> None:
        """Status On hold and the event `HOLD`: received on a closed day (SAPS-52 BR-03)."""
        ...

    async def save_extraction(
        self, invoice: InvoiceToProcess, extracted: ExtractedInvoice, *, actor: str, now: datetime
    ) -> None:
        """Header fields and lines (BR-05), status Matching, InvoiceEvent `EXTRACT` (BR-08)."""
        ...

    async def raise_unreadable(
        self, invoice: InvoiceToProcess, reason: str, *, actor: str, now: datetime
    ) -> None:
        """EX1 with `reason`, status Exception, InvoiceEvent `EXTRACT` with found false (BR-03, BR-04)."""
        ...
