"""Volume check of the invoice search (SAPS-46 TS-07): one company with one year of invoices.

Run by hand, it is not part of the normal test run:

    uv run pytest -m volume -s tests/integration/test_search_volume.py

It generates about 365,000 invoices (about 1,000 per day) with a line each, prints the time of the default
page and of every filter with the plan of the default query, and checks that the default order uses its index.
There is no time target (SAPS-46 Q4); the measured times are reported.
"""

import time
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.invoice_repository import SqlInvoiceRepository
from saps.domain.invoice_search import SearchCriteria, local_day_bounds
from saps.domain.mail_intake import IntakeChannel
from saps.ports.invoices import InvoiceFilter

pytestmark = [pytest.mark.integration, pytest.mark.volume]

INVOICES = 365_000

INSERT_INVOICES = """
INSERT INTO invoice (id, tenant_id, status, currency, uploaded_by, channel, file_name, file_content_type,
    file_size_bytes, file_sha256, file_storage_key, idempotency_key, created_at, vendor_name, vendor_code,
    invoice_number, invoice_number_normalized, invoice_date, total_amount)
SELECT md5(:p || i::text)::uuid, :t,
    (ARRAY['UPLOADED','EXCEPTION','PENDING_REVIEW','COMPLETED','REJECTED'])[1 + i % 5], 'USD', :u, 'UPLOAD',
    'f' || i || '.pdf', 'application/pdf', 100, repeat('a', 64), 'k/' || i, :p || i,
    timestamptz '2026-03-01 00:00+00' + i * interval '86 seconds', 'Vendor ' || (i % 500), 'V' || (i % 500),
    'INV-' || i, 'inv' || i, date '2026-03-01' + (i % 365), ((i % 100000) / 100.0)::numeric(18, 2)
FROM generate_series(1, :n) AS i
"""
INSERT_LINES = """
INSERT INTO invoice_line (id, tenant_id, invoice_id, line_number, po_number, po_line_number, match_status)
SELECT md5('l' || :p || i::text)::uuid, :t, md5(:p || i::text)::uuid, 1,
    lpad((i % 90000)::text, 7, '0'), 1, 'MATCHED'
FROM generate_series(1, :n) AS i
"""


async def test_search_with_one_year_of_invoices(engine: AsyncEngine, app_engine: AsyncEngine) -> None:
    tenant, user, prefix = uuid.uuid4(), uuid.uuid4(), uuid.uuid4().hex[:6]
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO tenant (id, name, code, time_zone) VALUES (:t, :n, :c, 'Asia/Singapore')"),
            {"t": tenant, "n": f"Volume {prefix}", "c": f"v{prefix}"},
        )
        await conn.execute(
            text(
                "INSERT INTO user_account (id, tenant_id, username, display_name, role, is_active) "
                "VALUES (:u, :t, :n, 'Volume', 'ACCOUNTING_MEMBER', true)"
            ),
            {"u": user, "t": tenant, "n": f"{prefix}@volume.example.com"},
        )
        started = time.perf_counter()
        params = {"t": tenant, "u": user, "p": prefix, "n": INVOICES}
        await conn.execute(text(INSERT_INVOICES), params)
        await conn.execute(text(INSERT_LINES), params)
        print(f"\ngenerated {INVOICES} invoices with lines in {time.perf_counter() - started:.1f} s")
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text("ANALYZE invoice"))
        await conn.execute(text("ANALYZE invoice_line"))

    repo = SqlInvoiceRepository(session_factory(app_engine, tenant))
    start, end = local_day_bounds(date(2026, 6, 1), date(2026, 6, 1), "Asia/Singapore")
    cases: dict[str, InvoiceFilter] = {
        "default page (no filter)": InvoiceFilter(),
        "status COMPLETED": InvoiceFilter(statuses=("COMPLETED",)),  # type: ignore[arg-type]
        "vendor 'vendor 42' (contains)": InvoiceFilter(vendor="vendor 42"),
        "invoice number 'inv 3650' (contains)": InvoiceFilter(invoice_number="inv3650"),
        "PO number 0000042": InvoiceFilter(po_number="0000042"),
        "invoice date, one month": InvoiceFilter(
            invoice_date_from=date(2026, 6, 1), invoice_date_to=date(2026, 6, 30)
        ),
        "uploaded on one local day": InvoiceFilter(uploaded_from=start, uploaded_to=end),
        "total 100.00 to 120.00": InvoiceFilter(total_min=Decimal("100"), total_max=Decimal("120")),
        "channel MAIL (none)": InvoiceFilter(channel=IntakeChannel.MAIL),
        "combined": InvoiceFilter(
            statuses=("COMPLETED",),  # type: ignore[arg-type]
            vendor="vendor 4",
            invoice_date_from=date(2026, 3, 1),
            total_min=Decimal("10"),
        ),
    }
    print(f"{'filter':42} {'first page ms':>14} {'second page ms':>15}")
    for name, flt in cases.items():
        first_started = time.perf_counter()
        page = await repo.list_invoices(tenant, flt, 20, None)
        first = (time.perf_counter() - first_started) * 1000
        second = float("nan")
        if page.next_page_token:
            second_started = time.perf_counter()
            await repo.list_invoices(tenant, flt, 20, page.next_page_token)
            second = (time.perf_counter() - second_started) * 1000
        print(f"{name:42} {first:14.1f} {second:15.1f}  ({len(page.items)} rows)")
    assert criteria_used(SearchCriteria(vendor="x")) == ["vendor"]

    async with app_engine.connect() as conn:
        await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant)})
        plan = "\n".join(
            row[0]
            for row in await conn.execute(
                text(
                    "EXPLAIN SELECT * FROM invoice WHERE tenant_id = :t "
                    "ORDER BY created_at DESC, id DESC LIMIT 21"
                ),
                {"t": tenant},
            )
        )
    print("\nplan of the default page:\n" + plan)
    assert "ix_invoice_tenant_created" in plan


def criteria_used(criteria: SearchCriteria) -> list[str]:
    return criteria.used()
