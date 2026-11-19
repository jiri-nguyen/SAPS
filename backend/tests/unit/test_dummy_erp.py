import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from saps.adapters.erp.dummy_erp import DummyErpAdapter, ErpFixtureError

FIXTURES = Path(__file__).parents[2] / "fixtures"


def _write(root: Path, scenario: str, data: dict[str, object]) -> None:
    folder = root / scenario / "erp"
    folder.mkdir(parents=True)
    (folder / "erp.json").write_text(json.dumps(data))


def _po(number: str = "0100001", lines: int = 1) -> dict[str, object]:
    return {
        "po_number": number,
        "vendor_code": "V001",
        "currency": "USD",
        "lines": [
            {"po_line_number": 1, "description": "x", "ordered_quantity": "1", "unit_price": "1.00"}
            for _ in range(lines)
        ],
    }


def _gr(number: str = "5000001", po: str = "0100001", po_line: int = 1) -> dict[str, object]:
    return {
        "gr_number": number,
        "po_number": po,
        "receipt_date": "2026-12-01",
        "lines": [{"po_line_number": po_line, "received_quantity": "1"}],
    }


def test_the_demo_fixtures_are_valid() -> None:  # like SAPS-18 TS-04: broken demo data fails in CI
    adapter = DummyErpAdapter(FIXTURES)
    assert adapter.purchase_order_count == 17


async def test_reads_orders_and_receipts_by_po_number() -> None:
    adapter = DummyErpAdapter(FIXTURES)
    orders = await adapter.get_purchase_orders(["0100004", "0199999"])
    assert list(orders) == ["0100004"]
    assert orders["0100004"].lines[1].unit_price == Decimal("15.00")
    receipts = await adapter.get_goods_receipt_lines(["0100004"])
    assert sorted(r.received_quantity for r in receipts) == [Decimal(4), Decimal(6)]


@pytest.mark.parametrize(
    ("files", "error"),
    [
        ({"a": {"purchase_orders": [_po()]}, "b": {"purchase_orders": [_po()]}}, "defined twice"),
        ({"a": {"purchase_orders": [_po(lines=2)]}}, "repeats a line number"),
        (
            {"a": {"purchase_orders": [_po()], "goods_receipts": [_gr(), _gr()]}},
            "goods receipt 5000001 is defined twice",
        ),
        (
            {"a": {"purchase_orders": [_po()], "goods_receipts": [_gr(po_line=2)]}},
            "unknown PO 0100001 line 2",
        ),
        ({"a": {"goods_receipts": [_gr()]}}, "unknown PO 0100001"),
    ],
)
def test_inconsistent_fixtures_fail_at_load(
    tmp_path: Path, files: dict[str, dict[str, object]], error: str
) -> None:
    for scenario, data in files.items():
        _write(tmp_path, scenario, data)
    with pytest.raises(ErpFixtureError, match=error):
        DummyErpAdapter(tmp_path)


@pytest.mark.parametrize(
    "bad",
    [
        {"purchase_orders": [{**_po(), "po_number": "2100001"}]},
        {"purchase_orders": [{**_po(), "lines": [{**_po()["lines"][0], "ordered_quantity": "0"}]}]},  # type: ignore[index]
        {"purchase_orders": [{**_po(), "currency": "EUR"}]},
        {"unknown": []},
    ],
)
def test_fixture_schema_is_enforced(tmp_path: Path, bad: dict[str, object]) -> None:
    _write(tmp_path, "a", bad)
    with pytest.raises(ValidationError):
        DummyErpAdapter(tmp_path)
