"""Integration: process_invoice on a real PostgreSQL with the real sample set and ERP fixtures (SAPS-18)."""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.persistence.db import dispose_engines, session_factory
from saps.adapters.persistence.models import (
    Invoice,
    InvoiceEvent,
    InvoiceException,
    InvoiceLine,
    Notification,
    UserAccount,
)
from saps.config import get_settings
from saps.domain.invoices import InvoiceStatus, InvoiceType, NotificationType
from saps.domain.users import Role
from tests.integration.db_urls import use_database
from tests.integration.pipeline import ERP, FIXTURES, process, uploaded

pytestmark = pytest.mark.integration


async def test_known_sample_is_extracted_and_matched(engine: AsyncEngine) -> None:  # TS-01
    invoice_id = await uploaded(engine, FIXTURES / "ds-01/invoices/ds-01-trade-po.pdf")
    outcome = await process(engine, invoice_id)
    assert outcome is not None and outcome.found and outcome.line_count == 2
    assert outcome.matching is not None and outcome.matching.status is InvoiceStatus.POSTING
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
        ("MATCH", InvoiceStatus.MATCHING, InvoiceStatus.POSTING),
    ]


async def test_unknown_file_raises_ex1_and_notifies_members(engine: AsyncEngine) -> None:  # TS-02, DS-07
    invoice_id = await uploaded(engine, FIXTURES / "ds-07/unregistered/ds-07-unknown-invoice.pdf")
    outcome = await process(engine, invoice_id)
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
    assert await process(engine, invoice_id) is None  # stale message: already processed


# First run of every sample, each in its own tenant (demo scenarios, Test Strategy §11).
DEMO_OUTCOMES = {
    "ds-01/invoices/ds-01-trade-po.pdf": ("POSTING", ()),
    "ds-02/invoices/ds-02-non-trade-po.jpg": ("POSTING", ()),
    "ds-03/invoices/ds-03-above-threshold.pdf": ("PENDING_APPROVAL", ()),
    "ds-04/invoices/ds-04-first-delivery.pdf": ("POSTING", ()),
    "ds-04/invoices/ds-04-second-delivery.pdf": ("POSTING", ()),
    "ds-05/invoices/ds-05-two-pos.pdf": ("POSTING", ()),
    "ds-06/invoices/ds-06-price-within-tolerance.pdf": ("POSTING", ()),
    "ds-08/invoices/ds-08-non-po.pdf": ("EXCEPTION", ("EX2",)),
    "ds-09/invoices/ds-09-invalid-po-number.pdf": ("EXCEPTION", ("EX3",)),
    "ds-10/invoices/ds-10-po-not-found.pdf": ("EXCEPTION", ("EX4",)),
    "ds-11/invoices/ds-11-trade-and-non-trade.pdf": ("EXCEPTION", ("EX5",)),
    "ds-12/invoices/ds-12-price-outside-tolerance.pdf": ("EXCEPTION", ("EX6",)),
    "ds-13/invoices/ds-13-quantity-above-expected.pdf": ("EXCEPTION", ("EX7",)),
    "ds-14/invoices/ds-14-missing-goods-receipt.pdf": ("EXCEPTION", ("EX8",)),
    "ds-15/invoices/ds-15-duplicate-scan.png": (
        "POSTING",
        (),
    ),  # alone; after DS-01 → EX9 (test_duplicates)
    "ds-16/invoices/ds-16-rejected-at-approval.pdf": ("PENDING_APPROVAL", ()),
    "ds-17/invoices/ds-17-rejected-at-review.pdf": ("POSTING", ()),
    "ds-18/invoices/ds-18-settings-tolerance.pdf": ("EXCEPTION", ("EX6",)),  # matches after tolerance 1.00
    "ds-20/invoices/ds-20-vendor-mismatch.pdf": ("EXCEPTION", ("EX10",)),
    "ds-21/invoices/ds-21-lot-by-do-number.pdf": ("POSTING", ()),  # SAPS-51
    "ds-22/invoices/ds-22-do-number-missing.pdf": ("EXCEPTION", ("EX11",)),
    "ds-23/invoices/ds-23-invalid-do-number.pdf": ("EXCEPTION", ("EX13",)),
    "ds-24/invoices/ds-24-no-purchasing-info-record.pdf": ("EXCEPTION", ("EX12",)),
    "ds-25/invoices/ds-25-po-not-open.pdf": ("EXCEPTION", ("EX4",)),
}


def test_the_outcome_table_covers_every_sample() -> None:
    assert sorted(DEMO_OUTCOMES) == sorted(
        p.relative_to(FIXTURES).as_posix() for p in FIXTURES.glob("*/invoices/*") if p.suffix != ".json"
    )


@pytest.mark.parametrize(("sample", "expected"), list(DEMO_OUTCOMES.items()), ids=list(DEMO_OUTCOMES))
async def test_demo_sample_first_outcome(
    engine: AsyncEngine, sample: str, expected: tuple[str, tuple[str, ...]]
) -> None:
    outcome = await process(engine, await uploaded(engine, FIXTURES / sample))
    assert outcome is not None and outcome.matching is not None
    assert (outcome.matching.status.value, tuple(c.value for c in outcome.matching.open_codes)) == expected


async def _tenant_of(engine: AsyncEngine, invoice_id: uuid.UUID) -> uuid.UUID:
    async with engine.connect() as conn:
        tenant: uuid.UUID = (
            await conn.execute(text("SELECT tenant_id FROM invoice WHERE id = :id"), {"id": invoice_id})
        ).scalar_one()
    return tenant


async def test_worker_job_runs_extraction_and_matching(
    engine: AsyncEngine, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saps.worker import jobs
    from saps.worker.jobs import run_processing

    monkeypatch.setattr(
        jobs, "erp_adapter", lambda name, fixtures_dir: ERP
    )  # test companies use the vn catalogue

    invoice_id = await uploaded(engine, FIXTURES / "ds-17/invoices/ds-17-rejected-at-review.pdf")
    use_database(monkeypatch, database_url)
    get_settings.cache_clear()
    try:
        tenant = await _tenant_of(engine, invoice_id)
        outcome = await run_processing(invoice_id, tenant)
        assert outcome is not None and outcome.matching is not None
        assert outcome.matching.status is InvoiceStatus.POSTING
        assert await run_processing(invoice_id, tenant) is None
        unknown = await uploaded(engine, FIXTURES / "ds-07/unregistered/ds-07-unknown-invoice.pdf")
        outcome = await run_processing(unknown, await _tenant_of(engine, unknown))
        assert outcome is not None and outcome.matching is None
    finally:
        await dispose_engines()
        get_settings.cache_clear()
