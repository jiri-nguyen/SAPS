"""Integration: SAPS-19 matching on a real PostgreSQL (TS-06, TS-08, TS-09, TS-10)."""

import asyncio
import logging
import random
import uuid
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal as D

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from saps.adapters.persistence.db import dispose_engines, session_factory
from saps.adapters.persistence.matching_repository import SqlMatchingRepository
from saps.adapters.persistence.models import (
    Invoice,
    InvoiceEvent,
    InvoiceException,
    InvoiceLine,
    Notification,
    UserAccount,
)
from saps.application.matching import MatchingService, MatchOutcome
from saps.config import get_settings
from saps.domain.invoices import ExceptionCode as EX
from saps.domain.invoices import ExceptionStatus, InvoiceStatus, InvoiceType, MatchStatus, NotificationType
from saps.domain.matching import GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine, PurchasingInfoRecord
from saps.seed import _run as run_seed
from tests.integration.db_urls import use_database

pytestmark = pytest.mark.integration


class MemoryErp:
    """ERP data with fresh PO numbers per test, so tests never share PO lines."""

    def __init__(
        self,
        *,
        ordered: str = "10",
        price: str = "10.00",
        trade: bool = True,
        delay: float = 0,
        lots: Sequence[tuple[str, str]] = (("DO1", "10"),),
    ) -> None:
        self.po_number = ("0" if trade else "1") + f"{random.randrange(10**6):06d}"  # noqa: S311
        self.order = PurchaseOrder(
            self.po_number, "V001", "USD", {1: PurchaseOrderLine(1, "Paper", D(ordered), D(price), "MAT1")}
        )
        self.delay = delay
        self.lots = lots  # (DO number, quantity) per goods receipt; the default is one lot of 10

    async def get_purchase_orders(
        self, company_code: str, po_numbers: Sequence[str]
    ) -> dict[str, PurchaseOrder]:
        await asyncio.sleep(self.delay)  # lets parallel runs overlap before the PO line lock
        return {self.po_number: self.order} if self.po_number in po_numbers else {}

    async def get_goods_receipt_lines(
        self, company_code: str, po_numbers: Sequence[str]
    ) -> list[GoodsReceiptLine]:
        return [
            GoodsReceiptLine(f"GR{n}", self.po_number, 1, D(quantity), do)
            for n, (do, quantity) in enumerate(self.lots, start=1)
        ]

    async def get_purchasing_info_records(
        self, company_code: str, keys: Sequence[tuple[str, str]]
    ) -> list[PurchasingInfoRecord]:
        return [PurchasingInfoRecord("V001", "MAT1", self.order.lines[1].unit_price, date(2026, 1, 1))]


