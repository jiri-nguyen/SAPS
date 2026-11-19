"""Index for the already invoiced quantity of a PO line (SAPS-19 BR-10, §3.6).

Revision ID: 0004
Revises: 0003
Create Date: 2026-12-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_invoice_line_po_line", "invoice_line", ["tenant_id", "po_number", "po_line_number"])


def downgrade() -> None:
    op.drop_index("ix_invoice_line_po_line", table_name="invoice_line")
