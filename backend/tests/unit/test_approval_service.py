"""SAPS-22 approval use case with in-memory ports."""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal as D
from uuid import UUID, uuid4

import pytest

from saps.application.approval import ApprovalService
from saps.application.exception_handling import ConflictError, UnprocessableError
from saps.application.invoices import InvoiceNotFoundError
from saps.domain.exception_handling import InvoiceData
from saps.domain.invoices import ApprovalDecision, InvoiceStatus, NotificationType
from saps.domain.users import CurrentUser, Role
from saps.ports.exception_handling import InvoiceForHandling
from tests.fakes import NOW

MANAGER = CurrentUser(uuid4(), uuid4(), "manager1", "Manager", Role.ACCOUNTING_MANAGER)
MEMBERS = [uuid4(), uuid4()]
DATA = InvoiceData("V001", "Alpha", "INV-1", None, None, None, D("495"), ())


def _invoice(status: InvoiceStatus = InvoiceStatus.PENDING_APPROVAL) -> InvoiceForHandling:
    return InvoiceForHandling(
        uuid4(),
        MANAGER.tenant_id,
        status,
        None,
        NOW,
        "INV-1",
        "Alpha",
        "inv.pdf",
        D("495"),
        D("300"),
        DATA,
        (),
    )


class FakeRepo:
    def __init__(self, invoice: InvoiceForHandling | None) -> None:
        self.invoice = invoice
        self.decision: tuple[ApprovalDecision, str | None, InvoiceStatus, str] | None = None
        self.notified: list[tuple[list[UUID], NotificationType, str]] = []

    async def lock_invoice(self, tenant_id: UUID, invoice_id: UUID) -> InvoiceForHandling | None:
        return self.invoice

    async def record_decision(
        self,
        invoice: InvoiceForHandling,
        decision: ApprovalDecision,
        comment: str | None,
        *,
        status: InvoiceStatus,
        user_id: UUID,
        actor: str,
        now: datetime,
    ) -> None:
        assert (user_id, now) == (MANAGER.user_id, NOW)
        self.decision = (decision, comment, status, actor)

    async def active_user_ids(self, tenant_id: UUID, role: Role) -> list[UUID]:
        assert role is Role.ACCOUNTING_MEMBER
        return MEMBERS

    async def add_notifications(
        self,
        tenant_id: UUID,
        invoice_id: UUID,
        recipients: Sequence[UUID],
        kind: NotificationType,
        message: str,
    ) -> None:
        self.notified.append((list(recipients), kind, message))


class Reader:
    """The invoice as read back after the commit."""

    async def get(self, tenant_id: UUID, invoice_id: UUID) -> str:
        return f"view of {invoice_id}"


def _service(repo: FakeRepo) -> ApprovalService:
    @asynccontextmanager
    async def unit_of_work() -> AsyncIterator[FakeRepo]:
        yield repo

    return ApprovalService(unit_of_work, Reader(), lambda: NOW)  # type: ignore[arg-type]


async def test_approval_goes_to_review_and_notifies_the_members() -> None:  # BR-04
    repo = FakeRepo(_invoice())
    invoice_id = repo.invoice.id  # type: ignore[union-attr]
    view = await _service(repo).decide(MANAGER, invoice_id, ApprovalDecision.APPROVED, " Fine. ")
    assert view == f"view of {invoice_id}"
    assert repo.decision == (ApprovalDecision.APPROVED, "Fine.", InvoiceStatus.PENDING_REVIEW, "manager1")
    assert repo.notified == [
        (MEMBERS, NotificationType.REVIEW_REQUESTED, "Invoice INV-1 from Alpha is ready for final review.")
    ]


async def test_rejection_needs_a_comment_and_notifies_nobody() -> None:  # BR-05, EC-02, DEC-040
    repo = FakeRepo(_invoice())
    for comment in (None, " "):
        with pytest.raises(UnprocessableError, match="comment is required"):
            await _service(repo).decide(MANAGER, repo.invoice.id, ApprovalDecision.REJECTED, comment)  # type: ignore[union-attr]
    assert repo.decision is None
    await _service(repo).decide(MANAGER, repo.invoice.id, ApprovalDecision.REJECTED, "PO is wrong.")  # type: ignore[union-attr]
    assert repo.decision == (ApprovalDecision.REJECTED, "PO is wrong.", InvoiceStatus.REJECTED, "manager1")
    assert repo.notified == []


@pytest.mark.parametrize(
    "status", [InvoiceStatus.EXCEPTION, InvoiceStatus.PENDING_REVIEW, InvoiceStatus.REJECTED]
)
async def test_only_invoices_waiting_for_approval_can_be_decided(status: InvoiceStatus) -> None:  # EC-04
    repo = FakeRepo(_invoice(status))
    with pytest.raises(ConflictError, match="does not wait for approval"):
        await _service(repo).decide(MANAGER, repo.invoice.id, ApprovalDecision.APPROVED, None)  # type: ignore[union-attr]
    assert repo.decision is None


async def test_unknown_invoice() -> None:
    with pytest.raises(InvoiceNotFoundError):
        await _service(FakeRepo(None)).decide(MANAGER, uuid4(), ApprovalDecision.APPROVED, None)
