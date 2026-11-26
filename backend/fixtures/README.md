# Fixtures — dummy data for the PoC demo

Synthetic data only (public repository, DEC-028). One folder per demo scenario of
[Test Strategy §11](../../docs/05-testing/test-strategy.md#11-poc-demo-acceptance), named in lower case (`ds-01`, …).

| Path | Read by | Feature |
|---|---|---|
| `<scenario>/erp/erp.json` | Dummy ERP Adapter (purchase orders, goods receipts) | [SAPS-19](../../docs/03-features/SAPS-19-invoice-matching.md) |
| `<scenario>/invoices/<name>.json` | Dummy Extraction Adapter: the extraction result of one sample (source of truth) | [SAPS-18](../../docs/03-features/SAPS-18-dummy-invoice-extraction.md) |
| `<scenario>/invoices/<name>.pdf` / `.png` / `.jpg` | The file to upload in the demo; generated from the JSON | SAPS-18 |
| `<scenario>/unregistered/` | Rendered files that are **not** in the sample set (DS-07 → EX1) | SAPS-18 |
| `companies.json` | Seed, Dummy ERP Adapter: demo companies, their users and the ERP fixture files each company uses | [SAPS-42](../../docs/03-features/SAPS-42-companies-and-demo-data.md) |
| `manifest.json`, `schema/extracted-invoice.schema.json` | Generated: SHA-256 → sample, and the JSON schema of a result | SAPS-18 |

`erp.json` format (validated when the SAPS Worker loads it, see `saps/adapters/erp/dummy_erp.py`):

```json
{
  "purchase_orders": [
    {"po_number": "0100001", "vendor_code": "V001", "currency": "USD",
     "lines": [{"po_line_number": 1, "description": "A4 copy paper, box", "ordered_quantity": "4", "unit_price": "25.00",
                "material_number": "MAT-0100001-1"}]}
  ],
  "goods_receipts": [
    {"gr_number": "5000001", "do_number": "DO-5000001", "po_number": "0100001", "receipt_date": "2026-12-01",
     "lines": [{"po_line_number": 1, "received_quantity": "4"}]}
  ],
  "purchasing_info_records": [
    {"vendor_code": "V001", "material_number": "MAT-0100001-1", "unit_price": "25.00", "currency": "USD",
     "valid_from": "2026-01-01"}
  ]
}
```

- Trade POs (`0…`) need a `material_number` on every line (it selects the purchasing info record, SAPS-51); a PO may have
  `"status": "CLOSED"` (not open, DS-25). Every goods receipt has a `do_number`; the goods receipts of one PO line with the same
  DO number form one received lot. Validity periods (`valid_from`, optional `valid_to`) of one vendor and material must not
  overlap. An invoice line may carry `do_number` (required when its PO line has several lots, DS-21 to DS-23).

- Quantities and prices are strings (exact decimals). PO numbers are 7 digits starting with `0` (trade) or `1` (non-trade).
- Every demo company lists its ERP files in `companies.json` (`"erp": ["ds-*/erp/*.json"]`; company-only files may live in
  `companies/<code>/erp/`). PO and goods receipt numbers are unique within a company; each company has its own copy.
- Scenarios without ERP data: DS-07, DS-08 (no PO), DS-10 (unknown PO `0199999`), DS-15 (uses DS-01), DS-19.

## Invoice samples

- Edit a `<scenario>/invoices/<name>.json`, then run `make fixtures` in `backend/` and commit the JSON, the regenerated file,
  `manifest.json` and the schema. The worker finds a sample only by the SHA-256 of the uploaded file.
- Values must agree with the scenario's `erp/erp.json` and the default settings (tolerance 0.5 USD, threshold 300 USD).
- DS-15 is a PNG copy of DS-01's data (same vendor and invoice number, different file) for the duplicate check.
- CI checks that every file matches the manifest, every JSON is valid and usable, every scenario except DS-19 has samples,
  and each PDF shows the values of its JSON.
