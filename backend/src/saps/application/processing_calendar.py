"""The processing calendar and the release of held invoices (SAPS-52, DEC-062).

- `ProcessingCalendarService`: both roles read the calendar, an Accounting Manager replaces its rules (BR-07).
- `InvoiceHoldService`: "Process now", an Accounting Manager lets one held invoice through (BR-06).
- `HoldReleaseService`: the SAPS Worker timer releases held invoices on open days, oldest first (BR-05).
"""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from saps.application.exception_handling import ConflictError, UnprocessableError
from saps.application.invoices import InvoiceNotFoundError
from saps.domain.invoices import InvoiceStatus
from saps.domain.processing_calendar import (
    CalendarRule,
    is_closed,
    local_today,
    next_open_day,
    rule_errors,
)
from saps.domain.users import CurrentUser
from saps.ports.invoice_hold import InvoiceHoldUnitOfWork
from saps.ports.job_queue import JobQueuePort
from saps.ports.processing_calendar import (
    CalendarView,
    HeldInvoiceRepository,
    ProcessingCalendarRepository,
)

log = logging.getLogger("saps.processing_calendar")


class InvalidCalendarError(UnprocessableError):
    """A rule that is not valid; `fields` maps the API field name to the message (EC-10)."""

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("The processing calendar is not valid.")
        self.fields = fields


@dataclass(frozen=True)
class CalendarStatus:
    """The calendar with today's state in the company's time zone (BR-08)."""

    view: CalendarView
    closed_today: bool
    open_again_on: date | None  # the first open day while closed today; None when open or never open again


class ProcessingCalendarService:
    def __init__(self, repository: ProcessingCalendarRepository, clock: Callable[[], datetime]) -> None:
        self._repo = repository
        self._clock = clock

    async def get(self, user: CurrentUser) -> CalendarStatus:
        return self._status(await self._repo.get(user.tenant_id))

    async def replace(self, user: CurrentUser, rules: Sequence[CalendarRule]) -> CalendarStatus:
        errors = rule_errors(rules)
        if errors:
            raise InvalidCalendarError(errors)
        await self._repo.replace(user.tenant_id, rules, user.username)
        log.info(
            "processing_calendar_changed",
            extra={"tenant_id": str(user.tenant_id), "user_id": str(user.user_id), "rules": len(rules)},
        )
        return self._status(await self._repo.get(user.tenant_id))

    def _status(self, view: CalendarView) -> CalendarStatus:
        today = local_today(self._clock(), view.time_zone)
        closed = is_closed(today, view.rules)
        return CalendarStatus(view, closed, next_open_day(today, view.rules) if closed else None)


class InvoiceHoldService:
    def __init__(
        self, uow: InvoiceHoldUnitOfWork, queue: JobQueuePort, clock: Callable[[], datetime]
    ) -> None:
        self._uow = uow
        self._queue = queue
        self._clock = clock

    async def release(self, user: CurrentUser, invoice_id: UUID) -> None:
        """On hold → Uploaded, then `process_invoice` is sent (a failed send is recovered by the sweeper)."""
        async with self._uow() as repo:
            invoice = await repo.lock_invoice(user.tenant_id, invoice_id)
            if invoice is None:
                raise InvoiceNotFoundError(invoice_id)
            if invoice.status is not InvoiceStatus.ON_HOLD:  # EC-07: released meanwhile by the timer
                raise ConflictError("The invoice is not on hold.")
            await repo.release_by_manager(invoice, actor=user.username, now=self._clock())
        log.info("invoice_released", extra={"invoice_id": str(invoice_id), "user_id": str(user.user_id)})
        try:
            await self._queue.send_process_invoice(invoice_id, user.tenant_id)
        except Exception:  # EC-06: the invoice stays Uploaded until the sweeper sends the message
            log.warning("process_invoice_not_sent", extra={"invoice_id": str(invoice_id)})


class HoldReleaseService:
    def __init__(
        self,
        repository: HeldInvoiceRepository,
        queue: JobQueuePort,
        clock: Callable[[], datetime],
        batch_size: int,
    ) -> None:
        self._repo = repository
        self._queue = queue
        self._clock = clock
        self._batch = batch_size

    async def release_due(self) -> int:
        """One tick: for every company that is open today, the oldest held invoices go back to Uploaded."""
        released = 0
        for company in await self._repo.list_companies():
            snapshot = await self._repo.snapshot(company.tenant_id)
            now = self._clock()
            if is_closed(local_today(now, snapshot.time_zone), snapshot.rules):
                continue
            ids = await self._repo.release_oldest(company.tenant_id, self._batch, now=now)
            for invoice_id in ids:  # after the commit; a failed send is recovered by the sweeper
                try:
                    await self._queue.send_process_invoice(invoice_id, company.tenant_id)
                except Exception:
                    log.warning("process_invoice_not_sent", extra={"invoice_id": str(invoice_id)})
            if ids:
                log.info("invoices_released", extra={"tenant_id": str(company.tenant_id), "count": len(ids)})
            released += len(ids)
        return released
