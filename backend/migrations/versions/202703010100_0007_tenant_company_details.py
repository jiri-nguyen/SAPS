"""Company details on the tenant (SAPS-42): code, e-mail domain, Keycloak group, mailbox, time zone.

Existing rows get a code `tenant-<first 8 characters of the id>`; the seed turns the PoC company into Demo Vietnam.

Revision ID: 0007
Revises: 0006
Create Date: 2027-03-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenant", sa.Column("code", sa.String(20), nullable=True))
    op.execute("UPDATE tenant SET code = 'tenant-' || left(id::text, 8) WHERE code IS NULL")
    op.alter_column("tenant", "code", nullable=False)
    op.create_unique_constraint("uq_tenant_code", "tenant", ["code"])
    for name, length in (("email_domain", 255), ("keycloak_group", 255), ("mailbox_address", 320)):
        op.add_column("tenant", sa.Column(name, sa.String(length), nullable=True))
        op.create_unique_constraint(f"uq_tenant_{name}", "tenant", [name])
    op.add_column("tenant", sa.Column("time_zone", sa.String(64), nullable=False, server_default="UTC"))


def downgrade() -> None:
    op.drop_column("tenant", "time_zone")
    for name in ("mailbox_address", "keycloak_group", "email_domain", "code"):
        op.drop_constraint(f"uq_tenant_{name}", "tenant", type_="unique")
        op.drop_column("tenant", name)
