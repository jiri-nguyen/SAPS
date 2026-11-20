"""In-memory ports for tests: File Storage, Job Queue, invoice repository and reader."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import BinaryIO
from uuid import UUID

from saps.domain.invoices import InvoiceStatus
from saps.ports.invoices import DuplicateIdempotencyKeyError, InvoiceView, NewUpload, UserRef

NOW = datetime(2026, 12, 15, 9, 0, tzinfo=UTC)

PDF_BYTES = b"%PDF-1.7\n% SAPS test file\n%%EOF\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32


class MemoryStorage:
    def __init__(self, fail: bool = False) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.fail = fail

    async def put(self, key: str, data: BinaryIO, content_type: str) -> None:
        if self.fail:
            raise OSError("SAPS File Storage unavailable")
        self.objects[key] = (data.read(), content_type)

    async def get(self, key: str) -> AsyncIterator[bytes]:
        if key not in self.objects:
            raise FileNotFoundError(key)
        content = self.objects[key][0]
        for start in range(0, len(content), 8):  # small chunks, like a real stream
            yield content[start : start + 8]


class MemoryQueue:
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[UUID] = []
        self.rematch: list[UUID] = []
        self.fail = fail

    async def send_process_invoice(self, invoice_id: UUID) -> None:
        if self.fail:
            raise ConnectionError("SAPS Message Broker unavailable")
        self.sent.append(invoice_id)

    async def send_rematch_invoice(self, invoice_id: UUID) -> None:
        if self.fail:
            raise ConnectionError("SAPS Message Broker unavailable")
        self.rematch.append(invoice_id)


class MemoryInvoices:
    def __init__(self) -> None:
        self.uploads: dict[UUID, NewUpload] = {}
        self.race_winner: NewUpload | None = None

    async def find_by_idempotency_key(self, tenant_id: UUID, key: str) -> UUID | None:
        return next(
            (
                u.invoice_id
                for u in self.uploads.values()
                if (u.tenant_id, u.idempotency_key) == (tenant_id, key)
            ),
            None,
        )

    async def add_uploaded(self, upload: NewUpload) -> None:
        if self.race_winner is not None:  # a parallel request committed first
            self.uploads[self.race_winner.invoice_id] = self.race_winner
            raise DuplicateIdempotencyKeyError(upload.idempotency_key)
        self.uploads[upload.invoice_id] = upload

    async def get(self, tenant_id: UUID, invoice_id: UUID) -> InvoiceView | None:
        upload = self.uploads.get(invoice_id)
        if upload is None or upload.tenant_id != tenant_id:
            return None
        empty: dict[str, None] = dict.fromkeys(
            ["invoice_type", "vendor_code", "vendor_name", "invoice_number", "invoice_date",
             "subtotal_amount", "tax_amount", "total_amount", "requires_approval", "price_tolerance_applied",
             "approval_threshold_applied", "assigned_to", "rejected_reason", "approval"]
        )  # fmt: skip
        return InvoiceView(
            id=upload.invoice_id,
            status=InvoiceStatus.UPLOADED,
            currency="USD",
            uploaded_by=UserRef(upload.uploaded_by, "Accounting Member 1"),
            file=upload.file,
            lines=[],
            exceptions=[],
            created_at=NOW,
            updated_at=NOW,
            **empty,  # type: ignore[arg-type]
        )
