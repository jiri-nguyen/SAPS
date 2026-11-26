"""Invoice operations: uploadInvoice (SAPS-17) and getInvoice."""

import hashlib
import logging
import time
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from saps.api.deps import (
    User,
    approval_service,
    exception_service,
    file_storage,
    invoice_hold_service,
    invoice_reader,
    require_roles,
    upload_service,
)
from saps.api.problems import FieldProblem
from saps.api.schemas import (
    ApprovalCreate,
    Invoice,
    InvoiceEvent,
    InvoiceEventPage,
    InvoiceSummary,
    InvoiceSummaryPage,
    InvoiceUpdate,
    RejectionCreate,
)
from saps.application.approval import ApprovalService
from saps.application.exception_handling import (
    ConflictError,
    ExceptionHandlingService,
    ForbiddenError,
    HandlingError,
    PreconditionFailedError,
    UnprocessableError,
)
from saps.application.invoices import (
    InvoiceNotFoundError,
    etag_of,
    get_invoice,
    list_invoice_events,
    open_invoice_file,
    search_invoices,
)
from saps.application.processing_calendar import InvoiceHoldService
from saps.application.upload import IncomingFile, UploadInvoiceService, UploadSource
from saps.domain.exception_handling import LineData
from saps.domain.invoice_files import (
    HEADER_BYTES,
    EmptyFileError,
    FileRejectedError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from saps.domain.invoice_search import InvalidSearchError, SearchCriteria
from saps.domain.invoices import ApprovalDecision, InvoiceStatus, InvoiceType
from saps.domain.mail_intake import IntakeChannel
from saps.domain.users import CurrentUser, Role
from saps.ports.file_storage import FileStoragePort
from saps.ports.invoices import InvalidPageTokenError, InvoiceFilter, InvoiceReader, InvoiceView

router = APIRouter(prefix="/v1/invoices", tags=["Invoices"])
log = logging.getLogger("saps.api.invoices")

_CHUNK_BYTES = 1024 * 1024
_REJECTION_STATUS: dict[type[FileRejectedError], int] = {
    EmptyFileError: status.HTTP_400_BAD_REQUEST,
    FileTooLargeError: status.HTTP_413_CONTENT_TOO_LARGE,
    UnsupportedFileTypeError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
}

Member = Annotated[CurrentUser, Depends(require_roles(Role.ACCOUNTING_MEMBER))]
Manager = Annotated[CurrentUser, Depends(require_roles(Role.ACCOUNTING_MANAGER))]
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
        result = await service.upload(UploadSource.of_user(user), idempotency_key, incoming)
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
    return _invoice_response(response, view)


# --- exception handling (SAPS-20) ---------------------------------------------------------------------

_HANDLING_STATUS: dict[type[HandlingError], int] = {
    ConflictError: status.HTTP_409_CONFLICT,
    ForbiddenError: status.HTTP_403_FORBIDDEN,
    PreconditionFailedError: status.HTTP_412_PRECONDITION_FAILED,
    UnprocessableError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}
Service = Annotated[ExceptionHandlingService, Depends(exception_service)]
Approvals = Annotated[ApprovalService, Depends(approval_service)]
IfMatch = Annotated[str | None, Header(alias="If-Match")]


def _invoice_response(response: Response, view: InvoiceView) -> Invoice:
    """The current version travels as ETag; clients send it back as If-Match (EC-02)."""
    response.headers["ETag"] = etag_of(view.updated_at)
    return Invoice.from_view(view)


def _problem(exc: Exception) -> HTTPException:
    if isinstance(exc, InvoiceNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found.")
    assert isinstance(exc, HandlingError)
    return HTTPException(_HANDLING_STATUS[type(exc)], exc.detail)


def _require_if_match(if_match: str | None) -> str:
    if not if_match:
        raise HTTPException(status.HTTP_428_PRECONDITION_REQUIRED, "The If-Match header is required.")
    return if_match


@router.get("", operation_id="listInvoices", response_model_by_alias=True)
async def list_invoices_operation(
    user: User,
    reader: Annotated[InvoiceReader, Depends(invoice_reader)],
    statuses: Annotated[list[InvoiceStatus] | None, Query(alias="status")] = None,
    invoice_type: Annotated[InvoiceType | None, Query(alias="invoiceType")] = None,
    assignee: Literal["me", "unassigned"] | None = None,
    vendor: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    invoice_number: Annotated[str | None, Query(alias="invoiceNumber", min_length=1, max_length=50)] = None,
    po_number: Annotated[str | None, Query(alias="poNumber", pattern=r"^[0-9]{7}$")] = None,
    invoice_date_from: Annotated[date | None, Query(alias="invoiceDateFrom")] = None,
    invoice_date_to: Annotated[date | None, Query(alias="invoiceDateTo")] = None,
    uploaded_from: Annotated[date | None, Query(alias="uploadedFrom")] = None,
    uploaded_to: Annotated[date | None, Query(alias="uploadedTo")] = None,
    total_min: Annotated[Decimal | None, Query(alias="totalMin", max_digits=18, decimal_places=2)] = None,
    total_max: Annotated[Decimal | None, Query(alias="totalMax", max_digits=18, decimal_places=2)] = None,
    channel: IntakeChannel | None = None,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    page_token: Annotated[str | None, Query(alias="pageToken")] = None,
) -> InvoiceSummaryPage:
    base = InvoiceFilter(tuple(statuses or ()), invoice_type, assignee, user.user_id)
    criteria = SearchCriteria(
        vendor=vendor,
        invoice_number=invoice_number,
        po_number=po_number,
        invoice_date_from=invoice_date_from,
        invoice_date_to=invoice_date_to,
        uploaded_from=uploaded_from,
        uploaded_to=uploaded_to,
        total_min=total_min,
        total_max=total_max,
        channel=channel,
    )
    try:
        page = await search_invoices(reader, user, criteria, base, page_size, page_token)
    except InvalidSearchError as exc:
        raise FieldProblem(
            status.HTTP_400_BAD_REQUEST, exc.message, [{"field": exc.field, "message": exc.message}]
        ) from exc
    except InvalidPageTokenError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The page token is not valid.") from exc
    return InvoiceSummaryPage(
        items=[InvoiceSummary.from_view(v) for v in page.items], next_page_token=page.next_page_token
    )


@router.post("/{invoice_id}/claim", operation_id="claimInvoice", response_model_by_alias=True)
async def claim_invoice(invoice_id: UUID, response: Response, user: Member, service: Service) -> Invoice:
    try:
        view = await service.claim(user, invoice_id)
    except (InvoiceNotFoundError, HandlingError) as exc:
        raise _problem(exc) from exc
    log.info("invoice_claimed", extra={"invoice_id": str(invoice_id), "user_id": str(user.user_id)})
    return _invoice_response(response, view)


@router.post("/{invoice_id}/release", operation_id="releaseInvoice", response_model_by_alias=True)
async def release_invoice(
    invoice_id: UUID,
    response: Response,
    user: Manager,
    service: Annotated[InvoiceHoldService, Depends(invoice_hold_service)],
    reader: Annotated[InvoiceReader, Depends(invoice_reader)],
) -> Invoice:
    """Process now: a held invoice goes back to Uploaded although the company is closed (SAPS-52 BR-06)."""
    try:
        await service.release(user, invoice_id)
        view = await get_invoice(reader, user, invoice_id)
    except (InvoiceNotFoundError, HandlingError) as exc:
        raise _problem(exc) from exc
    return _invoice_response(response, view)


@router.delete(
    "/{invoice_id}/claim",
    operation_id="releaseInvoiceClaim",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def release_invoice_claim(
    invoice_id: UUID,
    user: Annotated[CurrentUser, Depends(require_roles(Role.ACCOUNTING_MEMBER, Role.ACCOUNTING_MANAGER))],
    service: Service,
) -> Response:
    try:
        await service.release(user, invoice_id)
    except (InvoiceNotFoundError, HandlingError) as exc:
        raise _problem(exc) from exc
    log.info("invoice_claim_released", extra={"invoice_id": str(invoice_id), "user_id": str(user.user_id)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{invoice_id}", operation_id="updateInvoice", response_model_by_alias=True)
async def update_invoice(
    invoice_id: UUID,
    body: InvoiceUpdate,
    response: Response,
    user: Member,
    service: Service,
    if_match: IfMatch = None,
) -> Invoice:
    etag = _require_if_match(if_match)
    lines = (
        [
            LineData(
                ln.line_number,
                ln.description,
                ln.po_number,
                ln.po_line_number,
                ln.quantity,
                ln.unit_price,
                ln.line_amount,
                ln.do_number,
            )
            for ln in body.lines
        ]
        if body.lines is not None
        else None
    )
    try:
        result = await service.update(user, invoice_id, etag, body.header(), lines)
    except (InvoiceNotFoundError, HandlingError) as exc:
        raise _problem(exc) from exc
    log.info("invoice_updated", extra={"invoice_id": str(invoice_id), "rematch": result.rematch})
    if result.rematch:
        response.status_code = status.HTTP_202_ACCEPTED
    return _invoice_response(response, result.invoice)


@router.post(
    "/{invoice_id}/resolution", operation_id="resolveInvoiceExceptions", response_model_by_alias=True
)
async def resolve_invoice_exceptions(
    invoice_id: UUID, response: Response, user: Member, service: Service, if_match: IfMatch = None
) -> Invoice:
    etag = _require_if_match(if_match)
    try:
        view = await service.resolve(user, invoice_id, etag)
    except (InvoiceNotFoundError, HandlingError) as exc:
        raise _problem(exc) from exc
    log.info("exceptions_resolved", extra={"invoice_id": str(invoice_id), "status": view.status.value})
    response.status_code = status.HTTP_202_ACCEPTED  # the workflow runs again (SAPS-49 BR-04)
    return _invoice_response(response, view)


@router.post("/{invoice_id}/rejection", operation_id="rejectInvoice", response_model_by_alias=True)
async def reject_invoice(
    invoice_id: UUID, body: RejectionCreate, response: Response, user: Member, service: Service
) -> Invoice:
    try:
        view, _ = await service.reject(user, invoice_id, body.reason)
    except (InvoiceNotFoundError, HandlingError) as exc:
        raise _problem(exc) from exc
    log.info("invoice_rejected", extra={"invoice_id": str(invoice_id), "user_id": str(user.user_id)})
    return _invoice_response(response, view)


@router.post("/{invoice_id}/approval", operation_id="decideInvoiceApproval", response_model_by_alias=True)
async def decide_invoice_approval(
    invoice_id: UUID, body: ApprovalCreate, response: Response, user: Manager, service: Approvals
) -> Invoice:
    try:
        view = await service.decide(user, invoice_id, body.decision, body.comment)
    except (InvoiceNotFoundError, HandlingError) as exc:
        raise _problem(exc) from exc
    event = (
        "invoice_approved" if body.decision is ApprovalDecision.APPROVED else "invoice_rejected_by_manager"
    )
    log.info(event, extra={"invoice_id": str(invoice_id), "user_id": str(user.user_id)})
    return _invoice_response(response, view)


@router.get("/{invoice_id}/file", operation_id="downloadInvoiceFile")
async def download_invoice_file(
    invoice_id: UUID,
    user: User,
    reader: Annotated[InvoiceReader, Depends(invoice_reader)],
    storage: Annotated[FileStoragePort, Depends(file_storage)],
) -> StreamingResponse:
    try:
        info, chunks = await open_invoice_file(reader, storage, user, invoice_id)
    except InvoiceNotFoundError as exc:
        raise _problem(exc) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The invoice file is not available.") from exc
    disposition = f"inline; filename*=UTF-8''{quote(info.name)}"
    return StreamingResponse(
        chunks, media_type=info.content_type, headers={"Content-Disposition": disposition}
    )


@router.get("/{invoice_id}/events", operation_id="listInvoiceEvents", response_model_by_alias=True)
async def list_invoice_events_operation(
    invoice_id: UUID,
    user: User,
    reader: Annotated[InvoiceReader, Depends(invoice_reader)],
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    page_token: Annotated[str | None, Query(alias="pageToken")] = None,
) -> InvoiceEventPage:
    try:
        page = await list_invoice_events(reader, user, invoice_id, page_size, page_token)
    except InvoiceNotFoundError as exc:
        raise _problem(exc) from exc
    except InvalidPageTokenError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The page token is not valid.") from exc
    return InvoiceEventPage(
        items=[InvoiceEvent.from_view(v) for v in page.items], next_page_token=page.next_page_token
    )
