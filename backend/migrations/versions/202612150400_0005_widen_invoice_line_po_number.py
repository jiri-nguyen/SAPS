"""Widen invoice_line.po_number to 20 characters (SAPS-36 follow-up).

The PO number is stored as on the invoice, so matching can raise EX3 for invalid values
(API `InvoiceLine.poNumber` maxLength 20; SAPS-19 BR-02).

Revision ID: 0005
Revises: 0004
Create Date: 2026-12-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "invoice_line", "po_number", type_=sa.String(20), existing_type=sa.String(7), existing_nullable=True
    )


def downgrade() -> None:
    # Values longer than 7 characters would not fit; the PoC holds demo data only.
    op.alter_column(
        "invoice_line",
        "po_number",
        type_=sa.String(7),
        existing_type=sa.String(20),
        existing_nullable=True,
        postgresql_using="left(po_number, 7)",
    )
