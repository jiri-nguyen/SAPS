"""Dummy ERP Adapter (ADR-0001): POs and goods receipts from `<FIXTURES_DIR>/<scenario>/erp/*.json`.

All scenario files are loaded and validated once; a broken file or a PO / goods receipt number used twice
fails at load time, not during a demo.
"""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from saps.domain.matching import GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine

PO_NUMBER_PATTERN = r"^[01]\d{6}$"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _PoLine(_Model):
    po_line_number: int = Field(gt=0)
    description: str
    ordered_quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class _PurchaseOrder(_Model):
    po_number: str = Field(pattern=PO_NUMBER_PATTERN)
    vendor_code: str = Field(min_length=1, max_length=20)
    currency: str = Field(pattern=r"^USD$")
    lines: list[_PoLine] = Field(min_length=1)


class _GrLine(_Model):
    po_line_number: int = Field(gt=0)
    received_quantity: Decimal = Field(gt=0)


class _GoodsReceipt(_Model):
    gr_number: str = Field(min_length=1)
    po_number: str = Field(pattern=PO_NUMBER_PATTERN)
    receipt_date: date
    lines: list[_GrLine] = Field(min_length=1)


class ErpFixtureFile(_Model):
    """Schema of one `erp/*.json` fixture file (decimals as strings, no floats)."""

    purchase_orders: list[_PurchaseOrder] = []
    goods_receipts: list[_GoodsReceipt] = []


class ErpFixtureError(ValueError):
    """The dummy ERP data is inconsistent."""


class DummyErpAdapter:
    def __init__(self, fixtures_dir: Path) -> None:
        self._orders: dict[str, PurchaseOrder] = {}
        self._receipts: list[GoodsReceiptLine] = []
        gr_numbers: set[str] = set()
        for path in sorted(fixtures_dir.glob("*/erp/*.json")):
            data = ErpFixtureFile.model_validate_json(path.read_bytes())
            for order in data.purchase_orders:
                if order.po_number in self._orders:
                    raise ErpFixtureError(f"{path}: PO {order.po_number} is defined twice")
                lines = {line.po_line_number: line for line in order.lines}
                if len(lines) != len(order.lines):
                    raise ErpFixtureError(f"{path}: PO {order.po_number} repeats a line number")
                self._orders[order.po_number] = PurchaseOrder(
                    order.po_number,
                    order.vendor_code,
                    order.currency,
                    {
                        n: PurchaseOrderLine(n, line.description, line.ordered_quantity, line.unit_price)
                        for n, line in lines.items()
                    },
                )
            for receipt in data.goods_receipts:
                if receipt.gr_number in gr_numbers:
                    raise ErpFixtureError(f"{path}: goods receipt {receipt.gr_number} is defined twice")
                gr_numbers.add(receipt.gr_number)
                self._receipts.extend(
                    GoodsReceiptLine(
                        receipt.gr_number, receipt.po_number, line.po_line_number, line.received_quantity
                    )
                    for line in receipt.lines
                )
        for line in self._receipts:
            known = self._orders.get(line.po_number)
            if known is None or line.po_line_number not in known.lines:
                raise ErpFixtureError(
                    f"goods receipt {line.gr_number} refers to unknown "
                    f"PO {line.po_number} line {line.po_line_number}"
                )

    @property
    def purchase_order_count(self) -> int:
        return len(self._orders)

    async def get_purchase_orders(self, po_numbers: Sequence[str]) -> dict[str, PurchaseOrder]:
        return {n: self._orders[n] for n in po_numbers if n in self._orders}

    async def get_goods_receipt_lines(self, po_numbers: Sequence[str]) -> list[GoodsReceiptLine]:
        wanted = set(po_numbers)
        return [line for line in self._receipts if line.po_number in wanted]
