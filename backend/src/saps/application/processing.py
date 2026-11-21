"""`process_invoice` use case (SAPS-18 BR-01): extraction, duplicate check (SAPS-23), matching (SAPS-19).

Runs in one transaction with the invoice row locked (ADR-0004 S2, TD-01).
"""

import re
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
FAILURE_PREFIX = "Processing failed after the last retry"
MAX_REASON_MESSAGE = 200  # SAPS-38 BR-02
_EXCEPTION_LINE = re.compile(r"^(?P<name>[A-Za-z_][\w.]*)(?::\s?(?P<message>.*))?$")


def describe_failure(traceback_text: str) -> str:
    """SAPS-38 BR-02: the reason for EX1 from the last traceback: error class and a shortened message.

    Never the frames of the traceback. The exception line is the last line that starts in column 0 and looks
    like `Class: message` (chained errors put "During handling of ..." lines before it, which do not match).
    """
    for line in reversed(traceback_text.splitlines()):
        found = _EXCEPTION_LINE.match(line)
        if found is None:
            continue
        name = found.group("name").rsplit(".", 1)[-1]
        message = (found.group("message") or "").strip()[:MAX_REASON_MESSAGE]
        return f"{FAILURE_PREFIX}: {name}: {message}" if message else f"{FAILURE_PREFIX}: {name}"
    return f"{FAILURE_PREFIX}: unknown error"


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
        # The matching run starts with the duplicate check (EX9, SAPS-23 BR-06).
        outcome = await self._matching.match(invoice.id)
        return ProcessOutcome(invoice.id, invoice.tenant_id, True, len(extracted.lines), None, outcome)


class FailedProcessingService:
    """SAPS-38 BR-01, BR-03: EX1 for an invoice whose `process_invoice` failed on its last retry."""

    def __init__(self, repository: ProcessingRepository, clock: Callable[[], datetime]) -> None:
        self._repo = repository
        self._clock = clock

    async def fail(self, invoice_id: UUID, reason: str) -> bool:
        """True when EX1 was raised; False for an invoice that is gone or no longer in Uploaded."""
        invoice = await self._repo.lock_invoice(invoice_id)
        if invoice is None or invoice.status is not InvoiceStatus.UPLOADED:
            return False
        ensure_transition(invoice.status, InvoiceStatus.EXCEPTION)
        await self._repo.raise_unreadable(invoice, reason, actor=SYSTEM_ACTOR, now=self._clock())
        await notify_status(self._repo, invoice, InvoiceStatus.EXCEPTION, [ExceptionCode.EX1])
        return True
