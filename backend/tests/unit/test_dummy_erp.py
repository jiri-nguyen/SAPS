import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from saps.adapters.erp.dummy_erp import DummyErpAdapter, ErpFixtureError

FIXTURES = Path(__file__).parents[2] / "fixtures"


def _company(code: str, erp: list[str]) -> dict[str, object]:
    domain = f"{code}.example.com"
    return {
        "code": code,
        "name": f"Company {code}",
        "email_domain": domain,
        "keycloak_group": f"/companies/{code}",
        "mailbox_address": f"ap@{domain}",
        "time_zone": "UTC",
        "users": [{"username": f"m@{domain}", "display_name": "M", "role": "ACCOUNTING_MEMBER"}],
        "erp": erp,
    }


def _companies(root: Path, *companies: dict[str, object]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "companies.json").write_text(
        json.dumps({"companies": list(companies) or [_company("aa", ["*/erp/*.json"])]})
    )


def _write(root: Path, scenario: str, data: dict[str, object]) -> None:
    folder = root / scenario / "erp"
    folder.mkdir(parents=True)
    (folder / "erp.json").write_text(json.dumps(data))
    if not (root / "companies.json").exists():
        _companies(root)


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
    assert [adapter.purchase_order_count(code) for code in ("vn", "sg", "my")] == [17, 17, 17]  # SAPS-42 Q4


async def test_reads_orders_and_receipts_by_po_number() -> None:
    adapter = DummyErpAdapter(FIXTURES)
    orders = await adapter.get_purchase_orders("vn", ["0100004", "0199999"])
    assert list(orders) == ["0100004"]
    assert orders["0100004"].lines[1].unit_price == Decimal("15.00")
    receipts = await adapter.get_goods_receipt_lines("vn", ["0100004"])
    assert sorted(r.received_quantity for r in receipts) == [Decimal(4), Decimal(6)]


async def test_each_company_reads_its_own_files(tmp_path: Path) -> None:  # SAPS-42 BR-03
    _write(tmp_path, "shared", {"purchase_orders": [_po("0100001")]})
    _write(tmp_path, "only-b", {"purchase_orders": [_po("0100002")]})
    _companies(
        tmp_path,
        _company("aa", ["shared/erp/*.json"]),
        _company("bb", ["shared/erp/*.json", "only-b/erp/*.json"]),
    )
    adapter = DummyErpAdapter(tmp_path)
    assert list(await adapter.get_purchase_orders("aa", ["0100001", "0100002"])) == ["0100001"]
    assert list(await adapter.get_purchase_orders("bb", ["0100001", "0100002"])) == ["0100001", "0100002"]


async def test_an_unknown_company_gets_no_data_and_is_logged_once(
    caplog: pytest.LogCaptureFixture,
) -> None:  # EC-03
    caplog.set_level("WARNING", logger="saps.worker.erp")
    adapter = DummyErpAdapter(FIXTURES)
    assert await adapter.get_purchase_orders("zz", ["0100004"]) == {}
    assert await adapter.get_goods_receipt_lines("zz", ["0100004"]) == []
    assert [r.getMessage() for r in caplog.records] == ["erp_company_unknown"]


def test_a_pattern_without_files_fails_at_load(tmp_path: Path) -> None:  # EC-02
    _companies(tmp_path, _company("aa", ["missing/erp/*.json"]))
    with pytest.raises(ErpFixtureError, match="matches no ERP file"):
        DummyErpAdapter(tmp_path)


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
