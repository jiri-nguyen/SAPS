"""ERP Data Port (ADR-0001): purchase orders and goods receipts; dummy fixtures in the PoC, SAP later."""

from collections.abc import Sequence
from typing import Protocol

from saps.domain.matching import GoodsReceiptLine, PurchaseOrder


class ErpDataPort(Protocol):
    """One call of each per invoice, for all its PO numbers (SAPS-19 NFR-SCAL-001)."""

    async def get_purchase_orders(self, po_numbers: Sequence[str]) -> dict[str, PurchaseOrder]:
        """Known purchase orders by PO number; unknown numbers are missing from the result."""
        ...

    async def get_goods_receipt_lines(self, po_numbers: Sequence[str]) -> list[GoodsReceiptLine]: ...