@pytest.fixture
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    await run_seed(database_url)
    engine = create_async_engine(database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _member(session: AsyncSession, username: str = "member1@vn.example.com") -> UserAccount:
    return (await session.execute(select(UserAccount).where(UserAccount.username == username))).scalar_one()


async def _invoice(
    engine: AsyncEngine,
    po_number: str,
    *quantities: str,
    price: str = "10.00",
    total: str = "20.00",
    status: InvoiceStatus = InvoiceStatus.MATCHING,
    assigned: str | None = None,
    do_number: str | None = None,
    matched_do: str | None = None,
) -> uuid.UUID:
    async with session_factory(engine)() as session, session.begin():
        user = await _member(session)
        invoice = Invoice(
            tenant_id=user.tenant_id,
            status=status,
            vendor_code="V001",
            vendor_name="Alpha Supplies",
            invoice_number=f"INV-{uuid.uuid4().hex[:6]}",
            total_amount=D(total),
            invoice_date=date(2026, 12, 15),
            uploaded_by=user.id,
            assigned_to=(await _member(session, assigned)).id if assigned else None,
            file_name="sample.pdf",
            file_content_type="application/pdf",
            file_size_bytes=1,
            file_sha256="b" * 64,
            file_storage_key="invoices/x",
            idempotency_key=uuid.uuid4().hex,
        )
        session.add(invoice)
        await session.flush()
        session.add_all(
            InvoiceLine(
                tenant_id=user.tenant_id,
                invoice_id=invoice.id,
                line_number=n,
                po_number=po_number,
                po_line_number=1,
                quantity=D(q),
                unit_price=D(price),
                do_number=do_number,
                matched_do_number=matched_do,
            )
            for n, q in enumerate(quantities or ("2",), start=1)
        )
        return invoice.id


async def _match(engine: AsyncEngine, erp: MemoryErp, invoice_id: uuid.UUID) -> MatchOutcome | None:
    async with session_factory(engine)() as session, session.begin():
        service = MatchingService(SqlMatchingRepository(session), erp, lambda: datetime.now(UTC))
        return await service.match(invoice_id)


async def _notified(engine: AsyncEngine, invoice_id: uuid.UUID) -> list[tuple[str, NotificationType]]:
    async with session_factory(engine)() as session:
        rows = await session.execute(
            select(UserAccount.username, Notification.type)
            .join(UserAccount, UserAccount.id == Notification.recipient_id)
            .where(Notification.invoice_id == invoice_id)
            .order_by(UserAccount.username)
        )
        return [(name, kind) for name, kind in rows]


async def test_matched_invoice_is_saved_and_members_are_notified(engine: AsyncEngine) -> None:  # TS-09
    erp = MemoryErp()
    invoice_id = await _invoice(engine, erp.po_number, "2")
    outcome = await _match(engine, erp, invoice_id)
    assert outcome is not None and outcome.status is InvoiceStatus.PENDING_REVIEW

    async with session_factory(engine)() as session:
        invoice = await session.get_one(Invoice, invoice_id)
        assert invoice.invoice_type is InvoiceType.TRADE_PO
        assert (invoice.price_tolerance_applied, invoice.approval_threshold_applied) == (D("0.5"), D("300"))
        assert invoice.requires_approval is False
        line = (
            await session.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice_id))
        ).scalar_one()
        assert (line.match_status, line.po_unit_price, line.expected_quantity) == (
            MatchStatus.MATCHED,
            D("10.00"),
            D("10"),
        )
        event = (
            await session.execute(select(InvoiceEvent).where(InvoiceEvent.invoice_id == invoice_id))
        ).scalar_one()
        assert (event.action, event.actor, event.status_from, event.status_to) == (
            "MATCH",
            "system",
            InvoiceStatus.MATCHING,
            InvoiceStatus.PENDING_REVIEW,
        )
    assert await _notified(engine, invoice_id) == [
        ("member1@vn.example.com", NotificationType.REVIEW_REQUESTED),
        ("member2@vn.example.com", NotificationType.REVIEW_REQUESTED),
    ]


async def test_invoice_above_threshold_notifies_managers(engine: AsyncEngine) -> None:  # TS-09
    erp = MemoryErp()
    invoice_id = await _invoice(engine, erp.po_number, total="300.01")
    outcome = await _match(engine, erp, invoice_id)
    assert outcome is not None and outcome.status is InvoiceStatus.PENDING_APPROVAL
    assert await _notified(engine, invoice_id) == [
        ("manager1@vn.example.com", NotificationType.APPROVAL_REQUESTED),
    ]  # Demo Vietnam has one manager in a fresh database (SAPS-42 Q2)


async def test_exception_then_rematch_resolves_it_and_stale_message_is_skipped(
    engine: AsyncEngine,
) -> None:  # TS-10
    erp = MemoryErp()
    invoice_id = await _invoice(engine, erp.po_number, "2", price="10.60", assigned="member2@vn.example.com")
    first = await _match(engine, erp, invoice_id)
    assert first is not None and first.status is InvoiceStatus.EXCEPTION and first.open_codes == (EX.EX6,)
    assert await _notified(engine, invoice_id) == [
        ("member2@vn.example.com", NotificationType.EXCEPTION_RAISED)
    ]  # claimant only

    async with session_factory(engine)() as session, session.begin():  # what updateInvoice (SAPS-20) will do
        line = (
            await session.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice_id))
        ).scalar_one()
        line.unit_price = D("10.00")
        (await session.get_one(Invoice, invoice_id)).status = InvoiceStatus.MATCHING

    second = await _match(engine, erp, invoice_id)
    assert (
        second is not None and second.status is InvoiceStatus.PENDING_REVIEW and second.resolved == (EX.EX6,)
    )
    async with session_factory(engine)() as session:
        exception = (
            await session.execute(select(InvoiceException).where(InvoiceException.invoice_id == invoice_id))
        ).scalar_one()
        assert exception.status is ExceptionStatus.RESOLVED
        assert exception.resolved_by is None and exception.resolved_at is not None

    assert await _match(engine, erp, invoice_id) is None  # stale message (EC-03)
    async with session_factory(engine)() as session:
        events = await session.scalar(
            select(func.count()).select_from(InvoiceEvent).where(InvoiceEvent.invoice_id == invoice_id)
        )
    assert events == 2


