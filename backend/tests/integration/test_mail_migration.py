"""Migration 0009 on a database of its own (SAPS-45 §3.6).

Existing invoices become uploads, each channel needs its data, and the downgrade guards mail invoices.
"""

import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from tests.integration.conftest import alembic

pytestmark = pytest.mark.integration

COLUMNS = "id, tenant_id, status, currency, file_name, file_content_type, file_size_bytes, file_sha256"
VALUES = "gen_random_uuid(), :t, 'UPLOADED', 'USD', 'a.pdf', 'application/pdf', 10, :h"


async def _invoice(
    conn: AsyncConnection, tenant: uuid.UUID, extra_columns: str = "", extra: str = "", **p: Any
) -> None:
    sql = f"INSERT INTO invoice ({COLUMNS}, file_storage_key, idempotency_key{extra_columns}) "
    sql += f"VALUES ({VALUES}, 'k', :k{extra})"
    await conn.execute(text(sql), {"t": tenant, "h": "a" * 64, "k": uuid.uuid4().hex, **p})


async def test_existing_invoices_become_uploads_and_the_downgrade_refuses_mail_invoices(
    database_url: str,
) -> None:
    name = f"migration_{uuid.uuid4().hex[:8]}"
    admin = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = make_url(database_url).set(database=name).render_as_string(hide_password=False)
    engine = create_async_engine(url)
    tenant, user = uuid.uuid4(), uuid.uuid4()
    try:
        assert alembic(url, "upgrade", "0008").returncode == 0
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO tenant (id, name, code, is_active) VALUES (:t, 'Before', 'before', true)"),
                {"t": tenant},
            )
            await conn.execute(
                text(
                    "INSERT INTO user_account (id, tenant_id, username, display_name, role, is_active) "
                    "VALUES (:u, :t, 'member@before.example.com', 'M', 'ACCOUNTING_MEMBER', true)"
                ),
                {"u": user, "t": tenant},
            )
            await _invoice(conn, tenant, ", uploaded_by", ", :u", u=user)

        up = alembic(url, "upgrade", "0009")
        assert up.returncode == 0, up.stderr
        async with engine.begin() as conn:
            row = (await conn.execute(text("SELECT channel, inbound_mail_id FROM invoice"))).one()
            assert (row.channel, row.inbound_mail_id) == ("UPLOAD", None)  # existing rows are uploads

        for channel, uploaded_by in (("MAIL", user), ("UPLOAD", None)):  # each channel needs its data
            with pytest.raises(IntegrityError):
                async with engine.begin() as conn:
                    await _invoice(
                        conn, tenant, ", channel, uploaded_by", ", :c, :u", c=channel, u=uploaded_by
                    )

        mail = uuid.uuid4()
        async with engine.begin() as conn:  # a mail invoice blocks the downgrade
            await conn.execute(
                text(
                    "INSERT INTO inbound_mail (id, tenant_id, mailbox_address, mail_key, sender, subject, "
                    "received_at) VALUES (:m, :t, 'ap@before.example.com', '<k>', 's', 's', now())"
                ),
                {"m": mail, "t": tenant},
            )
            await _invoice(conn, tenant, ", channel, inbound_mail_id", ", 'MAIL', :m", m=mail)
        refused = alembic(url, "downgrade", "0008")
        assert refused.returncode != 0 and "received by mail" in refused.stderr
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM invoice WHERE channel = 'MAIL'"))
        ok = alembic(url, "downgrade", "0008")
        assert ok.returncode == 0, ok.stderr
    finally:
        await engine.dispose()
        async with admin.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await admin.dispose()
