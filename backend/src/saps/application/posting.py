"""`post_invoice` use case (SAPS-49 BR-02, ADR-0013): post an invoice in status Posting to the ERP.

Three steps, so the call to the ERP is never inside a database transaction:
1. lock the invoice; leave it when it is not in Posting; hold it on a closed day (DEC-070); else read it;
2. call the ERP Posting Port with the invoice ID as idempotency key;
3. lock again; when the invoice is still in Posting, set Posted with the document number.
A crash between 2 and 3 is recovered by the sweeper: the port returns the same document for the same key.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from saps.domain.invoices import InvoiceStatus, ensure_transition
from saps.domain.processing_calendar import is_closed, local_today
from saps.ports.erp_posting import ErpPostingPort
from saps.ports.posting import PostingUnitOfWork


@dataclass(frozen=True)
class PostOutcome:
    invoice_id: UUID
    tenant_id: UUID
    held: bool
    document_number: str | None = None


class PostingService:
    def __init__(
        self, unit_of_work: PostingUnitOfWork, port: ErpPostingPort, clock: Callable[[], datetime]
    ) -> None:
        self._uow = unit_of_work
        self._port = port
        self._clock = clock

    async def post(self, invoice_id: UUID) -> PostOutcome | None:
        """The outcome, or None for a stale or duplicate message (EC-01)."""
        async with self._uow() as repo:
            invoice = await repo.lock_invoice(invoice_id)
            if invoice is None or invoice.status is not InvoiceStatus.POSTING:
                return None
            now = self._clock()
            snapshot = await repo.calendar_of(invoice.tenant_id)
            if is_closed(local_today(now, snapshot.time_zone), snapshot.rules):  # DEC-070
                await repo.hold(invoice, now=now)
                return PostOutcome(invoice.id, invoice.tenant_id, held=True)
            request = invoice.request

        result = await self._port.post(request)

        async with self._uow() as repo:
            invoice = await repo.lock_invoice(invoice_id)
            if invoice is None or invoice.status is not InvoiceStatus.POSTING:  # decided meanwhile (EC-01)
                return None
            ensure_transition(invoice.status, InvoiceStatus.POSTED)
            await repo.mark_posted(invoice, result.document_number, now=self._clock())
        return PostOutcome(invoice_id, invoice.tenant_id, held=False, document_number=result.document_number)
