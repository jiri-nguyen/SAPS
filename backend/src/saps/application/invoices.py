"""Invoice queries (getInvoice). Tenant from the signed-in user (ADR-0007, SAPS-27 BR-08)."""

from uuid import UUID

from saps.domain.users import CurrentUser
from saps.ports.invoices import InvoiceReader, InvoiceView


class InvoiceNotFoundError(Exception):
    """Unknown invoice, or an invoice of another tenant (both answer 404)."""


async def get_invoice(reader: InvoiceReader, user: CurrentUser, invoice_id: UUID) -> InvoiceView:
    view = await reader.get(user.tenant_id, invoice_id)
    if view is None:
        raise InvoiceNotFoundError(invoice_id)
    return view
