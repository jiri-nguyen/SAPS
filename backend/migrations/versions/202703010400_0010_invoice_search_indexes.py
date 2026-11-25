"""Indexes for the invoice list and search (SAPS-46).

The default order (newest upload first) and the range filters read `invoice` by company; the PO number filter uses the
existing index of `invoice_line`.

Revision ID: 0010
Revises: 0009
Create Date: 2027-03-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_invoice_tenant_created", "invoice", ["tenant_id", "created_at", "id"])
    op.create_index("ix_invoice_tenant_invoice_date", "invoice", ["tenant_id", "invoice_date"])
    op.create_index("ix_invoice_tenant_total_amount", "invoice", ["tenant_id", "total_amount"])


def downgrade() -> None:
    op.drop_index("ix_invoice_tenant_total_amount", table_name="invoice")
    op.drop_index("ix_invoice_tenant_invoice_date", table_name="invoice")
    op.drop_index("ix_invoice_tenant_created", table_name="invoice")
