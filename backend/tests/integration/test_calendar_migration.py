"""Migration 0011 on a database of its own (SAPS-52 §3.6): the rule checks and the downgrade guard."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql.elements import TextClause

from tests.integration.conftest import alembic

pytestmark = pytest.mark.integration

RULE = (
    "INSERT INTO processing_calendar_rule (id, tenant_id, position, kind, {columns}) "
    "VALUES (gen_random_uuid(), :t, 0, :k, {values})"
)


def _rule(columns: str, values: str) -> TextClause:
    return text(RULE.format(columns=columns, values=values))


async def test_the_rules_are_checked_and_the_downgrade_refuses_held_invoices(database_url: str) -> None:
    name = f"migration_{uuid.uuid4().hex[:8]}"
    admin = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = make_url(database_url).set(database=name).render_as_string(hide_password=False)
    engine = create_async_engine(url)
    tenant = uuid.uuid4()
    try:
        assert alembic(url, "upgrade", "0010").returncode == 0
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO tenant (id, name, code, is_active) VALUES (:t, 'Before', 'before', true)"),
                {"t": tenant},
            )
        up = alembic(url, "upgrade", "0011")
        assert up.returncode == 0, up.stderr

        valid = [
            ("MONTHLY_RANGE", "from_day, to_day", "25, 5"),
            ("WEEKDAY", "weekday", "6"),
            ("DATE", "day", "'2027-04-30'"),
        ]
        async with engine.begin() as conn:
            for kind, columns, values in valid:
                await conn.execute(
                    text(RULE.format(columns=columns, values=values)), {"t": tenant, "k": kind}
                )
        invalid = [
            ("MONTHLY_RANGE", "from_day, to_day", "0, 5"),
            ("MONTHLY_RANGE", "from_day", "25"),
            ("WEEKDAY", "weekday", "8"),
            ("WEEKDAY", "from_day", "1"),
            ("DATE", "weekday", "1"),
        ]
        for kind, columns, values in invalid:
            with pytest.raises(IntegrityError):
                async with engine.begin() as conn:
                    await conn.execute(
                        text(RULE.format(columns=columns, values=values)), {"t": tenant, "k": kind}
                    )

        user = uuid.uuid4()
        async with engine.begin() as conn:  # an invoice On hold blocks the downgrade
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
                    "VALUES (gen_random_uuid(), :t, 'ON_HOLD', 'USD', :u, 'UPLOAD', 'a.pdf', "
                    "'application/pdf', 1, repeat('a', 64), 'k', 'i')"
                ),
                {"t": tenant, "u": user},
            )
        refused = alembic(url, "downgrade", "0010")
        assert refused.returncode != 0 and "on hold" in refused.stderr
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM invoice"))
        assert alembic(url, "downgrade", "0010").returncode == 0
        assert alembic(url, "upgrade", "0011").returncode == 0
    finally:
        await engine.dispose()
        async with admin.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await admin.dispose()
