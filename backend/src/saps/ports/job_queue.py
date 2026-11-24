"""Job Queue Port (ADR-0004): messages carry the invoice ID and its company (SAPS-41 BR-06)."""

from typing import Protocol
from uuid import UUID


class JobQueuePort(Protocol):
    async def send_process_invoice(self, invoice_id: UUID, tenant_id: UUID) -> None: ...

    async def send_rematch_invoice(self, invoice_id: UUID, tenant_id: UUID) -> None: ...
