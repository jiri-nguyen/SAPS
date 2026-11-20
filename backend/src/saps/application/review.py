"""Final review (SAPS-21): an Accounting Member confirms the result of an invoice in PendingReview.

No claim: any Accounting Member of the tenant may confirm, including the uploader (BR-02, DEC-041).
One transaction with the invoice row locked; check order 404 (tenant), 409 (status, also when another
member acted first, EC-01).
Rejecting at final review goes through `rejectInvoice` (`ExceptionHandlingService.reject`).
"""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from saps.application.exception_handling import ConflictError
from saps.application.invoices import InvoiceNotFoundError
from saps.domain.duplicates import STATUS_LABEL
from saps.domain.invoices import InvoiceStatus, ensure_transition
from saps.domain.users import CurrentUser
from saps.ports.exception_handling import ReviewUnitOfWork
from saps.ports.invoices import InvoiceReader, InvoiceView


class ReviewService:
    def __init__(
        self, unit_of_work: ReviewUnitOfWork, reader: InvoiceReader, clock: Callable[[], datetime]
    ) -> None:
        self._uow = unit_of_work
        self._reader = reader
        self._clock = clock

    async def confirm(self, user: CurrentUser, invoice_id: UUID) -> InvoiceView:
        """BR-03: Completed, a final state meaning "ready for posting"; posting happens outside the system."""
        async with self._uow() as repo:
            invoice = await repo.lock_invoice(user.tenant_id, invoice_id)
            if invoice is None:
                raise InvoiceNotFoundError(invoice_id)
            if invoice.status is not InvoiceStatus.PENDING_REVIEW:  # EC-04; EC-01: the first action wins
                raise ConflictError(
                    f"The invoice does not wait for the final review (status {STATUS_LABEL[invoice.status]})."
                )
            ensure_transition(invoice.status, InvoiceStatus.COMPLETED)
            await repo.confirm(invoice, actor=user.username, now=self._clock())
        view = await self._reader.get(user.tenant_id, invoice_id)
        if view is None:  # pragma: no cover - read right after a committed change in the same tenant
            raise InvoiceNotFoundError(invoice_id)
        return view
