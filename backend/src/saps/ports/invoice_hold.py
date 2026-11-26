"""Persistence port of "Process now": an Accounting Manager lets one held invoice through (SAPS-52 BR-06)."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from saps.domain.invoices import InvoiceStatus


@dataclass(frozen=True)
class HeldInvoice:
    id: UUID
    tenant_id: UUID
    status: InvoiceStatus


class InvoiceHoldRepository(Protocol):
    async def lock_invoice(self, tenant_id: UUID, invoice_id: UUID) -> HeldInvoice | None:
        """The invoice of this tenant, its row locked until the end of the unit of work."""
        ...

    async def release_by_manager(self, invoice: HeldInvoice, *, actor: str, now: datetime) -> None:
        """On hold → Uploaded, `released_from_hold_at` set, event `RELEASE_HOLD` by the manager."""
        ...


InvoiceHoldUnitOfWork = Callable[[], AbstractAsyncContextManager[InvoiceHoldRepository]]
