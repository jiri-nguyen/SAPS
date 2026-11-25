"""SQL adapters of the invoice ports (SAPS-17). Each call uses its own short transaction."""

import base64
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, or_, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from saps.adapters.persistence.models import (
    Approval,
    InboundMail,
    Invoice,
    InvoiceEvent,
    InvoiceLine,
    Tenant,
    UserAccount,
)
from saps.domain.invoices import ExceptionStatus, InvoiceStatus
from saps.domain.mail_intake import IntakeChannel
from saps.ports.invoices import (
    ApprovalView,
    DuplicateIdempotencyKeyError,
    InvalidPageTokenError,
    InvoiceEventView,
    InvoiceExceptionView,
    InvoiceFile,
    InvoiceFilter,
    InvoiceLineView,
    InvoiceSource,
    InvoiceSummaryView,
    InvoiceView,
    NewUpload,
    Page,
    StoredInvoiceFile,
    UserRef,
)

UPLOAD_ACTION = "UPLOAD"
MAX_PAGE_SIZE = 100


def encode_token(moment: datetime, row_id: UUID) -> str:
    return base64.urlsafe_b64encode(f"{moment.isoformat()}|{row_id}".encode()).decode()


def decode_token(token: str) -> tuple[datetime, UUID]:
    try:
        moment, row_id = base64.urlsafe_b64decode(token.encode()).decode().split("|")
        return datetime.fromisoformat(moment), UUID(row_id)
    except ValueError as exc:  # also covers bad base64, UnicodeDecodeError and wrong part count
        raise InvalidPageTokenError(token) from exc


def _upload_details(upload: NewUpload) -> dict[str, object]:
    details: dict[str, object] = {
        "fileName": upload.file.name,
        "sizeBytes": upload.file.size_bytes,
        "sha256": upload.file.sha256,
    }
    if upload.channel is IntakeChannel.MAIL:  # SAPS-45 §3.5; the event of an upload is unchanged
        details |= {"channel": upload.channel.value, "inboundMailId": str(upload.inbound_mail_id)}
    return details


def _search_filters(query: Select[Any], flt: InvoiceFilter) -> Select[Any]:
    """The filters of SAPS-46, combined with AND.

    A data filter never matches a NULL (EC-05); `autoescape` makes `%` and `_` plain text (EC-10).
    """
    if flt.vendor:
        query = query.where(
            or_(
                Invoice.vendor_name.icontains(flt.vendor, autoescape=True),
                Invoice.vendor_code.icontains(flt.vendor, autoescape=True),
            )
        )
    if flt.invoice_number:
        query = query.where(Invoice.invoice_number_normalized.contains(flt.invoice_number, autoescape=True))
    if flt.po_number:
        has_line = (
            select(InvoiceLine.id)
            .where(
                InvoiceLine.tenant_id == Invoice.tenant_id,  # lets the PO index narrow the lines
                InvoiceLine.invoice_id == Invoice.id,
                InvoiceLine.po_number == flt.po_number,
            )
            .correlate(Invoice)
            .exists()
        )
        query = query.where(has_line)
    if flt.invoice_date_from is not None:
        query = query.where(Invoice.invoice_date >= flt.invoice_date_from)
    if flt.invoice_date_to is not None:
        query = query.where(Invoice.invoice_date <= flt.invoice_date_to)
    if flt.uploaded_from is not None:
        query = query.where(Invoice.created_at >= flt.uploaded_from)
    if flt.uploaded_to is not None:
        query = query.where(Invoice.created_at < flt.uploaded_to)
    if flt.total_min is not None:
        query = query.where(Invoice.total_amount >= flt.total_min)
    if flt.total_max is not None:
        query = query.where(Invoice.total_amount <= flt.total_max)
    if flt.channel is not None:
        query = query.where(Invoice.channel == flt.channel)
    return query


_IDEMPOTENCY_CONSTRAINT = "uq_invoice_tenant_id_idempotency_key"


class SqlInvoiceRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def find_by_idempotency_key(self, tenant_id: UUID, key: str) -> UUID | None:
        async with self._sessions() as session:
            return await session.scalar(
                select(Invoice.id).where(Invoice.tenant_id == tenant_id, Invoice.idempotency_key == key)
            )

    async def add_uploaded(self, upload: NewUpload) -> None:
        try:
            async with self._sessions() as session, session.begin():
                session.add(
                    Invoice(
                        id=upload.invoice_id,
                        tenant_id=upload.tenant_id,
                        status=InvoiceStatus.UPLOADED,
                        uploaded_by=upload.uploaded_by,
                        channel=upload.channel,
                        inbound_mail_id=upload.inbound_mail_id,
                        file_name=upload.file.name,
                        file_content_type=upload.file.content_type,
                        file_size_bytes=upload.file.size_bytes,
                        file_sha256=upload.file.sha256,
                        file_storage_key=upload.storage_key,
                        idempotency_key=upload.idempotency_key,
                        created_by=upload.actor,
                        updated_by=upload.actor,
                    )
                )
                await session.flush()  # no ORM relationship orders the event after the invoice
                session.add(
                    InvoiceEvent(
                        tenant_id=upload.tenant_id,
                        invoice_id=upload.invoice_id,
                        status_from=None,
                        status_to=InvoiceStatus.UPLOADED,
                        action=UPLOAD_ACTION,
                        actor=upload.actor,
                        details=_upload_details(upload),
                        occurred_at=upload.uploaded_at,
                        created_by=upload.actor,
                        updated_by=upload.actor,
                    )
                )
        except IntegrityError as exc:
            if _IDEMPOTENCY_CONSTRAINT in str(exc.orig):
                raise DuplicateIdempotencyKeyError(upload.idempotency_key) from exc
            raise

    async def company_time_zone(self, tenant_id: UUID) -> str:
        async with self._sessions() as session:  # the tenant table has no row-level security
            zone = await session.scalar(select(Tenant.time_zone).where(Tenant.id == tenant_id))
        return zone or "UTC"

    async def get(self, tenant_id: UUID, invoice_id: UUID) -> InvoiceView | None:
        async with self._sessions() as session:
            invoice = await session.scalar(
                select(Invoice)
                .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
                .options(selectinload(Invoice.lines), selectinload(Invoice.exceptions))
            )
            if invoice is None:
                return None
            approval = await session.scalar(
                select(Approval)
                .where(Approval.invoice_id == invoice.id)
                .order_by(Approval.decided_at.desc())
                .limit(1)
            )
            mail = (
                await session.get(InboundMail, invoice.inbound_mail_id) if invoice.inbound_mail_id else None
            )
            user_ids = {invoice.uploaded_by, invoice.assigned_to, approval.decided_by if approval else None}
            user_ids |= {e.resolved_by for e in invoice.exceptions}
            rows = await session.execute(
                select(UserAccount.id, UserAccount.display_name).where(
                    UserAccount.id.in_([i for i in user_ids if i is not None])
                )
            )
            names: dict[UUID, str] = {user_id: name for user_id, name in rows}

        def user(user_id: UUID) -> UserRef:
            return UserRef(user_id, names.get(user_id, ""))

        def ref(user_id: UUID | None) -> UserRef | None:
            return user(user_id) if user_id is not None else None

        return InvoiceView(
            id=invoice.id,
            status=invoice.status,
            invoice_type=invoice.invoice_type,
            vendor_code=invoice.vendor_code,
            vendor_name=invoice.vendor_name,
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date,
            currency=invoice.currency,
            subtotal_amount=invoice.subtotal_amount,
            tax_amount=invoice.tax_amount,
            total_amount=invoice.total_amount,
            requires_approval=invoice.requires_approval,
            price_tolerance_applied=invoice.price_tolerance_applied,
            approval_threshold_applied=invoice.approval_threshold_applied,
            assigned_to=ref(invoice.assigned_to),
            uploaded_by=ref(invoice.uploaded_by),
            source=InvoiceSource(
                channel=invoice.channel,
                mail_from=mail.sender if mail else None,
                mail_subject=mail.subject if mail else None,
                mail_received_at=mail.received_at if mail else None,
            ),
            file=InvoiceFile(
                invoice.file_name, invoice.file_content_type, invoice.file_size_bytes, invoice.file_sha256
            ),
            rejected_reason=invoice.rejected_reason,
            lines=[
                InvoiceLineView(
                    ln.id,
                    ln.line_number,
                    ln.description,
                    ln.po_number,
                    ln.po_line_number,
                    ln.quantity,
                    ln.unit_price,
                    ln.line_amount,
                    ln.match_status,
                    ln.po_unit_price,
                    ln.expected_quantity,
                )
                for ln in invoice.lines
            ],
            exceptions=[
                InvoiceExceptionView(
                    e.id,
                    e.code,
                    e.message,
                    e.status,
                    e.invoice_line_id,
                    ref(e.resolved_by),
                    e.resolved_at,
                    e.created_at,
                )
                for e in sorted(invoice.exceptions, key=lambda e: e.created_at)
            ],
            approval=(
                ApprovalView(
                    approval.id,
                    approval.decision,
                    approval.comment,
                    user(approval.decided_by),
                    approval.decided_at,
                )
                if approval
                else None
            ),
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
        )

    async def list_invoices(
        self, tenant_id: UUID, flt: InvoiceFilter, page_size: int, page_token: str | None
    ) -> Page[InvoiceSummaryView]:
        query = select(Invoice).where(Invoice.tenant_id == tenant_id)
        if flt.statuses:
            query = query.where(Invoice.status.in_(list(flt.statuses)))
        if flt.invoice_type is not None:
            query = query.where(Invoice.invoice_type == flt.invoice_type)
        if flt.assignee == "unassigned":
            query = query.where(Invoice.assigned_to.is_(None))
        elif flt.assignee == "me":
            query = query.where(Invoice.assigned_to == flt.user_id)
        query = _search_filters(query, flt)
        if page_token is not None:
            after = decode_token(page_token)
            query = query.where(tuple_(Invoice.created_at, Invoice.id) < tuple_(*after))
        size = min(max(page_size, 1), MAX_PAGE_SIZE)
        query = (
            query.order_by(Invoice.created_at.desc(), Invoice.id.desc())
            .limit(size + 1)
            .options(selectinload(Invoice.exceptions))
        )
        async with self._sessions() as session:
            rows = list((await session.execute(query)).scalars())
            more = len(rows) > size
            rows = rows[:size]
            names = await self._display_names(session, {r.assigned_to for r in rows} - {None})
        items = [
            InvoiceSummaryView(
                id=r.id,
                status=r.status,
                invoice_type=r.invoice_type,
                vendor_name=r.vendor_name,
                invoice_number=r.invoice_number,
                total_amount=r.total_amount,
                currency=r.currency,
                open_exception_codes=sorted(
                    {e.code for e in r.exceptions if e.status is ExceptionStatus.OPEN},
                    key=lambda code: int(code.value[2:]),
                ),
                assigned_to=UserRef(r.assigned_to, names.get(r.assigned_to, "")) if r.assigned_to else None,
                updated_at=r.updated_at,
                invoice_date=r.invoice_date,
                channel=r.channel,
                uploaded_at=r.created_at,
            )
            for r in rows
        ]
        token = encode_token(rows[-1].created_at, rows[-1].id) if more else None
        return Page(items, token)

    async def list_events(
        self, tenant_id: UUID, invoice_id: UUID, page_size: int, page_token: str | None
    ) -> Page[InvoiceEventView] | None:
        async with self._sessions() as session:
            exists = await session.scalar(
                select(Invoice.id).where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
            )
            if exists is None:
                return None
            query = select(InvoiceEvent).where(InvoiceEvent.invoice_id == invoice_id)
            if page_token is not None:
                after = decode_token(page_token)
                query = query.where(tuple_(InvoiceEvent.occurred_at, InvoiceEvent.id) > tuple_(*after))
            size = min(max(page_size, 1), MAX_PAGE_SIZE)
            query = query.order_by(InvoiceEvent.occurred_at, InvoiceEvent.id).limit(size + 1)
            rows = list((await session.execute(query)).scalars())
            more = len(rows) > size
            rows = rows[:size]
            users = await session.execute(
                select(UserAccount.username, UserAccount.display_name).where(
                    UserAccount.tenant_id == tenant_id, UserAccount.username.in_({r.actor for r in rows})
                )
            )
            display = {username: display_name for username, display_name in users}
        items = [
            InvoiceEventView(
                e.id,
                e.status_from,
                e.status_to,
                e.action,
                display.get(e.actor, e.actor),
                e.details,
                e.occurred_at,
            )
            for e in rows
        ]
        token = encode_token(rows[-1].occurred_at, rows[-1].id) if more else None
        return Page(items, token)

    async def file_of(self, tenant_id: UUID, invoice_id: UUID) -> StoredInvoiceFile | None:
        async with self._sessions() as session:
            row = (
                await session.execute(
                    select(Invoice.file_storage_key, Invoice.file_content_type, Invoice.file_name).where(
                        Invoice.id == invoice_id, Invoice.tenant_id == tenant_id
                    )
                )
            ).one_or_none()
        return StoredInvoiceFile(row[0], row[1], row[2]) if row else None

    @staticmethod
    async def _display_names(session: AsyncSession, user_ids: set[UUID | None]) -> dict[UUID, str]:
        ids = [i for i in user_ids if i is not None]
        if not ids:
            return {}
        rows = await session.execute(
            select(UserAccount.id, UserAccount.display_name).where(UserAccount.id.in_(ids))
        )
        return {user_id: name for user_id, name in rows}
