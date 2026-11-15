---
title: "§12 Glossary"
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["BA (TBD)", "Tech Lead (TBD)"]
last_updated: 2026-11-21
related: [MTG-20261114, MTG-20261121, ADR-0001, ADR-0002, ADR-0003]
---

# §12 Glossary

## 12.1 Domain Terms
> **Assumption:** the business meaning of trade PO and non-trade PO (goods for resale or production vs. indirect
> goods and services) follows common AP practice. The customer must confirm it. How the system tells them apart is
> stated by the customer ([MTG-20261121](../../01-requirements/meetings/2026-11-21-requirements-workshop.md) R8).

| Term | Definition | Vietnamese term | Synonyms (avoid) |
|---|---|---|---|
| 1-way matching | Validation of a non-PO invoice without a PO. In the PoC there are no automated checks: the invoice goes directly to an Accounting Member for manual review. | Đối chiếu 1 chiều | — |
| 2-way matching | Line-level comparison of a non-trade PO invoice with its purchase order: unit price within the price tolerance, quantity not above the PO quantity not yet invoiced. | Đối chiếu 2 chiều | — |
| 3-way matching | Line-level comparison of a trade PO invoice with its purchase order and goods receipts: unit price within the price tolerance, quantity not above the received-not-invoiced quantity. | Đối chiếu 3 chiều | — |
| Accounting Manager | Customer staff member who approves invoices whose total amount is above the approval threshold. | Kế toán trưởng / Trưởng phòng kế toán | Approver, manager |
| Accounting Member | Customer staff member who uploads invoices, reviews and updates exceptions manually, and checks the final result. | Nhân viên kế toán | Accountant, AP clerk |
| Accounts Payable | The process and ledger for amounts the company owes its vendors. | Công nợ phải trả | Payables |
| Approval threshold | Invoice total amount, tax included, above which Accounting Manager approval is required. PoC value: 300 USD. | Ngưỡng phê duyệt | Approval limit |
| Credit note | Vendor document that reduces an amount previously invoiced. Out of the PoC scope. | Hóa đơn điều chỉnh giảm | Credit memo |
| Duplicate invoice | An invoice with the same vendor and invoice number as an invoice already in the system. | Hóa đơn trùng | — |
| Dummy data | Predefined test data that replaces a real data source in the PoC (invoice extraction results, ERP data). | Dữ liệu giả lập | Mock data, fake data |
| Exception | A condition that stops automatic processing of an invoice and needs review by an Accounting Member. PoC exception types: [MTG-20261121](../../01-requirements/meetings/2026-11-21-requirements-workshop.md) R19. | Ngoại lệ | Error, issue |
| Goods Receipt | Record that ordered goods were received, used in 3-way matching. | Phiếu nhập kho | GRN, receiving report |
| Invoice | Vendor document requesting payment, uploaded as PDF or image. | Hóa đơn | Bill |
| Invoice data extraction | Reading invoice fields from the uploaded file. In the PoC, the results come from dummy data. | Trích xuất dữ liệu hóa đơn | OCR, scanning |
| Invoice type | Classification of an invoice as non-PO, non-trade PO or trade PO; it decides the matching method. | Loại hóa đơn | — |
| Non-PO invoice | Invoice without a PO number; processed with 1-way matching. | Hóa đơn không có PO | — |
| Non-trade PO invoice | Invoice whose PO number starts with `1`; processed with 2-way matching. Usually for indirect goods or services. | Hóa đơn PO phi thương mại | Indirect PO invoice |
| PO number | Identifier of a purchase order: 7 characters, digits only. The first digit gives the PO type. | Số PO | PO ID |
| Price tolerance | Maximum allowed difference between the invoice unit price and the PO unit price on a line. PoC value: 0.5 USD. | Sai lệch giá cho phép | Price variance |
| Proof of Concept | First project phase: a locally run demo of the end-to-end flow, using dummy data. | Bản thử nghiệm khái niệm | Prototype, pilot |
| Purchase Order | Buyer document authorizing a purchase from a vendor. | Đơn đặt hàng | — |
| Received-not-invoiced quantity | Quantity received on goods receipts for a PO line minus the quantity already invoiced for that line. | Số lượng đã nhận chưa xuất hóa đơn | Open GR quantity |
| Trade PO invoice | Invoice whose PO number starts with `0`; processed with 3-way matching. Usually for goods for resale or production. | Hóa đơn PO thương mại | Direct PO invoice |

## 12.2 Architecture Element Names
| Name | C4 type | Description | Appears in |
|---|---|---|---|
| Accounting Manager | Person | Approves invoices above the approval threshold. | L1, L2 |
| Accounting Member | Person | Uploads invoices, handles exceptions, checks the final result. | L1, L2 |
| Dummy ERP Adapter | Component | PoC implementation of the ERP Data Port; reads fixture files ([ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md)). | L3 |
| Dummy Extraction Adapter | Component | PoC implementation of the Extraction Port; reads fixture files ([ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md)). | L3 |
| ERP Data Port | Component | Interface in the SAPS API that provides purchase orders, goods receipts and vendors. | L3 |
| Extraction Port | Component | Interface in the SAPS API that provides extracted invoice data for an uploaded file. | L3 |
| SAPS API | Container | Python/FastAPI backend: upload, extraction, matching, workflow, notifications ([ADR-0002](../adr/0002-use-python-fastapi-and-react.md)). | L2, L3 |
| SAPS Database | Container | PostgreSQL database: invoices, matching results and workflow state ([ADR-0003](../adr/0003-use-postgresql-and-docker-compose.md)). | L2 |
| SAPS Web App | Container | React single-page application for Accounting Members and Accounting Managers ([ADR-0002](../adr/0002-use-python-fastapi-and-react.md)). | L2 |
| Smart-AP-Suite | Software System | Automates the Accounts Payable flow: invoice upload, extraction, matching, exception review, approval. | L1 |

## 12.3 Abbreviations
| Abbreviation | Meaning |
|---|---|
| ADR | Architecture Decision Record |
| AP | Accounts Payable |
| API | Application Programming Interface |
| ECC | SAP ERP Central Component |
| ERP | Enterprise Resource Planning |
| GR | Goods Receipt |
| MCP | Model Context Protocol |
| PO | Purchase Order |
| PoC | Proof of Concept |
| S/4HANA | SAP S/4HANA, SAP's current ERP suite |
| SAPS | Smart-AP-Suite (project code) |
| SSO | Single Sign-On |
| USD | United States dollar |
