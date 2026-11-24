"""ORM models (docs/02-architecture/data-model.md). Each tenant-owned table carries tenant_id (ADR-0007)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from saps.adapters.persistence.db import Base
from saps.domain.invoices import (
    ApprovalDecision,
    ExceptionCode,
    ExceptionStatus,
    InvoiceStatus,
    InvoiceType,
    MatchStatus,
    NotificationType,
)
from saps.domain.users import Role


def _enum[E: StrEnum](enum: type[E], name: str) -> Enum:
    """Enums are stored as strings (no native PostgreSQL type), so adding a value needs no type migration."""
    return Enum(enum, native_enum=False, length=30, name=name)


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
    # Company details (SAPS-42): the code selects the ERP data; the others serve SSO, mailbox intake and
    # the processing calendar.
    code: Mapped[str] = mapped_column(String(20), unique=True)
    email_domain: Mapped[str | None] = mapped_column(String(255), unique=True)
    keycloak_group: Mapped[str | None] = mapped_column(String(255), unique=True)
    mailbox_address: Mapped[str | None] = mapped_column(String(320), unique=True)
    time_zone: Mapped[str] = mapped_column(String(64), server_default="UTC")


class UserAccount(AuditMixin, Base):
    __tablename__ = "user_account"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role, "role"))
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


class Invoice(AuditMixin, Base):
    """An uploaded vendor invoice and its processing state (data model §4.1)."""

    __tablename__ = "invoice"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_invoice_tenant_id_idempotency_key"),
        Index("ix_invoice_duplicate_check", "tenant_id", "vendor_code", "invoice_number_normalized"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    status: Mapped[InvoiceStatus] = mapped_column(_enum(InvoiceStatus, "invoice_status"))
    invoice_type: Mapped[InvoiceType | None] = mapped_column(_enum(InvoiceType, "invoice_type"))
    vendor_code: Mapped[str | None] = mapped_column(String(20))
    vendor_name: Mapped[str | None] = mapped_column(String(200))
    invoice_number: Mapped[str | None] = mapped_column(String(50))
    invoice_number_normalized: Mapped[str | None] = mapped_column(String(50))
    invoice_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD")
    subtotal_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    price_tolerance_applied: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    approval_threshold_applied: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    requires_approval: Mapped[bool | None] = mapped_column(Boolean)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user_account.id"))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    file_content_type: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    file_sha256: Mapped[str] = mapped_column(String(64))
    file_storage_key: Mapped[str] = mapped_column(String(500))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    rejected_reason: Mapped[str | None] = mapped_column(String(1000))

    lines: Mapped[list[InvoiceLine]] = relationship(
        back_populates="invoice", lazy="raise", order_by="InvoiceLine.line_number"
    )
    exceptions: Mapped[list[InvoiceException]] = relationship(back_populates="invoice", lazy="raise")


class InvoiceLine(AuditMixin, Base):
    """One line of an invoice and its matching result."""

    __tablename__ = "invoice_line"
    __table_args__ = (
        UniqueConstraint("invoice_id", "line_number", name="uq_invoice_line_invoice_id_line_number"),
        Index("ix_invoice_line_po_line", "tenant_id", "po_number", "po_line_number"),  # SAPS-19 BR-10
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoice.id"))
    line_number: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(String(500))
    po_number: Mapped[str | None] = mapped_column(
        String(20)
    )  # as on the invoice; matching validates it (EX3)
    po_line_number: Mapped[int | None] = mapped_column(Integer)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    line_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    match_status: Mapped[MatchStatus] = mapped_column(
        _enum(MatchStatus, "match_status"), server_default=MatchStatus.NOT_MATCHED.value
    )
    po_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    expected_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))

    invoice: Mapped[Invoice] = relationship(back_populates="lines", lazy="raise")


class InvoiceException(AuditMixin, Base):
    """An exception raised for an invoice; at most one open per code and line (data model §4.1)."""

    __tablename__ = "invoice_exception"
    __table_args__ = (
        Index(
            "uq_invoice_exception_open",
            "invoice_id",
            "code",
            "invoice_line_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
            postgresql_nulls_not_distinct=True,  # header-level exceptions have no line
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoice.id"), index=True)
    invoice_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoice_line.id"))
    code: Mapped[ExceptionCode] = mapped_column(_enum(ExceptionCode, "exception_code"))
    message: Mapped[str] = mapped_column(String(1000))
    status: Mapped[ExceptionStatus] = mapped_column(
        _enum(ExceptionStatus, "exception_status"), server_default=ExceptionStatus.OPEN.value
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user_account.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    invoice: Mapped[Invoice] = relationship(back_populates="exceptions", lazy="raise")


class Approval(AuditMixin, Base):
    """The Accounting Manager's decision on an invoice above the approval threshold (insert only)."""

    __tablename__ = "approval"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoice.id"), index=True)
    decided_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"))
    decision: Mapped[ApprovalDecision] = mapped_column(_enum(ApprovalDecision, "approval_decision"))
    comment: Mapped[str | None] = mapped_column(String(1000))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InvoiceEvent(AuditMixin, Base):
    """Audit trail of status changes and user actions on an invoice (insert only)."""

    __tablename__ = "invoice_event"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoice.id"), index=True)
    status_from: Mapped[InvoiceStatus | None] = mapped_column(_enum(InvoiceStatus, "invoice_status"))
    status_to: Mapped[InvoiceStatus] = mapped_column(_enum(InvoiceStatus, "invoice_status"))
    action: Mapped[str] = mapped_column(String(50))
    actor: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(AuditMixin, Base):
    """An in-app notification for one user (DEC-021); one row per recipient."""

    __tablename__ = "notification"
    __table_args__ = (Index("ix_notification_recipient_unread", "recipient_id", "read_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"))
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoice.id"), index=True)
    type: Mapped[NotificationType] = mapped_column(_enum(NotificationType, "notification_type"))
    message: Mapped[str] = mapped_column(String(500))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
