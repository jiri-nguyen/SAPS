"""Approval use case (SAPS-22): an Accounting Manager approves or rejects an invoice in PendingApproval.

One transaction with the invoice row locked. Check order: 404 (tenant), 409 (status: not PendingApproval, also
when another manager decided first, EC-01), 422 (comment).
"""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from saps.application.exception_handling import ConflictError, UnprocessableError
from saps.application.invoices import InvoiceNotFoundError
from saps.application.notifications import notify_status
from saps.domain.approval import NEXT_STATUS, CommentRequiredError, checked_comment
from saps.domain.duplicates import STATUS_LABEL
from saps.domain.invoices import ApprovalDecision, InvoiceStatus, ensure_transition
from saps.domain.users import CurrentUser
from saps.ports.exception_handling import ApprovalUnitOfWork
from saps.ports.invoices import InvoiceReader, InvoiceView


class ApprovalService:
    def __init__(
        self, unit_of_work: ApprovalUnitOfWork, reader: InvoiceReader, clock: Callable[[], datetime]
    ) -> None:
        self._uow = unit_of_work
        self._reader = reader
        self._clock = clock

    async def decide(
        self, user: CurrentUser, invoice_id: UUID, decision: ApprovalDecision, comment: str | None
    ) -> InvoiceView:
        async with self._uow() as repo:
            invoice = await repo.lock_invoice(user.tenant_id, invoice_id)
            if invoice is None:
                raise InvoiceNotFoundError(invoice_id)
            if invoice.status is not InvoiceStatus.PENDING_APPROVAL:  # EC-04; EC-01: the first decision wins
                raise ConflictError(
                    f"The invoice does not wait for approval (status {STATUS_LABEL[invoice.status]})."
                )
            try:
                text = checked_comment(decision, comment)
            except CommentRequiredError as exc:
                raise UnprocessableError(str(exc)) from exc
            status = NEXT_STATUS[decision]
            ensure_transition(invoice.status, status)
            await repo.record_decision(
                invoice,
                decision,
                text,
                status=status,
                user_id=user.user_id,
                actor=user.username,
                now=self._clock(),
            )
            if decision is ApprovalDecision.APPROVED:  # BR-04; a rejection notifies nobody (BR-05, DEC-040)
                await notify_status(repo, invoice, status, [])
        view = await self._reader.get(user.tenant_id, invoice_id)
        if view is None:  # pragma: no cover - read right after a committed change in the same tenant
            raise InvoiceNotFoundError(invoice_id)
        return view
