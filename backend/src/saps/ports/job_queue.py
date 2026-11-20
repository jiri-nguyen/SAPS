"""Job Queue Port (ADR-0004): messages to the SAPS Worker carry only the invoice ID."""

from typing import Protocol
from uuid import UUID


class JobQueuePort(Protocol):
    async def send_process_invoice(self, invoice_id: UUID) -> None: ...

    async def send_rematch_invoice(self, invoice_id: UUID) -> None: ...
