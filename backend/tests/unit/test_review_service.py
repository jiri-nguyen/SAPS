"""SAPS-21 final review use case with in-memory ports."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal as D
from uuid import UUID, uuid4

import pytest

from saps.application.exception_handling import ConflictError
from saps.application.invoices import InvoiceNotFoundError
from saps.application.review import ReviewService
from saps.domain.exception_handling import InvoiceData
from saps.domain.invoices import InvoiceStatus
from saps.domain.users import CurrentUser, Role
from saps.ports.exception_handling import InvoiceForHandling
from tests.fakes import NOW

MEMBER = CurrentUser(uuid4(), uuid4(), "member1", "Member", Role.ACCOUNTING_MEMBER)
DATA = InvoiceData("V001", "Alpha", "INV-1", None, None, None, D("209"), ())


def _invoice(status: InvoiceStatus = InvoiceStatus.PENDING_REVIEW) -> InvoiceForHandling:
    return InvoiceForHandling(
        uuid4(),
        MEMBER.tenant_id,
        status,
        None,
        NOW,
        "INV-1",
        "Alpha",
        "inv.pdf",
        D("209"),
        D("300"),
        DATA,
        (),
    )


class FakeRepo:
    def __init__(self, invoice: InvoiceForHandling | None) -> None:
        self.invoice = invoice
        self.confirmed: list[tuple[str, datetime]] = []

    async def lock_invoice(self, tenant_id: UUID, invoice_id: UUID) -> InvoiceForHandling | None:
        return self.invoice

    async def confirm(self, invoice: InvoiceForHandling, *, actor: str, now: datetime) -> None:
        self.confirmed.append((actor, now))


class Reader:
    async def get(self, tenant_id: UUID, invoice_id: UUID) -> str:
        return f"view of {invoice_id}"


def _service(repo: FakeRepo) -> ReviewService:
    @asynccontextmanager
    async def unit_of_work() -> AsyncIterator[FakeRepo]:
        yield repo

    return ReviewService(unit_of_work, Reader(), lambda: NOW)  # type: ignore[arg-type]


async def test_confirm_completes_the_invoice() -> None:  # BR-03
    repo = FakeRepo(_invoice())
    invoice_id = repo.invoice.id  # type: ignore[union-attr]
    assert await _service(repo).confirm(MEMBER, invoice_id) == f"view of {invoice_id}"
    assert repo.confirmed == [("member1", NOW)]


@pytest.mark.parametrize(
    "status",
    [
        InvoiceStatus.EXCEPTION,
        InvoiceStatus.PENDING_APPROVAL,
        InvoiceStatus.COMPLETED,
        InvoiceStatus.REJECTED,
    ],
)
async def test_only_invoices_waiting_for_review_can_be_confirmed(status: InvoiceStatus) -> None:  # EC-04
    repo = FakeRepo(_invoice(status))
    with pytest.raises(ConflictError, match="does not wait for the final review"):
        await _service(repo).confirm(MEMBER, uuid4())
    assert repo.confirmed == []


async def test_unknown_invoice() -> None:
    with pytest.raises(InvoiceNotFoundError):
        await _service(FakeRepo(None)).confirm(MEMBER, uuid4())
