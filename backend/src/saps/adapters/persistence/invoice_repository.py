"""SQL adapters of the invoice ports (SAPS-17). Each call uses its own short transaction."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from saps.adapters.persistence.models import Approval, Invoice, InvoiceEvent, UserAccount
from saps.domain.invoices import InvoiceStatus
from saps.ports.invoices import (
    ApprovalView,
    DuplicateIdempotencyKeyError,
    InvoiceExceptionView,
    InvoiceFile,
    InvoiceLineView,
    InvoiceView,
    NewUpload,
    UserRef,
)

UPLOAD_ACTION = "UPLOAD"
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
                        details={
                            "fileName": upload.file.name,
                            "sizeBytes": upload.file.size_bytes,
                            "sha256": upload.file.sha256,
                        },
                        occurred_at=upload.uploaded_at,
                        created_by=upload.actor,
                        updated_by=upload.actor,
                    )
                )
        except IntegrityError as exc:
            if _IDEMPOTENCY_CONSTRAINT in str(exc.orig):
                raise DuplicateIdempotencyKeyError(upload.idempotency_key) from exc
            raise

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
            uploaded_by=user(invoice.uploaded_by),
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
