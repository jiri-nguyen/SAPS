"""Stuck-invoice sweeper (SAPS-37): send the lost message again for invoices stuck in Uploaded or Matching.

One transaction per sweep. A failing send propagates, so the transaction rolls back and nothing is marked
(EC-03); the actors are idempotent, so a message that was sent anyway changes nothing (ADR-0004 S2).
"""

from dataclasses import dataclass
from uuid import UUID

from saps.domain.invoices import InvoiceStatus
from saps.ports.job_queue import JobQueuePort
from saps.ports.sweeper import SweepUnitOfWork

RESEND_ACTION = "RESEND"
BATCH_LIMIT = 100  # BR-06
MAX_RESENDS = 3  # SAPS-38 BR-05; the worker passes SWEEPER_MAX_RESENDS
PROCESS_MESSAGE = "process_invoice"
REMATCH_MESSAGE = "rematch_invoice"


@dataclass(frozen=True)
class Resent:
    invoice_id: UUID
    tenant_id: UUID
    message: str


@dataclass(frozen=True)
class GaveUp:
    invoice_id: UUID
    tenant_id: UUID
    resends: int


@dataclass(frozen=True)
class SweepResult:
    resent: list[Resent]
    gave_up: list[GaveUp]


class SweeperService:
    def __init__(
        self,
        unit_of_work: SweepUnitOfWork,
        queue: JobQueuePort,
        stuck_after_seconds: int,
        limit: int = BATCH_LIMIT,
        max_resends: int = MAX_RESENDS,
    ) -> None:
        self._uow = unit_of_work
        self._queue = queue
        self._stuck_after = stuck_after_seconds
        self._limit = limit
        self._max_resends = max_resends

    async def sweep(self) -> SweepResult | None:
        """What was sent again or given up, or None when another SAPS Worker process sweeps (EC-01)."""
        result = SweepResult([], [])
        async with self._uow() as repo:
            if not await repo.try_lock():
                return None
            for invoice in await repo.lock_stuck(self._stuck_after, self._limit):
                if invoice.status is InvoiceStatus.UPLOADED:  # BR-02
                    if (
                        invoice.resends >= self._max_resends
                    ):  # SAPS-38 BR-05: no EX1, the invoice stays Uploaded
                        await repo.mark_gave_up(invoice)
                        result.gave_up.append(GaveUp(invoice.id, invoice.tenant_id, invoice.resends))
                        continue
                    await self._queue.send_process_invoice(invoice.id)
                    message = PROCESS_MESSAGE
                else:
                    await self._queue.send_rematch_invoice(invoice.id)
                    message = REMATCH_MESSAGE
                await repo.mark_resent(invoice, message)
                result.resent.append(Resent(invoice.id, invoice.tenant_id, message))
        return result
