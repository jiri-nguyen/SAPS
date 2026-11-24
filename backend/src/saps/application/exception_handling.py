"""Exception handling use cases (SAPS-20): claim, release, correct, accept as is, reject.

Every operation runs in one transaction with the invoice row locked. Check order: 404 (tenant), 409 (status),
403 (claimant), 412 (ETag), 422 (business rules).
"""

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from saps.application.invoices import InvoiceNotFoundError, etag_matches, etag_of
from saps.application.notifications import notify_status
from saps.domain.duplicates import STATUS_LABEL
from saps.domain.exception_handling import (
    LineData,
    UpdateRefusedError,
    apply_update,
    ensure_can_release,
    refused_codes,
    status_after_acceptance,
)
from saps.domain.invoices import InvoiceStatus, ensure_transition
from saps.domain.users import AccessDeniedError, CurrentUser
from saps.ports.exception_handling import ExceptionUnitOfWork, InvoiceForHandling
from saps.ports.invoices import InvoiceReader, InvoiceView
from saps.ports.job_queue import JobQueuePort

log = logging.getLogger("saps.api.exceptions")


class HandlingError(Exception):
    """An operation that is refused; `detail` is shown to the user."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ConflictError(HandlingError):
    """409: wrong status, already claimed, not claimed."""


class ForbiddenError(HandlingError):
    """403: not the claimant."""


class PreconditionFailedError(HandlingError):
    """412: the invoice changed since it was read (EC-02)."""


class UnprocessableError(HandlingError):
    """422: a business rule refuses the request."""


@dataclass(frozen=True)
class UpdateResult:
    invoice: InvoiceView
    rematch: bool  # True: a matching field changed and re-matching is queued (202)


class ExceptionHandlingService:
    def __init__(
        self,
        unit_of_work: ExceptionUnitOfWork,
        reader: InvoiceReader,
        queue: JobQueuePort,
        clock: Callable[[], datetime],
    ) -> None:
        self._uow = unit_of_work
        self._reader = reader
        self._queue = queue
        self._clock = clock

    async def claim(self, user: CurrentUser, invoice_id: UUID) -> InvoiceView:
        async with self._uow() as repo:
            invoice = await self._lock(repo, user, invoice_id)
            _ensure_in_exception(invoice)
            if invoice.assigned_to is None:  # BR-01, EC-01: the row lock makes the second claimant see this
                await repo.claim(invoice, user.user_id, actor=user.username, now=self._clock())
            elif invoice.assigned_to != user.user_id:
                raise ConflictError("The invoice is already claimed by another member.")
        return await self._view(user, invoice_id)

    async def release(self, user: CurrentUser, invoice_id: UUID) -> None:
        async with self._uow() as repo:
            invoice = await self._lock(repo, user, invoice_id)
            _ensure_in_exception(invoice)
            try:
                claimed = ensure_can_release(user, invoice.assigned_to)
            except AccessDeniedError as exc:
                raise ForbiddenError(str(exc)) from exc
            if not claimed:
                raise ConflictError("The invoice is not claimed.")
            await repo.release(invoice, actor=user.username, now=self._clock())

    async def update(
        self,
        user: CurrentUser,
        invoice_id: UUID,
        if_match: str,
        header: Mapping[str, Any],
        lines: Sequence[LineData] | None,
    ) -> UpdateResult:
        rematch = False
        async with self._uow() as repo:
            invoice = await self._lock(repo, user, invoice_id)
            _ensure_in_exception(invoice)
            _ensure_claimant(user, invoice)
            _ensure_etag(invoice, if_match)
            try:
                change = apply_update(invoice.data, header, lines)
            except UpdateRefusedError as exc:
                raise UnprocessableError(str(exc)) from exc
            if not change.is_empty:  # EC-08: nothing saved, no event
                status = InvoiceStatus.MATCHING if change.matching else invoice.status
                if change.matching:
                    ensure_transition(invoice.status, status)
                await repo.save_update(
                    invoice,
                    change,
                    status=status,
                    user_id=user.user_id,
                    actor=user.username,
                    now=self._clock(),
                )
                rematch = change.matching
        if rematch:
            await self._queue_rematch(invoice_id, user.tenant_id)
        return UpdateResult(await self._view(user, invoice_id), rematch)

    async def resolve(self, user: CurrentUser, invoice_id: UUID, if_match: str) -> InvoiceView:
        async with self._uow() as repo:
            invoice = await self._lock(repo, user, invoice_id)
            _ensure_in_exception(invoice)
            _ensure_claimant(user, invoice)
            _ensure_etag(invoice, if_match)
            if not invoice.open_exceptions:
                raise ConflictError("The invoice has no open exceptions.")
            refused = refused_codes(invoice.open_codes)
            if refused:  # BR-06, EC-04
                codes = ", ".join(code.value for code in refused)
                raise UnprocessableError(
                    f"{codes} cannot be accepted as is: correct the data or reject the invoice."
                )
            threshold = invoice.approval_threshold_applied
            if threshold is None:
                threshold = await repo.current_approval_threshold(invoice.tenant_id)
            status, requires_approval = status_after_acceptance(invoice.total_amount, threshold)
            ensure_transition(invoice.status, status)
            await repo.resolve(
                invoice,
                status=status,
                requires_approval=requires_approval,
                threshold=threshold,
                user_id=user.user_id,
                actor=user.username,
                now=self._clock(),
            )
            await notify_status(repo, invoice, status, [])
        return await self._view(user, invoice_id)

    async def reject(
        self, user: CurrentUser, invoice_id: UUID, reason: str
    ) -> tuple[InvoiceView, InvoiceStatus]:
        """Reject during exception handling (claimant only, SAPS-20 BR-08) or at final review (any Accounting
        Member, no claim: SAPS-21 BR-02, BR-04). Returns the invoice and the status it was rejected from."""
        async with self._uow() as repo:
            invoice = await self._lock(repo, user, invoice_id)
            if invoice.status is not InvoiceStatus.PENDING_REVIEW:
                _ensure_in_exception(invoice)  # Pending approval is rejected by a manager (SAPS-22)
                _ensure_claimant(user, invoice)
            ensure_transition(invoice.status, InvoiceStatus.REJECTED)
            await repo.reject(invoice, reason, actor=user.username, now=self._clock())
        return await self._view(user, invoice_id), invoice.status

    # --- helpers -----------------------------------------------------------------------------------

    @staticmethod
    async def _lock(repo: Any, user: CurrentUser, invoice_id: UUID) -> InvoiceForHandling:
        invoice: InvoiceForHandling | None = await repo.lock_invoice(user.tenant_id, invoice_id)
        if invoice is None:
            raise InvoiceNotFoundError(invoice_id)
        return invoice

    async def _view(self, user: CurrentUser, invoice_id: UUID) -> InvoiceView:
        view = await self._reader.get(user.tenant_id, invoice_id)
        if view is None:  # pragma: no cover - read right after a committed change in the same tenant
            raise InvoiceNotFoundError(invoice_id)
        return view

    async def _queue_rematch(self, invoice_id: UUID, tenant_id: UUID) -> None:
        try:
            await self._queue.send_rematch_invoice(invoice_id, tenant_id)
        except Exception:  # the invoice stays in Matching until the sweeper re-sends the message (EC-05)
            log.warning("rematch_not_sent", extra={"invoice_id": str(invoice_id)})


def _ensure_in_exception(invoice: InvoiceForHandling) -> None:
    """EC-03: only invoices in Exception can be handled; Matching means a re-match is pending."""
    if invoice.status is InvoiceStatus.MATCHING:
        raise ConflictError("Re-matching is in progress.")
    if invoice.status is not InvoiceStatus.EXCEPTION:
        raise ConflictError(
            f"The invoice is not in exception handling (status {STATUS_LABEL[invoice.status]})."
        )


def _ensure_claimant(user: CurrentUser, invoice: InvoiceForHandling) -> None:
    """BR-02, EC-10."""
    if invoice.assigned_to is None:
        raise ForbiddenError("Claim the invoice first.")
    if invoice.assigned_to != user.user_id:
        raise ForbiddenError("The invoice is claimed by another member.")


def _ensure_etag(invoice: InvoiceForHandling, if_match: str) -> None:
    if not etag_matches(if_match, etag_of(invoice.updated_at)):
        raise PreconditionFailedError("The invoice changed since you loaded it. Reload and try again.")
