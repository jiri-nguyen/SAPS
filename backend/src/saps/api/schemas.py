"""API schemas; JSON properties are camelCase (OpenAPI contract conventions)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
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
from saps.ports.invoices import InvoiceEventView, InvoiceSummaryView, InvoiceView


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


class InvoiceSummary(_ReadModel):
    """OpenAPI `InvoiceSummary` (queue rows)."""

    id: UUID
    status: InvoiceStatus
    invoice_type: InvoiceType | None
    vendor_name: str | None
    invoice_number: str | None
    total_amount: Decimal | None
    currency: str
    open_exception_codes: list[ExceptionCode]
    assigned_to: UserAccountRef | None
    updated_at: datetime

    @classmethod
    def from_view(cls, view: InvoiceSummaryView) -> InvoiceSummary:
        return cls.model_validate(view)


class InvoiceSummaryPage(CamelModel):
    items: list[InvoiceSummary]
    next_page_token: str | None


class InvoiceEvent(_ReadModel):
    id: UUID
    status_from: InvoiceStatus | None
    status_to: InvoiceStatus
    action: str
    actor: str
    details: dict[str, Any] | None
    occurred_at: datetime

    @classmethod
    def from_view(cls, view: InvoiceEventView) -> InvoiceEvent:
        return cls.model_validate(view)


class InvoiceEventPage(CamelModel):
    items: list[InvoiceEvent]
    next_page_token: str | None


# --- requests of exception handling (SAPS-20) ----------------------------------------------------------

PoNumberText = Annotated[str, Field(pattern=r"^[0-9]{7}$")]
Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2)]
UnitPrice = Annotated[Decimal, Field(max_digits=18, decimal_places=4)]
Quantity = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=3)]


class InvoiceLineUpdate(CamelModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    line_number: int = Field(ge=1)
    description: str | None = Field(default=None, max_length=500)
    po_number: PoNumberText | None = None
    po_line_number: int | None = Field(default=None, ge=1)
    quantity: Quantity | None = None
    unit_price: UnitPrice | None = None
    line_amount: Money | None = None


class InvoiceUpdate(CamelModel):
    """Corrections: fields not sent stay unchanged; `lines`, when sent, replaces all lines (SAPS-20 BR-04)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    vendor_code: Annotated[str, Field(min_length=1, max_length=20)] | None = None
    vendor_name: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    invoice_number: Annotated[str, Field(min_length=1, max_length=50)] | None = None
    invoice_date: date | None = None
    subtotal_amount: Money | None = None
    tax_amount: Money | None = None
    total_amount: Money | None = None
    lines: list[InvoiceLineUpdate] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _not_empty_and_not_null(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Send at least one field to change.")
        nulls = [name for name in self.model_fields_set if getattr(self, name) is None]
        if nulls:
            raise ValueError(f"These fields cannot be null: {', '.join(sorted(nulls))}.")
        return self

    def header(self) -> dict[str, Any]:
        """Only the header fields that were sent."""
        return {name: getattr(self, name) for name in self.model_fields_set if name != "lines"}


class RejectionCreate(CamelModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
