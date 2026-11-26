"""Migration 0013 on a database of its own (SAPS-49 §3.6, §4): the upgrade of old invoices and the guard."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration.conftest import alembic

pytestmark = pytest.mark.integration

INVOICE = (
    "INSERT INTO invoice (id, tenant_id, status, currency, uploaded_by, channel, file_name, "
    "file_content_type, file_size_bytes, file_sha256, file_storage_key, idempotency_key) "
    "VALUES (:i, :t, :s, 'USD', :u, 'UPLOAD', 'a.pdf', 'application/pdf', 1, repeat('a', 64), :k, :k)"
)


async def test_pending_review_goes_to_posting_and_the_downgrade_refuses_posted_invoices(
    database_url: str,
) -> None:
    name = f"migration_{uuid.uuid4().hex[:8]}"
    admin = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = make_url(database_url).set(database=name).render_as_string(hide_password=False)
    engine = create_async_engine(url)
    tenant, user = uuid.uuid4(), uuid.uuid4()
    review, completed, approval = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    try:
        assert alembic(url, "upgrade", "0012").returncode == 0
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO tenant (id, name, code, is_active) VALUES (:t, 'Before', 'before', true)"),
                {"t": tenant},
            )
            await conn.execute(
                text(
                    "INSERT INTO user_account (id, tenant_id, username, display_name, role, is_active) "
                    "VALUES (:u, :t, 'm@before.example.com', 'M', 'ACCOUNTING_MEMBER', true)"
                ),
                {"u": user, "t": tenant},
            )
            for invoice, status in (
                (review, "PENDING_REVIEW"),
                (completed, "COMPLETED"),
                (approval, "PENDING_APPROVAL"),
            ):
                await conn.execute(
                    text(INVOICE), {"i": invoice, "t": tenant, "u": user, "s": status, "k": str(invoice)}
                )
        up = alembic(url, "upgrade", "0013")
        assert up.returncode == 0, up.stderr

        async with engine.connect() as conn:
            statuses = dict(
                (
                    await conn.execute(
                        text("SELECT id, status FROM invoice WHERE tenant_id = :t"), {"t": tenant}
                    )
                ).all()
            )
            events = (
                await conn.execute(
                    text(
                        "SELECT invoice_id, status_from, status_to, actor FROM invoice_event "
                        "WHERE action = 'UPGRADE_TO_POSTING'"
                    )
                )
            ).all()
            columns = (
                await conn.execute(
                    text("SELECT erp_document_number, posted_at, posting_held_at FROM invoice WHERE id = :i"),
                    {"i": review},
                )
            ).one()
        assert statuses == {review: "POSTING", completed: "COMPLETED", approval: "PENDING_APPROVAL"}
        assert [tuple(row) for row in events] == [(review, "PENDING_REVIEW", "POSTING", "system")]
        assert tuple(columns) == (None, None, None)

        refused = alembic(url, "downgrade", "0012")
        assert refused.returncode != 0 and "Posting or Posted" in refused.stderr
        async with engine.begin() as conn:
            await conn.execute(text("UPDATE invoice SET status = 'REJECTED' WHERE status = 'POSTING'"))
        assert alembic(url, "downgrade", "0012").returncode == 0
        assert alembic(url, "upgrade", "0013").returncode == 0
    finally:
        await engine.dispose()
        async with admin.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await admin.dispose()
