"""Processing calendar per company (SAPS-52): rules, the status On hold, the release marker.

`inbound_mail` style row-level security on the new table (SAPS-41). The downgrade refuses to run while invoices are
On hold, because the old lifecycle has no such status.

Revision ID: 0011
Revises: 0010
Create Date: 2027-03-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENT_TENANT = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
ROLES = ("saps_app", "saps_system")


def upgrade() -> None:
    op.create_table(
        "processing_calendar_rule",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("from_day", sa.Integer(), nullable=True),
        sa.Column("to_day", sa.Integer(), nullable=True),
        sa.Column("weekday", sa.Integer(), nullable=True),
        sa.Column("day", sa.Date(), nullable=True),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(100), server_default="system", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.String(100), server_default="system", nullable=False),
        sa.CheckConstraint(
            # NULL passes a CHECK, so every needed column is also tested with IS NOT NULL.
            "(kind = 'MONTHLY_RANGE' AND from_day IS NOT NULL AND from_day BETWEEN 1 AND 31 "
            "AND to_day IS NOT NULL AND to_day BETWEEN 1 AND 31 AND weekday IS NULL AND day IS NULL) "
            "OR (kind = 'WEEKDAY' AND weekday IS NOT NULL AND weekday BETWEEN 1 AND 7 "
            "AND from_day IS NULL AND to_day IS NULL AND day IS NULL) "
            "OR (kind = 'DATE' AND day IS NOT NULL AND from_day IS NULL AND to_day IS NULL AND weekday IS NULL)",
            name="ck_processing_calendar_rule_kind",
        ),
    )
    op.create_index("ix_processing_calendar_rule_tenant_id", "processing_calendar_rule", ["tenant_id"])
    for role in ROLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON processing_calendar_rule TO {role}")
    op.execute("ALTER TABLE processing_calendar_rule ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE processing_calendar_rule FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON processing_calendar_rule "
        f"USING (tenant_id = {CURRENT_TENANT}) WITH CHECK (tenant_id = {CURRENT_TENANT})"
    )

    op.add_column("invoice", sa.Column("released_from_hold_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_invoice_tenant_status_created", "invoice", ["tenant_id", "status", "created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    held = bind.execute(sa.text("SELECT count(*) FROM invoice WHERE status = 'ON_HOLD'")).scalar_one()
    if held:
        raise RuntimeError(f"{held} invoices are on hold; release them before the downgrade")
    op.drop_index("ix_invoice_tenant_status_created", table_name="invoice")
    op.drop_column("invoice", "released_from_hold_at")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON processing_calendar_rule")
    op.drop_table("processing_calendar_rule")
