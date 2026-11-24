"""Dummy ERP Adapter (ADR-0001): POs and goods receipts from `<FIXTURES_DIR>/*/erp/*.json`, per company.

`companies.json` lists, for each demo company, the ERP fixture files it uses (SAPS-42 BR-03). Every file is
parsed once; each company gets its own catalogue, so the same demo catalogue can serve several companies
without sharing anything. A broken file, a PO / goods receipt number used twice within a company, or a pattern
without files fails at load time, not during a demo.
"""

import logging
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from saps.adapters.demo.companies import load_demo_companies
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


log = logging.getLogger("saps.worker.erp")


class ErpCatalogue:
    """The POs and goods receipts of one company, from a list of fixture files."""

    def __init__(self, files: list[tuple[Path, ErpFixtureFile]]) -> None:
        self._orders: dict[str, PurchaseOrder] = {}
        self._receipts: list[GoodsReceiptLine] = []
        gr_numbers: set[str] = set()
        for path, data in files:
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

    def purchase_orders(self, po_numbers: Sequence[str]) -> dict[str, PurchaseOrder]:
        return {n: self._orders[n] for n in po_numbers if n in self._orders}

    def goods_receipt_lines(self, po_numbers: Sequence[str]) -> list[GoodsReceiptLine]:
        wanted = set(po_numbers)
        return [line for line in self._receipts if line.po_number in wanted]


_EMPTY = ErpCatalogue([])


class DummyErpAdapter:
    def __init__(self, fixtures_dir: Path) -> None:
        parsed: dict[Path, ErpFixtureFile] = {}
        self._catalogues: dict[str, ErpCatalogue] = {}
        for company in load_demo_companies(fixtures_dir).companies:
            files: list[Path] = []
            for pattern in company.erp:
                matched = sorted(fixtures_dir.glob(pattern))
                if not matched:
                    raise ErpFixtureError(f"company {company.code}: {pattern} matches no ERP file")
                files.extend(p for p in matched if p not in files)
            for path in files:
                if path not in parsed:
                    parsed[path] = ErpFixtureFile.model_validate_json(path.read_bytes())
            self._catalogues[company.code] = ErpCatalogue([(p, parsed[p]) for p in files])
        self._unknown_logged: set[str] = set()

    def purchase_order_count(self, company_code: str) -> int:
        return self._catalogue(company_code).purchase_order_count

    async def get_purchase_orders(
        self, company_code: str, po_numbers: Sequence[str]
    ) -> dict[str, PurchaseOrder]:
        return self._catalogue(company_code).purchase_orders(po_numbers)

    async def get_goods_receipt_lines(
        self, company_code: str, po_numbers: Sequence[str]
    ) -> list[GoodsReceiptLine]:
        return self._catalogue(company_code).goods_receipt_lines(po_numbers)

    def _catalogue(self, company_code: str) -> ErpCatalogue:
        catalogue = self._catalogues.get(company_code)
        if catalogue is None:  # EC-03: a tenant without demo ERP data
            if company_code not in self._unknown_logged:
                self._unknown_logged.add(company_code)
                log.warning("erp_company_unknown", extra={"company_code": company_code})
            return _EMPTY
        return catalogue