@pytest.mark.parametrize(
    ("status", "counts"),
    [
        (InvoiceStatus.PENDING_APPROVAL, True),
        (InvoiceStatus.PENDING_REVIEW, True),
        (InvoiceStatus.COMPLETED, True),
        (InvoiceStatus.EXCEPTION, False),
        (InvoiceStatus.REJECTED, False),
        (InvoiceStatus.MATCHING, False),
    ],
)
async def test_already_invoiced_counts_only_accepted_invoices(
    engine: AsyncEngine, status: InvoiceStatus, counts: bool
) -> None:  # TS-06, BR-10
    erp = MemoryErp(trade=False, ordered="10")
    await _invoice(engine, erp.po_number, "4", status=status)
    invoice_id = await _invoice(engine, erp.po_number, "7")
    outcome = await _match(engine, erp, invoice_id)
    assert outcome is not None
    assert outcome.open_codes == ((EX.EX7,) if counts else ())
    async with session_factory(engine)() as session:
        line = (
            await session.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice_id))
        ).scalar_one()
    assert line.expected_quantity == (D("6") if counts else D("10"))


async def test_parallel_invoices_cannot_use_the_same_quantity(engine: AsyncEngine) -> None:  # TS-08, EC-02
    erp = MemoryErp(trade=False, ordered="10", delay=0.2)
    first = await _invoice(engine, erp.po_number, "6")
    second = await _invoice(engine, erp.po_number, "6")
    outcomes = await asyncio.gather(_match(engine, erp, first), _match(engine, erp, second))
    assert sorted(o.status for o in outcomes if o) == [InvoiceStatus.EXCEPTION, InvoiceStatus.PENDING_REVIEW]


async def test_worker_job_uses_the_dummy_erp_fixtures(
    engine: AsyncEngine, database_url: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from saps.worker.jobs import run_matching  # the invoice belongs to the seeded Demo Vietnam (code vn)

    invoice_id = await _invoice(engine, "0100017", "5", price="9.00", total="45.00")  # ds-17 fixture
    use_database(monkeypatch, database_url)
    get_settings.cache_clear()
    caplog.set_level(logging.INFO, logger="saps.worker.matching")
    try:
        async with engine.connect() as conn:
            tenant = (
                await conn.execute(text("SELECT tenant_id FROM invoice WHERE id = :id"), {"id": invoice_id})
            ).scalar_one()
        outcome = await run_matching(invoice_id, tenant)
        assert outcome is not None and outcome.status is InvoiceStatus.PENDING_REVIEW
        assert await run_matching(invoice_id, tenant) is None
    finally:
        await dispose_engines()
        get_settings.cache_clear()
    messages = [r.getMessage() for r in caplog.records]
    assert messages == ["matching_completed", "matching_skipped"]


async def test_po_number_is_stored_as_on_the_invoice_and_raises_ex3(
    engine: AsyncEngine,
) -> None:  # SAPS-36 follow-up
    erp = MemoryErp()
    invoice_id = await _invoice(engine, "01000017-A")  # 10 characters: not a valid PO number
    outcome = await _match(engine, erp, invoice_id)
    assert outcome is not None and outcome.open_codes == (EX.EX3,)
    async with session_factory(engine)() as session:
        line = (
            await session.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice_id))
        ).scalar_one()
    assert line.po_number == "01000017-A" and line.match_status is MatchStatus.MISMATCH


# SAPS-51 TS-07: received lots stored and counted per lot -------------------------------------------------


async def _line(engine: AsyncEngine, invoice_id: uuid.UUID) -> InvoiceLine:
    async with session_factory(engine)() as session:
        return (
            await session.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice_id))
        ).scalar_one()


async def test_the_matched_lot_and_the_pir_price_are_stored(engine: AsyncEngine) -> None:  # BR-05
    erp = MemoryErp(lots=(("DO-A", "6"), ("DO-B", "4")))
    invoice_id = await _invoice(engine, erp.po_number, "4", do_number="do b")
    outcome = await _match(engine, erp, invoice_id)
    assert outcome is not None and outcome.status is InvoiceStatus.PENDING_REVIEW
    line = await _line(engine, invoice_id)
    assert (line.do_number, line.matched_do_number) == ("do b", "DO-B")  # the user's value stays as entered
    assert (line.pir_unit_price, line.expected_quantity) == (D("10.00"), D("4"))


