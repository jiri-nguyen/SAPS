"""Trade PO matching per received lot and PIR price (SAPS-51).

Adds the DO number on the invoice line, the received lot of the last matching run and the PIR price seen.

Revision ID: 0012
Revises: 0011
Create Date: 2027-03-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("invoice_line", sa.Column("do_number", sa.String(50), nullable=True))
    op.add_column("invoice_line", sa.Column("matched_do_number", sa.String(50), nullable=True))
    op.add_column("invoice_line", sa.Column("pir_unit_price", sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    blocked = bind.execute(
        sa.text("SELECT count(*) FROM invoice_exception WHERE code IN ('EX11', 'EX12', 'EX13')")
    ).scalar_one()
    if blocked:
        raise RuntimeError(
            f"{blocked} exception(s) EX11 to EX13 exist; the previous version cannot read them. "
            "Resolve or remove them first."
        )
    op.drop_column("invoice_line", "pir_unit_price")
    op.drop_column("invoice_line", "matched_do_number")
    op.drop_column("invoice_line", "do_number")
