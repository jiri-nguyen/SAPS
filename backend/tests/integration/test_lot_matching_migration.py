"""Migration 0012 on a database of its own (SAPS-51 §3.6, §4): old lines survive, the downgrade guard."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration.conftest import alembic

pytestmark = pytest.mark.integration


async def test_old_lines_keep_their_data_and_the_downgrade_refuses_new_exceptions(database_url: str) -> None:
    name = f"migration_{uuid.uuid4().hex[:8]}"
    admin = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = make_url(database_url).set(database=name).render_as_string(hide_password=False)
    engine = create_async_engine(url)
    tenant, user, invoice, line = (uuid.uuid4() for _ in range(4))
    try:
        assert alembic(url, "upgrade", "0011").returncode == 0
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
            await conn.execute(
                text(
                    "INSERT INTO invoice (id, tenant_id, status, currency, uploaded_by, channel, file_name, "
                    "file_content_type, file_size_bytes, file_sha256, file_storage_key, idempotency_key) "
                    "VALUES (:i, :t, 'COMPLETED', 'USD', :u, 'UPLOAD', 'a.pdf', 'application/pdf', 1, "
                    "repeat('a', 64), 'k', 'i')"
                ),
                {"i": invoice, "t": tenant, "u": user},
            )
            await conn.execute(
                text(
                    "INSERT INTO invoice_line (id, tenant_id, invoice_id, line_number, po_number, "
                    "po_line_number, quantity) VALUES (:l, :t, :i, 1, '0100001', 1, 4)"
                ),
                {"l": line, "t": tenant, "i": invoice},
            )
        up = alembic(url, "upgrade", "0012")
        assert up.returncode == 0, up.stderr

        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT quantity, do_number, matched_do_number, pir_unit_price "
                        "FROM invoice_line WHERE id = :l"
                    ),
                    {"l": line},
                )
            ).one()
        assert (row.quantity, row.do_number, row.matched_do_number, row.pir_unit_price) == (
            4,
            None,
            None,
            None,
        )

        async with engine.begin() as conn:  # an EX13 blocks the downgrade
            await conn.execute(
                text(
                    "INSERT INTO invoice_exception (id, tenant_id, invoice_id, code, message, status) "
                    "VALUES (gen_random_uuid(), :t, :i, 'EX13', 'Invalid DO number', 'OPEN')"
                ),
                {"t": tenant, "i": invoice},
            )
        refused = alembic(url, "downgrade", "0011")
        assert refused.returncode != 0 and "EX11 to EX13" in refused.stderr
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM invoice_exception"))
        assert alembic(url, "downgrade", "0011").returncode == 0
        assert alembic(url, "upgrade", "0012").returncode == 0
    finally:
        await engine.dispose()
        async with admin.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await admin.dispose()
