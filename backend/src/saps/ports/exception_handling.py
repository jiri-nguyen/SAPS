"""Persistence port of exception handling (SAPS-20): one unit of work per operation, invoice row locked."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from saps.domain.exception_handling import InvoiceChange, InvoiceData
from saps.domain.invoices import ExceptionCode, InvoiceStatus
from saps.ports.matching import OpenException
from saps.ports.notifications import NotificationPort


@dataclass(frozen=True)
class InvoiceForHandling:
    id: UUID
    tenant_id: UUID
    status: InvoiceStatus
    assigned_to: UUID | None
    updated_at: datetime
    invoice_number: str | None
    vendor_name: str | None
    file_name: str
    total_amount: Decimal | None
    approval_threshold_applied: Decimal | None
    data: InvoiceData
    open_exceptions: tuple[OpenException, ...]

    @property
    def open_codes(self) -> list[ExceptionCode]:
        return [e.code for e in self.open_exceptions]


class ExceptionRepository(NotificationPort, Protocol):
    async def lock_invoice(self, tenant_id: UUID, invoice_id: UUID) -> InvoiceForHandling | None:
        """The invoice of this tenant with lines and open exceptions; its row stays locked until the end."""
        ...

    async def current_approval_threshold(self, tenant_id: UUID) -> Decimal: ...

    async def claim(self, invoice: InvoiceForHandling, user_id: UUID, *, actor: str, now: datetime) -> None:
        """Set `assigned_to` and record `CLAIM` (SAPS-20 BR-11)."""
        ...

    async def release(self, invoice: InvoiceForHandling, *, actor: str, now: datetime) -> None:
        """Clear `assigned_to` and record `RELEASE`."""
        ...

    async def save_update(
        self,
        invoice: InvoiceForHandling,
        change: InvoiceChange,
        *,
        status: InvoiceStatus,
        user_id: UUID,
        actor: str,
        now: datetime,
    ) -> None:
        """Header fields and lines (lines matched by number), the new status (Matching keeps the claim) and
        `UPDATE_FIELDS` with old and new values."""
        ...

    async def resolve(
        self,
        invoice: InvoiceForHandling,
        *,
        status: InvoiceStatus,
        requires_approval: bool,
        threshold: Decimal,
        user_id: UUID,
        actor: str,
        now: datetime,
    ) -> None:
        """Resolve all open exceptions as the user, set the next status, clear the claim, record `RESOLVE`."""
        ...

    async def reject(self, invoice: InvoiceForHandling, reason: str, *, actor: str, now: datetime) -> None:
        """Status Rejected with the reason, clear the claim, record `REJECT`."""
        ...


ExceptionUnitOfWork = Callable[[], AbstractAsyncContextManager[ExceptionRepository]]
"""Starts a transaction and gives its repository; commits when the block ends, rolls back on an error."""
