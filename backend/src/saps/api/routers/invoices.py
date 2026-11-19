"""Invoice operations: uploadInvoice (SAPS-17) and getInvoice."""

import hashlib
import logging
import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, UploadFile, status

from saps.api.deps import User, invoice_reader, require_roles, upload_service
from saps.api.schemas import Invoice
from saps.application.invoices import InvoiceNotFoundError, get_invoice
from saps.application.upload import IncomingFile, UploadInvoiceService
from saps.domain.invoice_files import (
    HEADER_BYTES,
    EmptyFileError,
    FileRejectedError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from saps.domain.users import CurrentUser, Role
from saps.ports.invoices import InvoiceReader

router = APIRouter(prefix="/v1/invoices", tags=["Invoices"])
log = logging.getLogger("saps.api.invoices")

_CHUNK_BYTES = 1024 * 1024
_REJECTION_STATUS: dict[type[FileRejectedError], int] = {
    EmptyFileError: status.HTTP_400_BAD_REQUEST,
    FileTooLargeError: status.HTTP_413_CONTENT_TOO_LARGE,
    UnsupportedFileTypeError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
}

Member = Annotated[CurrentUser, Depends(require_roles(Role.ACCOUNTING_MEMBER))]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=64)]


async def _inspect(file: UploadFile) -> IncomingFile:
    """Size, SHA-256 and first bytes of the spooled file (BR-04); the content is never held in memory."""
    digest = hashlib.sha256()
    size = 0
    head = b""
    await file.seek(0)
    while chunk := await file.read(_CHUNK_BYTES):
        if len(head) < HEADER_BYTES:
            head = (head + chunk)[:HEADER_BYTES]
        digest.update(chunk)
        size += len(chunk)
    await file.seek(0)
    return IncomingFile(file.filename, size, digest.hexdigest(), head, file.file)


@router.post(
    "", operation_id="uploadInvoice", status_code=status.HTTP_202_ACCEPTED, response_model_by_alias=True
)
async def upload_invoice(
    file: UploadFile,
    response: Response,
    user: Member,
    idempotency_key: IdempotencyKey,
    service: Annotated[UploadInvoiceService, Depends(upload_service)],
) -> Invoice:
    started = time.perf_counter()
    incoming = await _inspect(file)
    try:
        result = await service.upload(user, idempotency_key, incoming)
    except FileRejectedError as exc:
        log.info("upload_rejected", extra={"reason": type(exc).__name__, "tenant_id": str(user.tenant_id)})
        raise HTTPException(_REJECTION_STATUS[type(exc)], str(exc)) from exc

    invoice = result.invoice
    response.headers["Location"] = f"/v1/invoices/{invoice.id}"
    if result.created:
        log.info(
            "invoice_uploaded",
            extra={
                "invoice_id": str(invoice.id),
                "tenant_id": str(user.tenant_id),
                "size_bytes": invoice.file.size_bytes,
                "content_type": invoice.file.content_type,
                "duration_ms": round((time.perf_counter() - started) * 1000),
            },
        )
        if not result.queued:
            log.warning("process_invoice_not_sent", extra={"invoice_id": str(invoice.id)})
    else:
        log.info("upload_replayed", extra={"invoice_id": str(invoice.id), "tenant_id": str(user.tenant_id)})
    return Invoice.from_view(invoice)


@router.get("/{invoice_id}", operation_id="getInvoice", response_model_by_alias=True)
async def get_invoice_operation(
    invoice_id: UUID,
    response: Response,
    user: User,
    reader: Annotated[InvoiceReader, Depends(invoice_reader)],
) -> Invoice:
    try:
        view = await get_invoice(reader, user, invoice_id)
    except InvoiceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found.") from exc
    # Weak ETag from the last change of the invoice row; If-Match handling comes with updateInvoice (SAPS-20).
    response.headers["ETag"] = f'W/"{int(view.updated_at.timestamp() * 1_000_000)}"'
    return Invoice.from_view(view)
