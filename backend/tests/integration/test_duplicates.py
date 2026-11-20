"""Integration: SAPS-23 duplicate check on a real PostgreSQL, through process_invoice and re-match."""

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.models import Invoice, InvoiceException
from saps.domain.duplicates import normalize_invoice_number
from saps.domain.invoices import ExceptionCode, ExceptionStatus, InvoiceStatus
from tests.integration.pipeline import FIXTURES, new_tenant, process, rematch, uploaded

pytestmark = pytest.mark.integration

DS17 = FIXTURES / "ds-17/invoices/ds-17-rejected-at-review.pdf"  # V001, AOS-2026-1017


async def _other(
    engine: AsyncEngine,
    tenant: tuple[uuid.UUID, uuid.UUID],
    status: InvoiceStatus,
    number: str = "aos 2026.1017",
    vendor: str = "V001",
) -> uuid.UUID:
    """An earlier invoice with the same key (normalized like the worker does)."""
    tenant_id, member_id = tenant
    async with session_factory(engine)() as session, session.begin():
        invoice = Invoice(
            tenant_id=tenant_id, status=status, vendor_code=vendor, invoice_number=number,
            invoice_number_normalized=normalize_invoice_number(number), uploaded_by=member_id,
            file_name="earlier.pdf", file_content_type="application/pdf", file_size_bytes=1,
            file_sha256="e" * 64, file_storage_key="invoices/e", idempotency_key=uuid.uuid4().hex,
        )  # fmt: skip
        session.add(invoice)
        await session.flush()
        return invoice.id


async def _open_codes(engine: AsyncEngine, invoice_id: uuid.UUID) -> list[str]:
    async with session_factory(engine)() as session:
        rows = await session.execute(
            select(InvoiceException.code).where(
                InvoiceException.invoice_id == invoice_id, InvoiceException.status == ExceptionStatus.OPEN
            )
        )
        return sorted({code.value for code in rows.scalars()}, key=lambda c: int(c[2:]))


@pytest.mark.parametrize(
    ("status", "duplicate"),
    [
        (InvoiceStatus.EXCEPTION, True),
        (InvoiceStatus.PENDING_APPROVAL, True),
        (InvoiceStatus.PENDING_REVIEW, True),
        (InvoiceStatus.COMPLETED, True),
        (InvoiceStatus.UPLOADED, False),
        (InvoiceStatus.MATCHING, False),
        (InvoiceStatus.REJECTED, False),  # EC-03, DEC-039
    ],
)
async def test_compared_statuses(
    engine: AsyncEngine, status: InvoiceStatus, duplicate: bool
) -> None:  # TS-01
    tenant = await new_tenant(engine)
    other = await _other(engine, tenant, status)
    outcome = await process(engine, await uploaded(engine, DS17, tenant))
    assert outcome is not None and outcome.matching is not None
    assert (ExceptionCode.EX9 in outcome.matching.open_codes) is duplicate
    assert outcome.matching.duplicate_of == ((other,) if duplicate else ())


async def test_same_number_other_vendor_is_no_duplicate(engine: AsyncEngine) -> None:  # TS-03
    tenant = await new_tenant(engine)
    await _other(engine, tenant, InvoiceStatus.COMPLETED, vendor="V002")
    outcome = await process(engine, await uploaded(engine, DS17, tenant))
    assert outcome is not None and outcome.matching is not None and outcome.matching.open_codes == ()


async def test_ds15_after_ds01_gets_ex9_and_its_matching_exceptions(
    engine: AsyncEngine,
) -> None:  # EC-02, TS-05
    tenant = await new_tenant(engine)
    first = await uploaded(engine, FIXTURES / "ds-01/invoices/ds-01-trade-po.pdf", tenant)
    await process(engine, first)
    second = await uploaded(engine, FIXTURES / "ds-15/invoices/ds-15-duplicate-scan.png", tenant)
    outcome = await process(engine, second)
    assert outcome is not None and outcome.matching is not None
    assert outcome.matching.status is InvoiceStatus.EXCEPTION
    assert await _open_codes(engine, second) == ["EX7", "EX9"]  # DS-01 already took the received quantity
    assert await _open_codes(engine, first) == []  # the earlier invoice is not changed (BR-04)
    async with session_factory(engine)() as session:
        message = await session.scalar(
            select(InvoiceException.message).where(
                InvoiceException.invoice_id == second, InvoiceException.code == ExceptionCode.EX9
            )
        )
        stored = await session.get_one(Invoice, first)
    assert message == "Duplicate of invoice AOS-2026-1001 (Pending review)."
    assert stored.invoice_number_normalized == "aos20261001"  # set when extraction saves the header


async def test_parallel_copies_get_exactly_one_ex9(engine: AsyncEngine) -> None:  # TS-04, EC-01
    tenant = await new_tenant(engine)
    copies = [await uploaded(engine, DS17, tenant) for _ in range(2)]
    outcomes = await asyncio.gather(*(process(engine, c) for c in copies))
    with_ex9 = [o for o in outcomes if o and o.matching and ExceptionCode.EX9 in o.matching.open_codes]
    assert len(with_ex9) == 1


async def test_corrected_number_resolves_ex9_on_rematch(engine: AsyncEngine) -> None:  # TS-06, EC-04
    tenant = await new_tenant(engine)
    await _other(engine, tenant, InvoiceStatus.COMPLETED)
    invoice_id = await uploaded(engine, DS17, tenant)
    await process(engine, invoice_id)
    assert "EX9" in await _open_codes(engine, invoice_id)

    async with session_factory(engine)() as session, session.begin():  # what updateInvoice (SAPS-20) will do
        invoice = await session.get_one(Invoice, invoice_id)
        invoice.invoice_number = "AOS-2026-1017-B"
        invoice.invoice_number_normalized = normalize_invoice_number(invoice.invoice_number)
        invoice.status = InvoiceStatus.MATCHING
    outcome = await rematch(engine, invoice_id)
    assert outcome is not None and outcome.resolved == (ExceptionCode.EX9,)
    async with session_factory(engine)() as session:
        ex9 = await session.scalar(
            select(InvoiceException).where(
                InvoiceException.invoice_id == invoice_id, InvoiceException.code == ExceptionCode.EX9
            )
        )
    assert ex9 is not None and ex9.status is ExceptionStatus.RESOLVED
    assert ex9.resolved_by is None and ex9.resolved_at is not None and ex9.resolved_at <= datetime.now(UTC)


async def test_third_copy_names_both_earlier_invoices(engine: AsyncEngine) -> None:  # EC-05
    tenant = await new_tenant(engine)
    await _other(engine, tenant, InvoiceStatus.COMPLETED, number="AOS-2026-1017")
    await _other(engine, tenant, InvoiceStatus.PENDING_REVIEW, number="aos20261017")
    invoice_id = await uploaded(engine, DS17, tenant)
    outcome = await process(engine, invoice_id)
    assert outcome is not None and outcome.matching is not None and len(outcome.matching.duplicate_of) == 2
    async with session_factory(engine)() as session:
        message = await session.scalar(
            select(InvoiceException.message).where(
                InvoiceException.invoice_id == invoice_id, InvoiceException.code == ExceptionCode.EX9
            )
        )
    assert message == "Duplicate of invoices AOS-2026-1017 (Completed), aos20261017 (Pending review)."
