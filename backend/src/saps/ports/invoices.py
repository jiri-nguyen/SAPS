"""Invoice persistence ports: upload (SAPS-17) and the invoice read model of `getInvoice`."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from saps.domain.invoices import (
    ApprovalDecision,
    ExceptionCode,
    ExceptionStatus,
    InvoiceStatus,
    InvoiceType,
    MatchStatus,
)
from saps.domain.mail_intake import IntakeChannel


@dataclass(frozen=True)
class UserRef:
    id: UUID
    display_name: str


@dataclass(frozen=True)
class InvoiceFile:
    name: str
    content_type: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class InvoiceLineView:
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


@dataclass(frozen=True)
class InvoiceExceptionView:
    id: UUID
    code: ExceptionCode
    message: str
    status: ExceptionStatus
    invoice_line_id: UUID | None
    resolved_by: UserRef | None
    resolved_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class ApprovalView:
    id: UUID
    decision: ApprovalDecision
    comment: str | None
    decided_by: UserRef
    decided_at: datetime


@dataclass(frozen=True)
class InvoiceSource:
    """How the invoice entered the system (SAPS-45)."""

    channel: IntakeChannel
    mail_from: str | None = None
    mail_subject: str | None = None
    mail_received_at: datetime | None = None


@dataclass(frozen=True)
class InvoiceView:
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
    assigned_to: UserRef | None
    uploaded_by: UserRef | None  # None for an invoice received by mail
    source: InvoiceSource
    file: InvoiceFile
    rejected_reason: str | None
    lines: Sequence[InvoiceLineView]
    exceptions: Sequence[InvoiceExceptionView]
    approval: ApprovalView | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewUpload:
    invoice_id: UUID
    tenant_id: UUID
    uploaded_by: UUID | None
    actor: str
    file: InvoiceFile
    storage_key: str
    idempotency_key: str
    uploaded_at: datetime
    channel: IntakeChannel = IntakeChannel.UPLOAD
    inbound_mail_id: UUID | None = None


@dataclass(frozen=True)
class InvoiceSummaryView:
    id: UUID
    status: InvoiceStatus
    invoice_type: InvoiceType | None
    vendor_name: str | None
    invoice_number: str | None
    total_amount: Decimal | None
    currency: str
    open_exception_codes: Sequence[ExceptionCode]
    assigned_to: UserRef | None
    updated_at: datetime
    invoice_date: date | None
    channel: IntakeChannel
    uploaded_at: datetime  # when the invoice entered the system (SAPS-46)


@dataclass(frozen=True)
class InvoiceEventView:
    id: UUID
    status_from: InvoiceStatus | None
    status_to: InvoiceStatus
    action: str
    actor: str
    details: dict[str, object] | None
    occurred_at: datetime


@dataclass(frozen=True)
class StoredInvoiceFile:
    storage_key: str
    content_type: str
    name: str


@dataclass(frozen=True)
class Page[T]:
    items: Sequence[T]
    next_page_token: str | None


@dataclass(frozen=True)
class InvoiceFilter:
    statuses: Sequence[InvoiceStatus] = ()
    invoice_type: InvoiceType | None = None
    assignee: str | None = None  # "me" or "unassigned"
    user_id: UUID | None = None  # the caller, for assignee "me"
    # The search of SAPS-46: every field optional, combined with AND.
    vendor: str | None = None  # part of the vendor name or code, ignoring case
    invoice_number: str | None = None  # already normalized (DEC-042); part of `invoice_number_normalized`
    po_number: str | None = None  # exact, on any line
    invoice_date_from: date | None = None
    invoice_date_to: date | None = None
    uploaded_from: datetime | None = None  # UTC instant, included
    uploaded_to: datetime | None = None  # UTC instant, excluded
    total_min: Decimal | None = None
    total_max: Decimal | None = None
    channel: IntakeChannel | None = None


class InvalidPageTokenError(ValueError):
    """The page token is not one this API issued (answers 400)."""


class DuplicateIdempotencyKeyError(Exception):
    """Another request with the same key and tenant created its invoice first (SAPS-17 EC-04)."""


class InvoiceRepository(Protocol):
    async def find_by_idempotency_key(self, tenant_id: UUID, key: str) -> UUID | None: ...

    async def add_uploaded(self, upload: NewUpload) -> None:
        """Insert the invoice (Uploaded) and its `UPLOAD` event and commit (BR-05).

        Raises DuplicateIdempotencyKeyError when the key is already used.
        """
        ...


class InvoiceReader(Protocol):
    async def get(self, tenant_id: UUID, invoice_id: UUID) -> InvoiceView | None:
        """The invoice of this tenant with lines, exceptions, approval and user names (ADR-0007)."""
        ...

    async def list_invoices(
        self, tenant_id: UUID, flt: InvoiceFilter, page_size: int, page_token: str | None
    ) -> Page[InvoiceSummaryView]:
        """Newest first; the token is opaque (keyset paging)."""
        ...

    async def list_events(
        self, tenant_id: UUID, invoice_id: UUID, page_size: int, page_token: str | None
    ) -> Page[InvoiceEventView] | None:
        """Oldest first; None when the invoice does not exist in the tenant."""
        ...

    async def file_of(self, tenant_id: UUID, invoice_id: UUID) -> StoredInvoiceFile | None: ...

    async def company_time_zone(self, tenant_id: UUID) -> str:
        """IANA time zone of the company; the upload date filter counts local days (SAPS-46 BR-04)."""
        ...
