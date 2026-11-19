"""ORM models (docs/02-architecture/data-model.md). Each tenant-owned table carries tenant_id (ADR-0007)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from saps.adapters.persistence.db import Base
from saps.domain.users import Role


class AuditMixin:
    """Audit columns of every table (data model §4.1)."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(100), server_default="system")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str] = mapped_column(String(100), server_default="system")


class Tenant(AuditMixin, Base):
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")


class UserAccount(AuditMixin, Base):
    __tablename__ = "user_account"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=30, name="role"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")

    tenant: Mapped[Tenant] = relationship(lazy="raise")


class UserSession(AuditMixin, Base):
    __tablename__ = "user_session"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    user_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserAccount] = relationship(lazy="raise")


class MatchingSettings(AuditMixin, Base):
    """One row per tenant (DEC-015); defaults 0.5 USD and 300 USD."""

    __tablename__ = "matching_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), primary_key=True)
    price_tolerance_usd: Mapped[Decimal] = mapped_column(Numeric(18, 4), server_default="0.5")
    approval_threshold_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), server_default="300")