async def test_a_second_invoice_cannot_use_a_lot_that_is_taken(engine: AsyncEngine) -> None:
    erp = MemoryErp(lots=(("DO-A", "6"), ("DO-B", "4")))
    await _invoice(
        engine, erp.po_number, "3", status=InvoiceStatus.PENDING_REVIEW, do_number="DO-B", matched_do="DO-B"
    )
    taken = await _match(engine, erp, await _invoice(engine, erp.po_number, "2", do_number="DO-B"))
    assert taken is not None and taken.open_codes == (EX.EX7,)
    free = await _match(engine, erp, await _invoice(engine, erp.po_number, "1", do_number="DO-B"))
    assert free is not None and free.status is InvoiceStatus.PENDING_REVIEW
    other_lot = await _match(engine, erp, await _invoice(engine, erp.po_number, "6", do_number="DO-A"))
    assert other_lot is not None and other_lot.status is InvoiceStatus.PENDING_REVIEW


@pytest.mark.parametrize(
    ("status", "frees_the_lot"),
    [(InvoiceStatus.REJECTED, True), (InvoiceStatus.EXCEPTION, True), (InvoiceStatus.COMPLETED, False)],
)
async def test_a_rejected_invoice_frees_its_lot(
    engine: AsyncEngine, status: InvoiceStatus, frees_the_lot: bool
) -> None:  # EC-14, DEC-023
    erp = MemoryErp(lots=(("DO-A", "6"), ("DO-B", "4")))
    await _invoice(engine, erp.po_number, "4", status=status, do_number="DO-B", matched_do="DO-B")
    outcome = await _match(engine, erp, await _invoice(engine, erp.po_number, "4", do_number="DO-B"))
    assert outcome is not None and (outcome.open_codes == ()) is frees_the_lot


async def test_an_invoice_matched_before_saps_51_counts_for_the_po_line_only(
    engine: AsyncEngine,
) -> None:  # EC-06
    erp = MemoryErp(ordered="12", lots=(("DO-A", "6"), ("DO-B", "4")))
    await _invoice(engine, erp.po_number, "7", status=InvoiceStatus.COMPLETED)  # no matched lot
    ok = await _match(engine, erp, await _invoice(engine, erp.po_number, "3", do_number="DO-A"))
    assert ok is not None and ok.status is InvoiceStatus.PENDING_REVIEW
    over = await _match(engine, erp, await _invoice(engine, erp.po_number, "1", do_number="DO-B"))
    assert over is not None and over.open_codes == (EX.EX7,)  # 10 received, 7 + 3 invoiced


async def test_a_fully_invoiced_po_is_not_open(engine: AsyncEngine) -> None:  # EC-13
    erp = MemoryErp(trade=False, ordered="5")
    await _invoice(engine, erp.po_number, "5", status=InvoiceStatus.COMPLETED)
    outcome = await _match(engine, erp, await _invoice(engine, erp.po_number, "1"))
    assert outcome is not None and outcome.open_codes == (EX.EX4,)
    async with session_factory(engine)() as session:
        message = (await session.execute(select(InvoiceException.message))).scalars().all()[-1]
    assert "is not open" in message


async def test_the_worker_matches_the_demo_lot_scenarios(
    engine: AsyncEngine, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:  # DS-21 to DS-25 with the dummy ERP fixtures
    from saps.worker.jobs import run_matching

    cases = [
        ("0100021", "4", "DO-7000021B", "40.00", InvoiceStatus.PENDING_REVIEW, ()),
        ("0100022", "6", None, "40.00", InvoiceStatus.EXCEPTION, (EX.EX11,)),
        ("0100023", "6", "DO-7000023X", "40.00", InvoiceStatus.EXCEPTION, (EX.EX13,)),
        ("0100024", "3", None, "25.00", InvoiceStatus.EXCEPTION, (EX.EX12,)),
        ("0100025", "2", None, "30.00", InvoiceStatus.EXCEPTION, (EX.EX4,)),
    ]
    use_database(monkeypatch, database_url)
    get_settings.cache_clear()
    try:
        for po, quantity, do, price, status, codes in cases:
            invoice_id = await _invoice(engine, po, quantity, price=price, total="82.50", do_number=do)
            async with engine.connect() as conn:
                tenant = (
                    await conn.execute(
                        text("SELECT tenant_id FROM invoice WHERE id = :id"), {"id": invoice_id}
                    )
                ).scalar_one()
            outcome = await run_matching(invoice_id, tenant)
            assert outcome is not None and (outcome.status, outcome.open_codes) == (status, codes), po
    finally:
        await dispose_engines()
        get_settings.cache_clear()
