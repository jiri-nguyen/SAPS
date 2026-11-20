"""Invoice queries (getInvoice, listInvoices, listInvoiceEvents, downloadInvoiceFile).

The tenant comes from the signed-in user (ADR-0007, SAPS-27 BR-08).
"""

from collections.abc import AsyncIterator
from datetime import datetime
from uuid import UUID

from saps.domain.users import CurrentUser
from saps.ports.file_storage import FileStoragePort
from saps.ports.invoices import (
    InvoiceEventView,
    InvoiceFilter,
    InvoiceReader,
    InvoiceSummaryView,
    InvoiceView,
    Page,
    StoredInvoiceFile,
)


class InvoiceNotFoundError(Exception):
    """Unknown invoice, or an invoice of another tenant (both answer 404)."""


def etag_of(updated_at: datetime) -> str:
    """Weak ETag from the last change of the invoice row; `If-Match` compares it (SAPS-20 EC-02)."""
    return f'W/"{int(updated_at.timestamp() * 1_000_000)}"'


def etag_matches(if_match: str, current: str) -> bool:
    """`If-Match` as sent by a client: weak or strong form of the same ETag."""

    def bare(value: str) -> str:
        return value.strip().removeprefix("W/").strip('"')

    return bare(if_match) == bare(current)


async def get_invoice(reader: InvoiceReader, user: CurrentUser, invoice_id: UUID) -> InvoiceView:
    view = await reader.get(user.tenant_id, invoice_id)
    if view is None:
        raise InvoiceNotFoundError(invoice_id)
    return view


async def list_invoices(
    reader: InvoiceReader, user: CurrentUser, flt: InvoiceFilter, page_size: int, page_token: str | None
) -> Page[InvoiceSummaryView]:
    return await reader.list_invoices(user.tenant_id, flt, page_size, page_token)


async def list_invoice_events(
    reader: InvoiceReader, user: CurrentUser, invoice_id: UUID, page_size: int, page_token: str | None
) -> Page[InvoiceEventView]:
    page = await reader.list_events(user.tenant_id, invoice_id, page_size, page_token)
    if page is None:
        raise InvoiceNotFoundError(invoice_id)
    return page


async def open_invoice_file(
    reader: InvoiceReader, storage: FileStoragePort, user: CurrentUser, invoice_id: UUID
) -> tuple[StoredInvoiceFile, AsyncIterator[bytes]]:
    """The file and its content stream. The first chunk is read here, so a missing object is found before the
    response starts (FileNotFoundError)."""
    info = await reader.file_of(user.tenant_id, invoice_id)
    if info is None:
        raise InvoiceNotFoundError(invoice_id)
    chunks = storage.get(info.storage_key)
    try:
        first = await anext(chunks)
    except StopAsyncIteration:
        first = b""

    async def stream() -> AsyncIterator[bytes]:
        if first:
            yield first
        async for chunk in chunks:
            yield chunk

    return info, stream()
