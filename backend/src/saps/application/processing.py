"""`process_invoice` use case (SAPS-18 BR-01): extraction, duplicate check (SAPS-23), matching (SAPS-19).

Runs in one transaction with the invoice row locked (ADR-0004 S2, TD-01).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from saps.application.matching import SYSTEM_ACTOR, MatchingService, MatchOutcome
from saps.application.notifications import notify_status
from saps.domain.extraction import unusable_reason
from saps.domain.invoices import ExceptionCode, InvoiceStatus, ensure_transition
from saps.ports.extraction import ExtractionPort
from saps.ports.processing import ProcessingRepository

NOT_IN_SAMPLE_SET = "The file is not in the dummy sample set."


@dataclass(frozen=True)
class ProcessOutcome:
    invoice_id: UUID
    tenant_id: UUID
    found: bool
    line_count: int
    unreadable_reason: str | None
    matching: MatchOutcome | None


class ProcessInvoiceService:
    def __init__(
        self,
        repository: ProcessingRepository,
        extraction: ExtractionPort,
        matching: MatchingService,
        clock: Callable[[], datetime],
    ) -> None:
        self._repo = repository
        self._extraction = extraction
        self._matching = matching
        self._clock = clock

    async def process(self, invoice_id: UUID) -> ProcessOutcome | None:
        """Process an invoice in status Uploaded; None for a duplicate or stale message (ADR-0004 S2)."""
        invoice = await self._repo.lock_invoice(invoice_id)
        if invoice is None or invoice.status is not InvoiceStatus.UPLOADED:
            return None

        extracted = await self._extraction.extract(invoice.file)
        reason = NOT_IN_SAMPLE_SET if extracted is None else unusable_reason(extracted)
        if extracted is None or reason is not None:
            assert reason is not None
            ensure_transition(invoice.status, InvoiceStatus.EXCEPTION)
            await self._repo.raise_unreadable(invoice, reason, actor=SYSTEM_ACTOR, now=self._clock())
            await notify_status(self._repo, invoice, InvoiceStatus.EXCEPTION, [ExceptionCode.EX1])
            return ProcessOutcome(invoice.id, invoice.tenant_id, extracted is not None, 0, reason, None)

        ensure_transition(invoice.status, InvoiceStatus.MATCHING)
        await self._repo.save_extraction(invoice, extracted, actor=SYSTEM_ACTOR, now=self._clock())
        # The duplicate check (EX9, SAPS-23) runs here, before matching.
        outcome = await self._matching.match(invoice.id)
        return ProcessOutcome(invoice.id, invoice.tenant_id, True, len(extracted.lines), None, outcome)
