"""Integration: process_invoice on a real PostgreSQL with the real sample set and ERP fixtures (SAPS-18)."""

import hashlib
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saps.adapters.erp.dummy_erp import DummyErpAdapter
from saps.adapters.extraction.dummy_extraction import DummyExtractionAdapter
from saps.adapters.persistence.db import dispose_engines, session_factory
from saps.adapters.persistence.matching_repository import SqlMatchingRepository
from saps.adapters.persistence.models import (
    Invoice,
    InvoiceEvent,
    InvoiceException,
    InvoiceLine,
    MatchingSettings,
    Notification,
    Tenant,
    UserAccount,
)
from saps.adapters.persistence.processing_repository import SqlProcessingRepository
from saps.application.matching import MatchingService
from saps.application.processing import ProcessInvoiceService, ProcessOutcome
from saps.config import get_settings
from saps.domain.invoices import InvoiceStatus, InvoiceType, NotificationType
from saps.domain.users import Role

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parents[2] / "fixtures"
EXTRACTION = DummyExtractionAdapter(FIXTURES)
ERP = DummyErpAdapter(FIXTURES)
NO_LOGIN = "!"


def _file_info(file: Path) -> tuple[str, int]:
    return hashlib.sha256(file.read_bytes()).hexdigest(), file.stat().st_size


@pytest.fixture
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _tenant(engine: AsyncEngine) -> tuple[uuid.UUID, uuid.UUID]:
    """A fresh tenant with one member and one manager, so scenarios never share PO quantities (ADR-0007)."""
    async with session_factory(engine)() as session, session.begin():
        tenant = Tenant(name=f"Test tenant {uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()
        session.add(MatchingSettings(tenant_id=tenant.id))
        member = UserAccount(
            tenant_id=tenant.id, username=f"m-{uuid.uuid4().hex[:10]}", display_name="Member",
            password_hash=NO_LOGIN, role=Role.ACCOUNTING_MEMBER,
        )  # fmt: skip
        manager = UserAccount(
            tenant_id=tenant.id, username=f"g-{uuid.uuid4().hex[:10]}", display_name="Manager",
            password_hash=NO_LOGIN, role=Role.ACCOUNTING_MANAGER,
        )  # fmt: skip
        session.add_all([member, manager])
        await session.flush()
        return tenant.id, member.id


async def _uploaded(engine: AsyncEngine, file: Path) -> uuid.UUID:
    tenant_id, member_id = await _tenant(engine)
    sha, size = _file_info(file)
    async with session_factory(engine)() as session, session.begin():
        invoice = Invoice(
            tenant_id=tenant_id, status=InvoiceStatus.UPLOADED, uploaded_by=member_id, file_name=file.name,
            file_content_type="application/pdf", file_size_bytes=size, file_sha256=sha,
            file_storage_key=f"invoices/x/{sha}", idempotency_key=uuid.uuid4().hex,
        )  # fmt: skip
        session.add(invoice)
        await session.flush()
        return invoice.id


async def _process(engine: AsyncEngine, invoice_id: uuid.UUID) -> ProcessOutcome | None:
    async with session_factory(engine)() as session, session.begin():
        clock = lambda: datetime.now(UTC)  # noqa: E731
        matching = MatchingService(SqlMatchingRepository(session), ERP, clock)
        service = ProcessInvoiceService(SqlProcessingRepository(session), EXTRACTION, matching, clock)
        return await service.process(invoice_id)


async def test_known_sample_is_extracted_and_matched(engine: AsyncEngine) -> None:  # TS-01
    invoice_id = await _uploaded(engine, FIXTURES / "ds-01/invoices/ds-01-trade-po.pdf")
    outcome = await _process(engine, invoice_id)
    assert outcome is not None and outcome.found and outcome.line_count == 2
    assert outcome.matching is not None and outcome.matching.status is InvoiceStatus.PENDING_REVIEW
    async with session_factory(engine)() as session:
        invoice = await session.get_one(Invoice, invoice_id)
        lines = (
            (await session.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice_id)))
            .scalars()
            .all()
        )
        events = (
            await session.execute(
                select(InvoiceEvent.action, InvoiceEvent.status_from, InvoiceEvent.status_to)
                .where(InvoiceEvent.invoice_id == invoice_id)
                .order_by(InvoiceEvent.occurred_at)
            )
        ).all()
    assert (invoice.vendor_code, invoice.invoice_number, str(invoice.total_amount)) == (
        "V001",
        "AOS-2026-1001",
        "209.00",
    )
    assert invoice.invoice_type is InvoiceType.TRADE_PO
    assert sorted((ln.line_number, ln.po_number, str(ln.quantity)) for ln in lines) == [
        (1, "0100001", "4.000"),
        (2, "0100001", "2.000"),
    ]
    assert [tuple(e) for e in events] == [
        ("EXTRACT", InvoiceStatus.UPLOADED, InvoiceStatus.MATCHING),
        ("MATCH", InvoiceStatus.MATCHING, InvoiceStatus.PENDING_REVIEW),
    ]


