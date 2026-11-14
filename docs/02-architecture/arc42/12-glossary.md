---
title: "§12 Glossary"
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["BA (TBD)", "Tech Lead (TBD)"]
last_updated: 2026-11-14
related: [MTG-20261114]
---

# §12 Glossary

## 12.1 Domain Terms
> **Assumption:** the definitions of 1-way matching, trade PO and non-trade PO follow common AP practice.
> The customer must confirm them ([MTG-20261114](../../01-requirements/meetings/2026-11-14-kickoff.md) Q13, Q14).

| Term | Definition | Vietnamese term | Synonyms (avoid) |
|---|---|---|---|
| 1-way matching | Validation of a non-PO invoice on its own data (e.g. vendor, amounts, mandatory fields), without a PO. Exact checks TBD (Q14). | Đối chiếu 1 chiều | — |
| 2-way matching | Comparison of a non-trade PO invoice with its purchase order (vendor, price, quantity, amount). | Đối chiếu 2 chiều | — |
| 3-way matching | Comparison of a trade PO invoice with its purchase order and goods receipt. | Đối chiếu 3 chiều | — |
| Accounting Member | Customer staff member who reviews exceptions, updates invoices manually and checks the final result. | Nhân viên kế toán | Accountant, AP clerk |
| Accounts Payable | The process and ledger for amounts the company owes its vendors. | Công nợ phải trả | Payables |
| Exception | A condition that stops automatic processing of an invoice and needs review by an Accounting Member. Exception types TBD (Q22). | Ngoại lệ | Error, issue |
| Goods Receipt | Record that ordered goods were received, used in 3-way matching. | Phiếu nhập kho | GRN, receiving report |
| Invoice | Vendor document requesting payment, uploaded as PDF or image. | Hóa đơn | Bill |
| Invoice data extraction | Automatic reading of invoice fields from the uploaded file. | Trích xuất dữ liệu hóa đơn | OCR, scanning |
| Invoice type | Classification of an invoice as non-PO, non-trade PO or trade PO; it decides the matching method. | Loại hóa đơn | — |
| Non-PO invoice | Invoice without a purchase order; processed with 1-way matching. | Hóa đơn không có PO | — |
| Non-trade PO invoice | Invoice for a PO for indirect goods or services (not for resale or production); processed with 2-way matching. | Hóa đơn PO phi thương mại | Indirect PO invoice |
| Purchase Order | Buyer document authorizing a purchase from a vendor. | Đơn đặt hàng | — |
| Trade PO invoice | Invoice for a PO for goods for resale or production (inventory); processed with 3-way matching. | Hóa đơn PO thương mại | Direct PO invoice |

## 12.2 Architecture Element Names
| Name | C4 type | Description | Appears in |
|---|---|---|---|
| Smart-AP-Suite | Software System | Automates the Accounts Payable flow: invoice upload, extraction, matching, exception review. | L1 |

## 12.3 Abbreviations
| Abbreviation | Meaning |
|---|---|
| AP | Accounts Payable |
| ERP | Enterprise Resource Planning |
| GR | Goods Receipt |
| PO | Purchase Order |
| SAPS | Smart-AP-Suite (project code) |
