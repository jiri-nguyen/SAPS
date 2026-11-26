---
title: "§12 Glossary"
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["BA (TBD)", "Tech Lead (TBD)"]
last_updated: 2027-03-01
related: [MTG-20261114, MTG-20261121, MTG-20261128, DEC-012, DEC-015, DEC-033, DEC-055, SAPS-45, ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006]
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
| Approval | The Accounting Manager's decision (approve or reject) on an invoice above the approval threshold. Entity `Approval` ([data model](../data-model.md#approval)). | Phê duyệt | Sign-off |
| Approval threshold | Invoice total amount, tax included, above which Accounting Manager approval is required. Configurable by the Accounting Manager; default 300 USD ([DEC-015](../../01-requirements/decision-log.md#dec-015)). | Ngưỡng phê duyệt | Approval limit |
| Closed day | A day of the company's time zone on which its processing calendar holds new invoices ([SAPS-52](../../03-features/SAPS-52-processing-calendar.md)). | Ngày đóng xử lý | Blackout day |
| Completed | Final invoice state after the Accounting Member confirms the result: ready for posting. Posting to the ERP and payment happen outside Smart-AP-Suite ([SCP-OUT-03](../../01-requirements/scope.md#4-out-of-scope), [SCP-OUT-08](../../01-requirements/scope.md#4-out-of-scope)). | Hoàn tất | Paid, closed |
| Credit note | Vendor document that reduces an amount previously invoiced. Out of the PoC scope. | Hóa đơn điều chỉnh giảm | Credit memo |
| Delivery order | Vendor document that accompanies a delivery; its number is recorded on the goods receipt in the ERP. A trade PO invoice line carries it when the PO line has several goods receipts ([DEC-065](../../01-requirements/decision-log.md#dec-065)); in the PoC invoices did not ([DEC-034](../../01-requirements/decision-log.md#dec-034), superseded). | Phiếu giao hàng | DO, delivery note |
| Demo scenario | One end-to-end flow shown at the PoC demo, with an expected end state (DS-NN in the test strategy). | Kịch bản demo | Test case |
| Dummy data | Predefined test data that replaces a real data source in the PoC (invoice extraction results, ERP data). | Dữ liệu giả lập | Mock data, fake data |
| Dummy sample set | Invoice files with predefined extraction data used in the PoC; uploading any other file raises EX1 ([DEC-012](../../01-requirements/decision-log.md#dec-012)). | Bộ hóa đơn mẫu | Test invoices |
| Duplicate invoice | An invoice with the same vendor and invoice number as an invoice already in the system. | Hóa đơn trùng | — |
| Exception | A condition that stops automatic processing of an invoice and needs review by an Accounting Member. PoC exception types EX1–EX10: [DEC-033](../../01-requirements/decision-log.md#dec-033). | Ngoại lệ | Error, issue |
| Exception queue | Shared list of invoices in status Exception; any available Accounting Member picks one up. | Hàng đợi ngoại lệ | Inbox, task list |
| Extracted invoice | Invoice data returned by the Extraction Port for an uploaded file ([data model](../data-model.md#42-external-entities-read-through-ports-not-stored)). | Dữ liệu hóa đơn đã trích xuất | OCR result |
| Open PO | A purchase order that the ERP has not closed and that still has a line with quantity left to invoice; only open POs are matched, others raise EX4 ([DEC-067](../../01-requirements/decision-log.md#dec-067)). | PO đang mở | — |
| Purchasing info record | Agreed unit price of a material for a vendor, valid in a period; the reference price of trade PO invoice lines ([DEC-066](../../01-requirements/decision-log.md#dec-066)). | Bản ghi thông tin mua hàng | PIR |
| Received lot | The goods received under one delivery order number for a PO line; a trade PO invoice line is matched against one lot ([DEC-065](../../01-requirements/decision-log.md#dec-065)). | Lô hàng đã nhận | Lot |
| Goods Receipt | Record that ordered goods were received, used in 3-way matching. | Phiếu nhập kho | GRN, receiving report |
| GR-based invoice verification | Matching where each invoice line references a specific goods receipt; a candidate after the PoC ([SCP-OUT-13](../../01-requirements/scope.md#4-out-of-scope)). | Đối chiếu theo từng phiếu nhập kho | — |
| GR/IR clearing account | ERP account that holds goods received but not yet invoiced (and the reverse) until the invoice is posted. | Tài khoản trung gian hàng đã nhận chưa có hóa đơn | — |
| Invoice | Vendor document requesting payment, uploaded as PDF or image. | Hóa đơn | Bill |
| Invoice data extraction | Reading invoice fields from the uploaded file. In the PoC, the results come from dummy data. | Trích xuất dữ liệu hóa đơn | OCR, scanning |
| Invoice event | Audit record of a status change or user action on an invoice. Entity `InvoiceEvent`. | Sự kiện hóa đơn | Log entry |
| Invoice line | One line of an invoice; matched against its PO line. Entity `InvoiceLine`. | Dòng hóa đơn | Line item |
| Invoice type | Classification of an invoice as non-PO, non-trade PO or trade PO; it decides the matching method. | Loại hóa đơn | — |
| Matching settings | Price tolerance and approval threshold; changed only by the Accounting Manager ([DEC-015](../../01-requirements/decision-log.md#dec-015)). | Cấu hình đối chiếu | Parameters |
| Non-PO invoice | Invoice without a PO number; processed with 1-way matching. | Hóa đơn không có PO | — |
| Non-trade PO invoice | Invoice whose PO number starts with `1`; processed with 2-way matching. Usually for indirect goods or services. | Hóa đơn PO phi thương mại | Indirect PO invoice |
| Notification | In-app message to one user about an invoice that needs action. Entity `Notification`. | Thông báo | Alert |
| Partial invoicing | Invoicing part of a PO line quantity; allowed as long as the quantity does not exceed the expected quantity ([DEC-032](../../01-requirements/decision-log.md#dec-032)). | Xuất hóa đơn từng phần | Partial billing |
| PO number | Identifier of a purchase order: 7 characters, digits only. The first digit gives the PO type. | Số PO | PO ID |
| Price tolerance | Maximum allowed difference between the invoice unit price and the PO unit price on a line. Configurable by the Accounting Manager; default 0.5 USD ([DEC-015](../../01-requirements/decision-log.md#dec-015)). | Sai lệch giá cho phép | Price variance |
| On hold | Invoice state: received on a closed day and waiting to be processed; released at the end of the closed period or by an Accounting Manager ("Process now"). | Đang tạm giữ | Paused, Held |
| Processing calendar | The days on which a company does not process new invoices, set by its Accounting Manager with monthly ranges, weekdays and specific dates. Entity `ProcessingCalendarRule` ([DEC-062](../../01-requirements/decision-log.md#dec-062)). | Lịch xử lý | Schedule, Blackout calendar |
| Processing job | Unit of background work (process or re-match an invoice), sent as a message to the SAPS Message Broker and run by the SAPS Worker. Not stored as an entity. | Tác vụ xử lý | Task |
| Product Owner | The customer's single representative and decision maker for Smart-AP-Suite. | Chủ sản phẩm | Customer representative |
| Proof of Concept | First project phase: a locally run demo of the end-to-end flow, using dummy data. | Bản thử nghiệm khái niệm | Prototype, pilot |
| Purchase Order | Buyer document authorizing a purchase from a vendor. | Đơn đặt hàng | — |
| Received-not-invoiced quantity | Quantity received on goods receipts for a PO line minus the quantity already invoiced for that line. | Số lượng đã nhận chưa xuất hóa đơn | Open GR quantity |
| Rejected | Final invoice state after a rejection by the Accounting Manager or an Accounting Member ([DEC-014](../../01-requirements/decision-log.md#dec-014)). | Bị từ chối | Cancelled |
| Inbound mail | A mail read from a company mailbox; one record per mail makes the import exactly-once. Entity `InboundMail` ([SAPS-45](../../03-features/SAPS-45-mailbox-intake.md)). | Thư đến | Email record |
| Intake channel | How an invoice entered the system: `UPLOAD` by a user or `MAIL` from a company mailbox. | Kênh tiếp nhận | — |
| Mailbox | The e-mail address of a company where vendors send invoices; the mailbox sets the company of the invoices ([DEC-055](../../01-requirements/decision-log.md#dec-055)). | Hộp thư | Inbox |
| Tenant | A customer company served by Smart-AP-Suite; its data is separated from other tenants. The PoC has one tenant ([ADR-0007](../adr/0007-prepare-data-model-for-tenants.md)). | Khách hàng thuê bao | Client, customer |
| Trade PO invoice | Invoice whose PO number starts with `0`; processed with 3-way matching. Usually for goods for resale or production. | Hóa đơn PO thương mại | Direct PO invoice |
| User account | Sign-in identity of an Accounting Member or Accounting Manager. Entity `UserAccount`. | Tài khoản người dùng | Login |
| User session | A signed-in browser session, identified by the HttpOnly cookie `saps_session`. Entity `UserSession` ([ADR-0008](../adr/0008-use-session-cookies-for-authentication.md)). | Phiên đăng nhập | Login session |
| Vendor | Supplier that issues invoices; read from the ERP through the ERP Data Port. | Nhà cung cấp | Supplier |

## 12.2 Architecture Element Names
| Name | C4 type | Description | Appears in |
|---|---|---|---|
| Accounting Manager | Person | Approves invoices above the approval threshold. | L1, L2 |
| Accounting Member | Person | Uploads invoices, handles exceptions, checks the final result. | L1, L2 |
| Dummy ERP Adapter | Component | PoC implementation of the ERP Data Port; reads fixture files ([ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md)). | L3 |
| Dummy Extraction Adapter | Component | PoC implementation of the Extraction Port; reads fixture files ([ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md)). | L3 |
| IMAP Mail Adapter | Component | Implementation of the Mailbox Port for the local test mail server over IMAP ([ADR-0012](../adr/0012-read-invoice-mailboxes-through-a-mail-port.md)); a Microsoft Graph adapter for Outlook comes later. | L3 |
| ERP Data Port | Component | Interface in the SAPS API / SAPS Worker codebase that provides purchase orders, goods receipts and vendors. | L3 |
| Extraction Port | Component | Interface in the SAPS API / SAPS Worker codebase that provides extracted invoice data for an uploaded file. | L3 |
| File Storage Port | Component | Interface for storing and reading invoice files (S3 API) ([ADR-0006](../adr/0006-store-invoice-files-in-seaweedfs.md)). | L3 |
| Invoice Extraction Service | External System | OCR / AI service that extracts invoice data after the PoC; product TBD. Replaced by the Dummy Extraction Adapter in the PoC. | L1, L2 |
| Job Queue Port | Component | Interface for sending and receiving processing jobs; Dramatiq on Redis in the PoC ([ADR-0004](../adr/0004-process-invoices-in-background-worker.md)). | L3 |
| MuleSoft APIs | External System | Customer integration layer exposing SAP purchasing data (APIs or MCP Tools) after the PoC ([CON-03](02-constraints.md)). | L1, L2 |
| SAP ERP | External System | SAP ECC or SAP S/4HANA holding purchase orders, goods receipts and vendors; reached through MuleSoft APIs. | L1, L2 |
| Mailbox Port | Component | Interface in the SAPS Worker codebase to list, read and move the mails of a company mailbox ([ADR-0012](../adr/0012-read-invoice-mailboxes-through-a-mail-port.md)). | L3 |
| Keycloak | Container | Identity provider for single sign-on: realm `saps`, a group per company, realm roles Accounting Member and Accounting Manager ([ADR-0010](../adr/0010-use-one-keycloak-realm-with-company-groups.md), [ADR-0011](../adr/0011-sign-in-through-keycloak-with-a-server-side-session.md)). | L2 |
| Test Mail Server | Container | GreenMail (SMTP and IMAP) in Docker Compose that stands in for the company mailboxes in the demo and the tests ([ADR-0012](../adr/0012-read-invoice-mailboxes-through-a-mail-port.md)). | L2 |
| SAPS API | Container | Python/FastAPI backend: upload, invoice workflow, approvals, settings, notifications ([ADR-0002](../adr/0002-use-python-fastapi-and-react.md)). | L2, L3 |
| SAPS Database | Container | PostgreSQL database: invoices, matching results and workflow state ([ADR-0003](../adr/0003-use-postgresql-and-docker-compose.md)). | L2 |
| SAPS File Storage | Container | SeaweedFS object storage with S3 API for uploaded invoice files ([ADR-0006](../adr/0006-store-invoice-files-in-seaweedfs.md)). | L2 |
| SAPS Message Broker | Container | Redis: queues processing messages for the SAPS Worker ([ADR-0004](../adr/0004-process-invoices-in-background-worker.md)). | L2 |
| SAPS Web App | Container | React single-page application for Accounting Members and Accounting Managers ([ADR-0002](../adr/0002-use-python-fastapi-and-react.md)). | L2 |
| SAPS Worker | Container | Python / Dramatiq background worker: extraction, duplicate check, matching, sweeper, mail intake ([ADR-0004](../adr/0004-process-invoices-in-background-worker.md)). | L2 |
| Smart-AP-Suite | Software System | Automates the Accounts Payable flow: invoice upload, extraction, matching, exception review, approval. | L1, L2 |

## 12.3 Abbreviations
| Abbreviation | Meaning |
|---|---|
| ADR | Architecture Decision Record |
| AOF | Append-Only File (Redis persistence mode) |
| AP | Accounts Payable |
| API | Application Programming Interface |
| CSRF | Cross-Site Request Forgery |
| DO | Delivery order |
| DS | Demo scenario (test strategy) |
| E2E | End-to-end (test) |
| ECC | SAP ERP Central Component |
| ERP | Enterprise Resource Planning |
| GR | Goods Receipt |
| GR/IR | Goods Receipt / Invoice Receipt |
| MCP | Model Context Protocol |
| ORM | Object-Relational Mapping |
| PO | Purchase Order |
| PoC | Proof of Concept |
| S/4HANA | SAP S/4HANA, SAP's current ERP suite |
| S3 | Amazon Simple Storage Service; also the de-facto object storage API |
| SAPS | Smart-AP-Suite (project code) |
| SHA-256 | Secure Hash Algorithm, 256-bit; used to identify dummy sample files |
| SSO | Single Sign-On |
| USD | United States dollar |
