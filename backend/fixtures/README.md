# Fixtures — dummy data for the PoC demo

Synthetic data only (public repository, DEC-028). One folder per demo scenario of
[Test Strategy §11](../../docs/05-testing/test-strategy.md#11-poc-demo-acceptance), named in lower case (`ds-01`, …).

| Path | Read by | Feature |
|---|---|---|
| `<scenario>/erp/erp.json` | Dummy ERP Adapter (purchase orders, goods receipts) | [SAPS-19](../../docs/03-features/SAPS-19-invoice-matching.md) |
| `<scenario>/invoices/<name>.json`, `manifest.json`, `schema/` | Dummy Extraction Adapter | [SAPS-18](../../docs/03-features/SAPS-18-dummy-invoice-extraction.md) |

`erp.json` format (validated when the SAPS Worker loads it, see `saps/adapters/erp/dummy_erp.py`):

```json
{
  "purchase_orders": [
    {"po_number": "0100001", "vendor_code": "V001", "currency": "USD",
     "lines": [{"po_line_number": 1, "description": "A4 copy paper, box", "ordered_quantity": "4", "unit_price": "25.00"}]}
  ],
  "goods_receipts": [
    {"gr_number": "5000001", "po_number": "0100001", "receipt_date": "2026-12-01",
     "lines": [{"po_line_number": 1, "received_quantity": "4"}]}
  ]
}
```

- Quantities and prices are strings (exact decimals). PO numbers are 7 digits starting with `0` (trade) or `1` (non-trade).
- PO and goods receipt numbers are unique across all scenarios; all scenarios are loaded together.
- Scenarios without ERP data: DS-07, DS-08 (no PO), DS-10 (unknown PO `0199999`), DS-15 (uses DS-01), DS-19.
