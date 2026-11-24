"""Invoice intake from company mailboxes (SAPS-45): `inbound_mail`, the intake channel on invoices.

Invoices received by mail have no uploading user: `uploaded_by` becomes optional, `channel` tells how the invoice came
(existing rows are uploads) and a check ties each channel to its data. `inbound_mail` is tenant-owned: row-level
security like every other tenant table (SAPS-41).

Revision ID: 0009
Revises: 0008
Create Date: 2027-03-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENT_TENANT = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
ROLES = ("saps_app", "saps_system")


def upgrade() -> None:
    op.create_table(
        "inbound_mail",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("mailbox_address", sa.String(320), nullable=False),
        sa.Column("mail_key", sa.String(500), nullable=False),
        sa.Column("sender", sa.String(320), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="RECEIVED"),
        sa.Column("skip_reason", sa.String(50), nullable=True),
        sa.Column("attachments", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(100), server_default="system", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.String(100), server_default="system", nullable=False),
        sa.UniqueConstraint("tenant_id", "mail_key", name="uq_inbound_mail_tenant_id_mail_key"),
    )
    op.create_index("ix_inbound_mail_tenant_id", "inbound_mail", ["tenant_id"])
    op.create_index("ix_inbound_mail_status", "inbound_mail", ["status"])
    for role in ROLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON inbound_mail TO {role}")
    op.execute("ALTER TABLE inbound_mail ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE inbound_mail FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON inbound_mail "
        f"USING (tenant_id = {CURRENT_TENANT}) WITH CHECK (tenant_id = {CURRENT_TENANT})"
    )

    op.add_column("invoice", sa.Column("channel", sa.String(30), nullable=False, server_default="UPLOAD"))
    op.add_column("invoice", sa.Column("inbound_mail_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_invoice_inbound_mail_id", "invoice", "inbound_mail", ["inbound_mail_id"], ["id"]
    )
    op.alter_column("invoice", "uploaded_by", nullable=True)
    op.create_check_constraint(
        "ck_invoice_channel_source",
        "invoice",
        "(channel = 'UPLOAD' AND uploaded_by IS NOT NULL) OR (channel = 'MAIL' AND inbound_mail_id IS NOT NULL)",
    )


def downgrade() -> None:
    bind = op.get_bind()
    mail_invoices = bind.execute(sa.text("SELECT count(*) FROM invoice WHERE channel = 'MAIL'")).scalar_one()
    if mail_invoices:
        raise RuntimeError(
            f"{mail_invoices} invoices were received by mail; uploaded_by would be required again"
        )
    op.drop_constraint("ck_invoice_channel_source", "invoice", type_="check")
    op.alter_column("invoice", "uploaded_by", nullable=False)
    op.drop_constraint("fk_invoice_inbound_mail_id", "invoice", type_="foreignkey")
    op.drop_column("invoice", "inbound_mail_id")
    op.drop_column("invoice", "channel")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON inbound_mail")
    op.drop_table("inbound_mail")
