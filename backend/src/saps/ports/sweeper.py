"""Persistence port of the stuck-invoice sweeper (SAPS-37)."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from saps.domain.invoices import InvoiceStatus


@dataclass(frozen=True)
class StuckInvoice:
    id: UUID
    tenant_id: UUID
    status: InvoiceStatus
    resends: int = 0
    """Number of `RESEND` events of the invoice (SAPS-38 BR-05)."""


class StuckInvoiceRepository(Protocol):
    async def try_lock(self) -> bool:
        """The sweeper lock of this transaction; False when another SAPS Worker process sweeps (BR-03)."""
        ...

    async def lock_stuck(self, older_than_seconds: int, limit: int) -> list[StuckInvoice]:
        """Invoices in Uploaded or Matching not updated for `older_than_seconds` (database clock), oldest
        first, row-locked; invoices whose job is running are skipped (BR-01, BR-03, BR-06)."""
        ...

    async def mark_gave_up(self, invoice: StuckInvoice) -> None:
        """Set `updated_at` and record `RESEND_LIMIT`; the invoice is never selected again (SAPS-38 BR-05)."""
        ...

    async def mark_resent(self, invoice: StuckInvoice, message: str) -> None:
        """Set `updated_at` and record the event `RESEND` (BR-04)."""
        ...


SweepUnitOfWork = Callable[[], AbstractAsyncContextManager[StuckInvoiceRepository]]
"""Starts a transaction and gives its repository; commits when the block ends, rolls back on an error."""
