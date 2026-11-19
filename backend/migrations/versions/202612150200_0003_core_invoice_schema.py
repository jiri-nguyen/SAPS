"""Core invoice schema: invoice, invoice_line, invoice_exception, approval, invoice_event, notification.

Tables, columns and indexes as in docs/02-architecture/data-model.md §4.1 (SAPS-36, ADR-0005, ADR-0007).

Revision ID: 0003
Revises: 0002
Create Date: 2026-12-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoice",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "UPLOADED",
                "MATCHING",
                "EXCEPTION",
                "PENDING_APPROVAL",
                "PENDING_REVIEW",
                "COMPLETED",
                "REJECTED",
                name="invoice_status",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column(
            "invoice_type",
            sa.Enum("TRADE_PO", "NON_TRADE_PO", "NON_PO", name="invoice_type", native_enum=False, length=30),
            nullable=True,
        ),
        sa.Column("vendor_code", sa.String(length=20), nullable=True),
        sa.Column("vendor_name", sa.String(length=200), nullable=True),
        sa.Column("invoice_number", sa.String(length=50), nullable=True),
        sa.Column("invoice_number_normalized", sa.String(length=50), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("subtotal_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("tax_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("price_tolerance_applied", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("approval_threshold_applied", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=True),
        sa.Column("assigned_to", sa.Uuid(), nullable=True),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_storage_key", sa.String(length=500), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("rejected_reason", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=100), server_default="system", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(length=100), server_default="system", nullable=False),
        sa.ForeignKeyConstraint(
            ["assigned_to"],
            ["user_account.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["user_account.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_invoice_tenant_id_idempotency_key"),
    )
    op.create_index(
        "ix_invoice_duplicate_check",
        "invoice",
        ["tenant_id", "vendor_code", "invoice_number_normalized"],
        unique=False,
    )
    op.create_index(op.f("ix_invoice_tenant_id"), "invoice", ["tenant_id"], unique=False)
    op.create_table(
        "approval",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=False),
        sa.Column(
            "decision",
            sa.Enum("APPROVED", "REJECTED", name="approval_decision", native_enum=False, length=30),
            nullable=False,
        ),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=100), server_default="system", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(length=100), server_default="system", nullable=False),
        sa.ForeignKeyConstraint(
            ["decided_by"],
            ["user_account.id"],
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoice.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_approval_invoice_id"), "approval", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_approval_tenant_id"), "approval", ["tenant_id"], unique=False)
    op.create_table(
        "invoice_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status_from",
            sa.Enum(
                "UPLOADED",
                "MATCHING",
                "EXCEPTION",
                "PENDING_APPROVAL",
                "PENDING_REVIEW",
                "COMPLETED",
                "REJECTED",
                name="invoice_status",
                native_enum=False,
                length=30,
            ),
            nullable=True,
        ),
        sa.Column(
            "status_to",
            sa.Enum(
                "UPLOADED",
                "MATCHING",
                "EXCEPTION",
                "PENDING_APPROVAL",
                "PENDING_REVIEW",
                "COMPLETED",
                "REJECTED",
                name="invoice_status",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=100), server_default="system", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(length=100), server_default="system", nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoice.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_event_invoice_id"), "invoice_event", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_invoice_event_tenant_id"), "invoice_event", ["tenant_id"], unique=False)
    op.create_table(
        "invoice_line",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("po_number", sa.String(length=7), nullable=True),
        sa.Column("po_line_number", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("line_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column(
            "match_status",
            sa.Enum(
                "NOT_MATCHED",
                "MATCHED",
                "MISMATCH",
                "NOT_APPLICABLE",
                name="match_status",
                native_enum=False,
                length=30,
            ),
            server_default="NOT_MATCHED",
            nullable=False,
        ),
        sa.Column("po_unit_price", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("expected_quantity", sa.Numeric(precision=18, scale=3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=100), server_default="system", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(length=100), server_default="system", nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoice.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id", "line_number", name="uq_invoice_line_invoice_id_line_number"),
    )
    op.create_index(op.f("ix_invoice_line_tenant_id"), "invoice_line", ["tenant_id"], unique=False)
    op.create_table(
        "notification",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "EXCEPTION_RAISED",
                "APPROVAL_REQUESTED",
                "REVIEW_REQUESTED",
                name="notification_type",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=100), server_default="system", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(length=100), server_default="system", nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoice.id"],
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["user_account.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_invoice_id"), "notification", ["invoice_id"], unique=False)
    op.create_index(
        "ix_notification_recipient_unread",
        "notification",
        ["recipient_id", "read_at", "created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_notification_tenant_id"), "notification", ["tenant_id"], unique=False)
    op.create_table(
        "invoice_exception",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_line_id", sa.Uuid(), nullable=True),
        sa.Column(
            "code",
            sa.Enum(
                "EX1",
                "EX2",
                "EX3",
                "EX4",
                "EX5",
                "EX6",
                "EX7",
                "EX8",
                "EX9",
                "EX10",
                name="exception_code",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column(
            "status",
            sa.Enum("OPEN", "RESOLVED", name="exception_status", native_enum=False, length=30),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=100), server_default="system", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(length=100), server_default="system", nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoice.id"],
        ),
        sa.ForeignKeyConstraint(
            ["invoice_line_id"],
            ["invoice_line.id"],
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["user_account.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_invoice_exception_invoice_id"), "invoice_exception", ["invoice_id"], unique=False
    )
    op.create_index(op.f("ix_invoice_exception_tenant_id"), "invoice_exception", ["tenant_id"], unique=False)
    op.create_index(
        "uq_invoice_exception_open",
        "invoice_exception",
        ["invoice_id", "code", "invoice_line_id"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    # Dropping a table also drops its indexes; children before parents.
    for table in (
        "invoice_exception",
        "notification",
        "invoice_line",
        "invoice_event",
        "approval",
        "invoice",
    ):
        op.drop_table(table)
