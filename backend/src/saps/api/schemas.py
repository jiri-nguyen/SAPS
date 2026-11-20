"""API schemas; JSON properties are camelCase (OpenAPI contract conventions)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from saps.domain.invoices import (
    ApprovalDecision,
    ExceptionCode,
    ExceptionStatus,
    InvoiceStatus,
    InvoiceType,
    MatchStatus,
)
from saps.domain.users import CurrentUser, Role
from saps.ports.invoices import InvoiceView


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SessionCreate(CamelModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class UserAccount(CamelModel):
    id: UUID
    username: str
    display_name: str
    role: Role

    @classmethod
    def from_user(cls, user: CurrentUser) -> UserAccount:
        return cls(id=user.user_id, username=user.username, display_name=user.display_name, role=user.role)


class _ReadModel(CamelModel):
    """Built from the read model dataclasses of `saps.ports.invoices`; decimals are JSON strings."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class UserAccountRef(_ReadModel):
    id: UUID
    display_name: str


class InvoiceFile(_ReadModel):
    name: str
    content_type: str
    size_bytes: int
    sha256: str


class InvoiceLine(_ReadModel):
    id: UUID
    line_number: int
    description: str | None
    po_number: str | None
    po_line_number: int | None
    quantity: Decimal | None
    unit_price: Decimal | None
    line_amount: Decimal | None
    match_status: MatchStatus
    po_unit_price: Decimal | None
    expected_quantity: Decimal | None


class InvoiceException(_ReadModel):
    id: UUID
    code: ExceptionCode
    message: str
    status: ExceptionStatus
    invoice_line_id: UUID | None
    resolved_by: UserAccountRef | None
    resolved_at: datetime | None
    created_at: datetime


class Approval(_ReadModel):
    id: UUID
    decision: ApprovalDecision
    comment: str | None
    decided_by: UserAccountRef
    decided_at: datetime


class Invoice(_ReadModel):
    """OpenAPI `Invoice`."""

    id: UUID
    status: InvoiceStatus
    invoice_type: InvoiceType | None
    vendor_code: str | None
    vendor_name: str | None
    invoice_number: str | None
    invoice_date: date | None
    currency: str
    subtotal_amount: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None
    requires_approval: bool | None
    price_tolerance_applied: Decimal | None
    approval_threshold_applied: Decimal | None
    assigned_to: UserAccountRef | None
    uploaded_by: UserAccountRef
    file: InvoiceFile
    rejected_reason: str | None
    lines: list[InvoiceLine]
    exceptions: list[InvoiceException]
    approval: Approval | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_view(cls, view: InvoiceView) -> Invoice:
        return cls.model_validate(view)