async def test_unknown_file_raises_ex1_and_notifies_members(engine: AsyncEngine) -> None:  # TS-02, DS-07
    invoice_id = await _uploaded(engine, FIXTURES / "ds-07/unregistered/ds-07-unknown-invoice.pdf")
    outcome = await _process(engine, invoice_id)
    assert outcome is not None and not outcome.found and outcome.matching is None
    async with session_factory(engine)() as session:
        invoice = await session.get_one(Invoice, invoice_id)
        exception = await session.scalar(
            select(InvoiceException).where(InvoiceException.invoice_id == invoice_id)
        )
        notified = (
            await session.execute(
                select(UserAccount.role, Notification.type, Notification.message)
                .join(UserAccount, UserAccount.id == Notification.recipient_id)
                .where(Notification.invoice_id == invoice_id)
            )
        ).all()
        event = await session.scalar(select(InvoiceEvent).where(InvoiceEvent.invoice_id == invoice_id))
    assert invoice.status is InvoiceStatus.EXCEPTION
    assert exception is not None and exception.code == "EX1" and exception.invoice_line_id is None
    assert exception.message == "Invoice unreadable: The file is not in the dummy sample set."
    assert [tuple(n) for n in notified] == [
        (
            Role.ACCOUNTING_MEMBER,
            NotificationType.EXCEPTION_RAISED,
            "Invoice file ds-07-unknown-invoice.pdf has exceptions: EX1.",
        )
    ]
    assert event is not None and event.details == {
        "found": False,
        "reason": "The file is not in the dummy sample set.",
    }
    assert await _process(engine, invoice_id) is None  # stale message: already processed


# First run of every sample, each in its own tenant (demo scenarios, Test Strategy §11).
DEMO_OUTCOMES = {
    "ds-01/invoices/ds-01-trade-po.pdf": ("PENDING_REVIEW", ()),
    "ds-02/invoices/ds-02-non-trade-po.jpg": ("PENDING_REVIEW", ()),
    "ds-03/invoices/ds-03-above-threshold.pdf": ("PENDING_APPROVAL", ()),
    "ds-04/invoices/ds-04-first-delivery.pdf": ("PENDING_REVIEW", ()),
    "ds-04/invoices/ds-04-second-delivery.pdf": ("PENDING_REVIEW", ()),
    "ds-05/invoices/ds-05-two-pos.pdf": ("PENDING_REVIEW", ()),
    "ds-06/invoices/ds-06-price-within-tolerance.pdf": ("PENDING_REVIEW", ()),
    "ds-08/invoices/ds-08-non-po.pdf": ("EXCEPTION", ("EX2",)),
    "ds-09/invoices/ds-09-invalid-po-number.pdf": ("EXCEPTION", ("EX3",)),
    "ds-10/invoices/ds-10-po-not-found.pdf": ("EXCEPTION", ("EX4",)),
    "ds-11/invoices/ds-11-trade-and-non-trade.pdf": ("EXCEPTION", ("EX5",)),
    "ds-12/invoices/ds-12-price-outside-tolerance.pdf": ("EXCEPTION", ("EX6",)),
    "ds-13/invoices/ds-13-quantity-above-expected.pdf": ("EXCEPTION", ("EX7",)),
    "ds-14/invoices/ds-14-missing-goods-receipt.pdf": ("EXCEPTION", ("EX8",)),
    "ds-15/invoices/ds-15-duplicate-scan.png": ("PENDING_REVIEW", ()),  # EX9 comes with SAPS-23
    "ds-16/invoices/ds-16-rejected-at-approval.pdf": ("PENDING_APPROVAL", ()),
    "ds-17/invoices/ds-17-rejected-at-review.pdf": ("PENDING_REVIEW", ()),
    "ds-18/invoices/ds-18-settings-tolerance.pdf": ("EXCEPTION", ("EX6",)),  # matches after tolerance 1.00
    "ds-20/invoices/ds-20-vendor-mismatch.pdf": ("EXCEPTION", ("EX10",)),
}


def test_the_outcome_table_covers_every_sample() -> None:
    assert sorted(DEMO_OUTCOMES) == sorted(
        p.relative_to(FIXTURES).as_posix() for p in FIXTURES.glob("*/invoices/*") if p.suffix != ".json"
    )


@pytest.mark.parametrize(("sample", "expected"), list(DEMO_OUTCOMES.items()), ids=list(DEMO_OUTCOMES))
async def test_demo_sample_first_outcome(
    engine: AsyncEngine, sample: str, expected: tuple[str, tuple[str, ...]]
) -> None:
    outcome = await _process(engine, await _uploaded(engine, FIXTURES / sample))
    assert outcome is not None and outcome.matching is not None
    assert (outcome.matching.status.value, tuple(c.value for c in outcome.matching.open_codes)) == expected


async def test_worker_job_runs_extraction_and_matching(
    engine: AsyncEngine, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saps.worker.jobs import run_processing

    invoice_id = await _uploaded(engine, FIXTURES / "ds-17/invoices/ds-17-rejected-at-review.pdf")
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        outcome = await run_processing(invoice_id)
        assert outcome is not None and outcome.matching is not None
        assert outcome.matching.status is InvoiceStatus.PENDING_REVIEW
        assert await run_processing(invoice_id) is None
        unknown = await _uploaded(engine, FIXTURES / "ds-07/unregistered/ds-07-unknown-invoice.pdf")
        assert (await run_processing(unknown)).matching is None  # type: ignore[union-attr]
    finally:
        await dispose_engines()
        get_settings.cache_clear()
