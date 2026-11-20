"""Upload use case (SAPS-17): check the file, store it, create the invoice, queue processing."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO
from uuid import UUID, uuid4

from saps.domain.invoice_files import check_file, clean_file_name, storage_key
from saps.domain.users import CurrentUser
from saps.ports.file_storage import FileStoragePort
from saps.ports.invoices import (
    DuplicateIdempotencyKeyError,
    InvoiceFile,
    InvoiceReader,
    InvoiceRepository,
    InvoiceView,
    NewUpload,
)
from saps.ports.job_queue import JobQueuePort


@dataclass(frozen=True)
class IncomingFile:
    """The received file, already spooled; `head` holds its first bytes (magic bytes, BR-02)."""

    name: str | None
    size: int
    sha256: str
    head: bytes
    data: BinaryIO


@dataclass(frozen=True)
class UploadResult:
    invoice: InvoiceView
    created: bool  # False: the Idempotency-Key was used before (BR-06)
    queued: bool  # False: process_invoice could not be sent; the sweeper sends it later (EC-06)


class UploadInvoiceService:
    def __init__(
        self,
        repository: InvoiceRepository,
        reader: InvoiceReader,
        storage: FileStoragePort,
        queue: JobQueuePort,
        clock: Callable[[], datetime],
        max_size_bytes: int,
    ) -> None:
        self._repo = repository
        self._reader = reader
        self._storage = storage
        self._queue = queue
        self._clock = clock
        self._max_size = max_size_bytes

    async def upload(self, user: CurrentUser, idempotency_key: str, file: IncomingFile) -> UploadResult:
        existing = await self._repo.find_by_idempotency_key(user.tenant_id, idempotency_key)
        if existing is not None:
            return UploadResult(await self._view(user, existing), created=False, queued=False)

        content_type = check_file(file.size, file.head, self._max_size)  # raises FileRejectedError
        invoice_id = uuid4()
        key = storage_key(invoice_id, file.sha256)
        await self._storage.put(key, file.data, content_type)  # EC-07: failure → nothing in the database

        upload = NewUpload(
            invoice_id=invoice_id,
            tenant_id=user.tenant_id,
            uploaded_by=user.user_id,
            actor=user.username,
            file=InvoiceFile(clean_file_name(file.name), content_type, file.size, file.sha256),
            storage_key=key,
            idempotency_key=idempotency_key,
            uploaded_at=self._clock(),
        )
        try:
            await self._repo.add_uploaded(upload)
        except DuplicateIdempotencyKeyError:  # EC-04: a parallel request with the same key won
            winner = await self._repo.find_by_idempotency_key(user.tenant_id, idempotency_key)
            if winner is None:  # pragma: no cover - the unique index guarantees a winner
                raise
            return UploadResult(await self._view(user, winner), created=False, queued=False)

        try:
            await self._queue.send_process_invoice(invoice_id)
            queued = True
        except Exception:  # EC-06: the invoice stays Uploaded until the sweeper re-sends the message
            queued = False
        return UploadResult(await self._view(user, invoice_id), created=True, queued=queued)

    async def _view(self, user: CurrentUser, invoice_id: UUID) -> InvoiceView:
        view = await self._reader.get(user.tenant_id, invoice_id)
        if view is None:  # pragma: no cover - read right after a committed insert in the same tenant
            raise LookupError(invoice_id)
        return view
