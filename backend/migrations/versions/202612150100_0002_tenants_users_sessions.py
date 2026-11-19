"""Tenants, users, sessions and matching settings (SAPS-27, ADR-0007, ADR-0008).

Revision ID: 0002
Revises: 0001
Create Date: 2026-12-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _audit() -> list[sa.Column[object]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(100), server_default="system", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.String(100), server_default="system", nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        *_audit(),
    )
    op.create_table(
        "user_account",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ACCOUNTING_MEMBER", "ACCOUNTING_MANAGER", name="role", native_enum=False, length=30),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        *_audit(),
    )
    op.create_index("ix_user_account_tenant_id", "user_account", ["tenant_id"])
    op.create_table(
        "user_session",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("user_account_id", sa.Uuid(), sa.ForeignKey("user_account.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
    )
    op.create_index("ix_user_session_tenant_id", "user_session", ["tenant_id"])
    op.create_index("ix_user_session_user_account_id", "user_session", ["user_account_id"])
    op.create_table(
        "matching_settings",
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), primary_key=True),
        sa.Column("price_tolerance_usd", sa.Numeric(18, 4), server_default="0.5", nullable=False),
        sa.Column("approval_threshold_usd", sa.Numeric(18, 2), server_default="300", nullable=False),
        *_audit(),
    )


def downgrade() -> None:
    op.drop_table("matching_settings")
    op.drop_index("ix_user_session_user_account_id", table_name="user_session")
    op.drop_index("ix_user_session_tenant_id", table_name="user_session")
    op.drop_table("user_session")
    op.drop_index("ix_user_account_tenant_id", table_name="user_account")
    op.drop_table("user_account")
    op.drop_table("tenant")
