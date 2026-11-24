"""Integration: core invoice schema constraints and relationships on a real PostgreSQL (data model §4.1)."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.models import (
    Approval,
    Invoice,
    InvoiceEvent,
    InvoiceException,
    InvoiceLine,
    Notification,
    UserAccount,
)
from saps.domain.invoices import (
    ApprovalDecision,
    ExceptionCode,
    ExceptionStatus,
    InvoiceStatus,
    InvoiceType,
    MatchStatus,
    NotificationType,
)
from saps.seed import _run as run_seed

pytestmark = pytest.mark.integration


@pytest.fixture
async def db(database_url: str) -> AsyncIterator[AsyncSession]:
    await run_seed(database_url)
    engine = create_async_engine(database_url)
    try:
        async with session_factory(engine)() as session:
            yield session
    finally:
        await engine.dispose()


async def _member(db: AsyncSession) -> UserAccount:
    return (
        await db.execute(select(UserAccount).where(UserAccount.username == "member1@vn.example.com"))
    ).scalar_one()


def _invoice(user: UserAccount, idempotency_key: str | None = None) -> Invoice:
    return Invoice(
        tenant_id=user.tenant_id,
        status=InvoiceStatus.UPLOADED,
        uploaded_by=user.id,
        file_name="sample.pdf",
        file_content_type="application/pdf",
        file_size_bytes=1234,
        file_sha256="a" * 64,
        file_storage_key=f"invoices/{uuid.uuid4()}/{'a' * 64}",
        idempotency_key=idempotency_key or uuid.uuid4().hex,
    )


async def test_an_invoice_graph_round_trips(db: AsyncSession) -> None:
    user = await _member(db)
    invoice = _invoice(user)
    invoice.invoice_type = InvoiceType.TRADE_PO
    invoice.total_amount = Decimal("320.00")
    db.add(invoice)
    await db.flush()
    line = InvoiceLine(
        tenant_id=user.tenant_id,
        invoice_id=invoice.id,
        line_number=1,
        po_number="0100001",
        po_line_number=1,
        quantity=Decimal("2.000"),
        unit_price=Decimal("160.0000"),
    )
    db.add(line)
    await db.flush()
    now = datetime.now(UTC)
    db.add_all(
        [
            InvoiceException(
                tenant_id=user.tenant_id,
                invoice_id=invoice.id,
                invoice_line_id=line.id,
                code=ExceptionCode.EX6,
                message="m",
            ),
            InvoiceEvent(
                tenant_id=user.tenant_id,
                invoice_id=invoice.id,
                status_to=InvoiceStatus.UPLOADED,
                action="UPLOAD",
                actor="member1@vn.example.com",
                details={"fileName": "sample.pdf"},
            ),
            Notification(
                tenant_id=user.tenant_id,
                recipient_id=user.id,
                invoice_id=invoice.id,
                type=NotificationType.EXCEPTION_RAISED,
                message="m",
            ),
            Approval(
                tenant_id=user.tenant_id,
                invoice_id=invoice.id,
                decided_by=user.id,
                decision=ApprovalDecision.APPROVED,
                decided_at=now,
            ),
        ]
    )
    await db.commit()

    loaded = (
        await db.execute(
            select(Invoice)
            .where(Invoice.id == invoice.id)
            .options(selectinload(Invoice.lines), selectinload(Invoice.exceptions))
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert loaded.currency == "USD"
    assert loaded.invoice_type is InvoiceType.TRADE_PO
    assert loaded.lines[0].match_status is MatchStatus.NOT_MATCHED  # server default
    assert loaded.lines[0].unit_price == Decimal("160.0000")
    assert loaded.exceptions[0].status is ExceptionStatus.OPEN  # server default
    event = (await db.execute(select(InvoiceEvent).where(InvoiceEvent.invoice_id == invoice.id))).scalar_one()
    assert event.details == {"fileName": "sample.pdf"} and event.occurred_at is not None


async def test_idempotency_key_is_unique_per_tenant(db: AsyncSession) -> None:
    user = await _member(db)
    db.add(_invoice(user, "same-key"))
    await db.commit()
    db.add(_invoice(user, "same-key"))
    with pytest.raises(IntegrityError, match="uq_invoice_tenant_id_idempotency_key"):
        await db.commit()


async def test_line_numbers_are_unique_per_invoice(db: AsyncSession) -> None:
    user = await _member(db)
    invoice = _invoice(user)
    db.add(invoice)
    await db.flush()
    db.add_all(
        [InvoiceLine(tenant_id=user.tenant_id, invoice_id=invoice.id, line_number=1) for _ in range(2)]
    )
    with pytest.raises(IntegrityError, match="uq_invoice_line_invoice_id_line_number"):
        await db.commit()


@pytest.mark.parametrize("on_line", [True, False])
async def test_at_most_one_open_exception_per_code_and_line(db: AsyncSession, on_line: bool) -> None:
    user = await _member(db)
    invoice = _invoice(user)
    db.add(invoice)
    await db.flush()
    line_id = None
    if on_line:
        line = InvoiceLine(tenant_id=user.tenant_id, invoice_id=invoice.id, line_number=1)
        db.add(line)
        await db.flush()
        line_id = line.id

    def exception(status: ExceptionStatus) -> InvoiceException:
        return InvoiceException(
            tenant_id=user.tenant_id,
            invoice_id=invoice.id,
            invoice_line_id=line_id,
            code=ExceptionCode.EX2,
            message="m",
            status=status,
        )

    # A resolved exception does not block a new open one with the same code.
    db.add_all([exception(ExceptionStatus.RESOLVED), exception(ExceptionStatus.OPEN)])
    await db.commit()
    db.add(exception(ExceptionStatus.OPEN))
    with pytest.raises(IntegrityError, match="uq_invoice_exception_open"):
        await db.commit()
