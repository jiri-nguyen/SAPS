---
id: MTG-20261121
title: "MTG-20261121 — Requirements workshop: PoC, matching and exceptions"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2026-11-21
related: [MTG-20261114, DEC-003, DEC-004, DEC-005, DEC-006, DEC-007, DEC-008, DEC-009, DEC-010]
---

# MTG-20261121 — Requirements workshop: PoC, matching and exceptions

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Time | TBD |
| Type | requirements workshop |
| Channel | TBD |
| Facilitator | Solution Architect (our company) |
| Note taker | Solution Architect (our company) |
| Recording / slides | none |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Customer representative | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
All items come from [MTG-20261114](2026-11-14-kickoff.md).

| From | Item | Update / new status |
|---|---|---|
| MTG-20261114 #A1 | Send sample invoices | Closed — not needed: the PoC uses dummy extraction data (R2) |
| MTG-20261114 #A2 | As-is process, ERP landscape, key contacts | As-is process and ERP answered (R4, R5). Contacts: still open; customer sends later |
| MTG-20261114 #A3 | Send kickoff summary | Done 2026-11-14 |
| MTG-20261114 #A4 | Prepare workshop agenda | Done |
| MTG-20261114 #Q1 | Organization and legal entities | Still open; customer sends later. Not needed for the PoC design |
| MTG-20261114 #Q2 | As-is process and pain points | Answered → R5 |
| MTG-20261114 #Q3 | Business objectives and success measures | Still open; PoC success criterion answered → R1 |
| MTG-20261114 #Q4 | User roles and counts | Answered for the PoC → R7. User counts not given |
| MTG-20261114 #Q5 | Invoices per month per type | Still open (not discussed) |
| MTG-20261114 #Q6 | Peak periods | Still open (not discussed) |
| MTG-20261114 #Q7 | Pages, file size, image formats | Deferred: out of PoC scope (R24) |
| MTG-20261114 #Q8 | Invoice languages | Deferred: extraction is dummy in the PoC (R24) |
| MTG-20261114 #Q9 | E-invoice XML, other intake channels | Still open (not discussed) |
| MTG-20261114 #Q10 | Fields to extract | Deferred: extraction is dummy in the PoC (R24) |
| MTG-20261114 #Q11 | Extraction accuracy, low-confidence fields | Deferred: extraction is dummy in the PoC (R24) |
| MTG-20261114 #Q12 | Unreadable scans, multi-invoice files | Deferred: extraction is dummy in the PoC (R24) |
| MTG-20261114 #Q13 | How the invoice type is decided | Answered → R8 |
| MTG-20261114 #Q14 | 1-way matching checks for non-PO | Answered for the PoC → R9 |
| MTG-20261114 #Q15 | Header or line-level matching | Answered → R10 |
| MTG-20261114 #Q16 | Tolerances | Answered → R11 |
| MTG-20261114 #Q17 | Partial deliveries, multi-PO/GR, credit notes | Answered: SA proposal accepted → R13 |
| MTG-20261114 #Q18 | Duplicate detection, tax/VAT checks | Answered → R14, R15 |
| MTG-20261114 #Q19 | ERP and integration method | Answered → R3, R4 |
| MTG-20261114 #Q20 | What happens with a matched invoice | Answered for the PoC → R16 |
| MTG-20261114 #Q21 | Approval workflow, payment | Answered → R17, R18 |
| MTG-20261114 #Q22 | Exception types | Answered → R19 |
| MTG-20261114 #Q23 | Exception assignment, SLA, escalation | Still open (not discussed) → see Q6 below |
| MTG-20261114 #Q24 | Notification channels | Answered → R20 |
| MTG-20261114 #Q25 | Re-run matching after manual update | Answered → R21 |
| MTG-20261114 #Q26 | Go-live, phases, budget, UAT, sign-off | Partly answered: PoC first, 3 months → R1. Go-live, budget, UAT and sign-off owner still open |
| MTG-20261114 #Q27 | Cloud provider, account ownership | Partly answered: PoC runs locally → R1. Cloud for later phases still open |
| MTG-20261114 #Q28 | Data residency, cloud AI/OCR services | Deferred: extraction is dummy in the PoC (R24) |
| MTG-20261114 #Q29 | Sign-in and UI language | Answered for the PoC → R22, R23 |
| MTG-20261114 #Q30 | Retention of invoice files and audit trail | Still open (not discussed) |
| MTG-20261114 #Q31 | Operating hours and availability | Still open (not discussed) |

## 4. Agenda
1. Follow-up from the kickoff
2. As-is AP process and users
3. Invoice types and matching rules
4. ERP and integration
5. PoC approach, exceptions and notifications

## 5. Discussion
### 5.1 Follow-up from the kickoff
- Attendee names, organization and contacts are not needed for the design; the customer sends them later.

### 5.2 As-is AP process and users
- Today every step of invoice processing is manual.
- Main pain points: processing takes a long time when invoice volume is high, and human errors sometimes reduce accuracy.
- Business objectives and success measures are not defined yet.
- PoC users: the Accounting Member uploads invoices, handles exceptions and reviews the final result.
  An Accounting Manager approves invoices above the approval threshold.

### 5.3 Invoice types and matching rules
- The invoice type comes from the PO number on the invoice: 7 characters, digits only.
  Prefix `0` = trade PO, prefix `1` = non-trade PO, no PO number = non-PO invoice.
  Any other prefix is an exception and goes back to the Accounting Member.
- Non-PO invoices go directly to the Accounting Member for manual review and update in the PoC.
  Automated checks for non-PO invoices come later.
- 2-way and 3-way matching compare line by line.
- Price tolerance: the invoice unit price may differ from the PO unit price by at most 0.5 USD per line.
  The same tolerance applies to all vendors and categories. Quantity must match exactly.
- The PoC handles USD only.
- The customer accepted the SA proposal for partial deliveries and multi-document invoices (R13).
- Duplicate invoices are detected (same vendor and invoice number) and become exceptions. No tax/VAT checks.

### 5.4 ERP and integration
- The PoC uses dummy data for the minimum ERP data the flow needs (POs, goods receipts, vendors).
- Later phases get the data from SAP ECC or SAP S/4HANA through MuleSoft APIs or MuleSoft MCP Tools.
- In the PoC, the matching result is only displayed. Nothing is posted or exported.
- Invoices with a total amount above 300 USD, tax included, need Accounting Manager approval.
- Payment is out of the project scope.

### 5.5 PoC approach, exceptions and notifications
- The customer wants a PoC first. Duration: 3 months from 2026-11-21. It runs locally.
- PoC focus: the automated business flow. Invoice data extraction uses dummy data.
- PoC success criterion: an end-to-end demo of the flow for different cases, including exception cases.
- The exception types proposed by the SA are enough for the PoC (R19).
- Notifications are shown in the application only.
- When an Accounting Member changes a field used in matching, the system re-runs matching.
- The PoC uses simple user accounts. The UI language is English.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | Deliver a PoC first: 3 months from 2026-11-21, runs locally, success = end-to-end demo including exception cases | Customer representative (Customer) | [DEC-003](../decision-log.md#dec-003) |
| D2 | The PoC uses dummy data for invoice extraction and for ERP data | Customer representative (Customer) | [DEC-004](../decision-log.md#dec-004) |
| D3 | Invoice type is derived from the PO number (7 digits; `0` trade, `1` non-trade, none non-PO, other prefix exception) | Customer representative (Customer) | [DEC-005](../decision-log.md#dec-005) |
| D4 | Matching rules: line level; unit price tolerance 0.5 USD per line; exact quantity; USD only; non-PO invoices go to manual review | Customer representative (Customer) | [DEC-006](../decision-log.md#dec-006) |
| D5 | Handling of partial deliveries, multiple goods receipts, multi-PO and mixed invoices as proposed by the SA; credit notes out of the PoC | Customer representative (Customer) | [DEC-007](../decision-log.md#dec-007) |
| D6 | Duplicate detection by vendor + invoice number → exception; no tax/VAT checks | Customer representative (Customer) | [DEC-008](../decision-log.md#dec-008) |
| D7 | Invoices with total amount (tax included) above 300 USD need Accounting Manager approval | Customer representative (Customer) | [DEC-009](../decision-log.md#dec-009) |
| D8 | Re-run matching when a manual update changes a field used in matching | Customer representative (Customer) | [DEC-010](../decision-log.md#dec-010) |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Deliver a PoC first: 3 months from 2026-11-21; runs locally; success = end-to-end demo for different cases including exceptions | Scope | [DEC-003](../decision-log.md#dec-003); [SCP-IN-10](../scope.md), [SCP-IN-11](../scope.md); scope.md §2 BO2; arc42 §2 [CON-01](../../02-architecture/arc42/02-constraints.md), [CON-02](../../02-architecture/arc42/02-constraints.md) | logged |
| R2 | PoC focus is the automated business flow; invoice data extraction uses dummy data | Scope | [DEC-004](../decision-log.md#dec-004); change [SCP-IN-02](../scope.md); [SCP-OUT-01](../scope.md) | logged |
| R3 | The minimum ERP data needed by the flow (POs, goods receipts, vendors) is dummy data in the PoC | Scope | [DEC-004](../decision-log.md#dec-004); [SCP-IN-09](../scope.md) | logged |
| R4 | Later phases get ERP data from SAP ECC or SAP S/4HANA through MuleSoft APIs or MuleSoft MCP Tools | Constraint | [SCP-OUT-02](../scope.md); arc42 §2 [CON-03](../../02-architecture/arc42/02-constraints.md); [ADR-0001](../../02-architecture/adr/0001-isolate-extraction-and-erp-behind-ports.md) | logged |
| R5 | As-is: all steps manual; pain points are long processing time at high volume and human errors | Scope | scope.md §1 Background | logged |
| R6 | Business objectives and success measures are not defined yet | Scope | scope.md §2 BO1 stays TBD | logged |
| R7 | PoC roles: Accounting Member (uploads, handles exceptions, reviews result); Accounting Manager (approves) | Functional | [SCP-IN-12](../scope.md); glossary | logged |
| R8 | PO number: 7 characters, digits only; prefix `0` trade PO, `1` non-trade PO; no PO number = non-PO; other prefix = exception to Accounting Member | Functional | [DEC-005](../decision-log.md#dec-005); [SCP-IN-03](../scope.md) | logged |
| R9 | PoC: non-PO invoices go to the Accounting Member for manual review and update; automated checks come later | Functional | [DEC-006](../decision-log.md#dec-006); [SCP-OUT-07](../scope.md) | logged |
| R10 | 2-way and 3-way matching compare line by line | Functional | [DEC-006](../decision-log.md#dec-006) | logged |
| R11 | Unit price tolerance 0.5 USD per line, for all vendors and categories; quantity must match exactly | Functional | [DEC-006](../decision-log.md#dec-006) | logged |
| R12 | The PoC handles USD only | Scope | [DEC-006](../decision-log.md#dec-006); [SCP-OUT-06](../scope.md) | logged |
| R13 | Partial delivery: invoice quantity compared with received-not-invoiced quantity; several goods receipts summed per PO line; each invoice line references its own PO line; mixed trade and non-trade POs on one invoice = exception; 2-way compares with PO quantity not yet invoiced; credit notes out of the PoC | Functional | [DEC-007](../decision-log.md#dec-007); [SCP-OUT-05](../scope.md) | logged |
| R14 | Duplicate invoice = same vendor + invoice number; it becomes an exception (not auto-rejected) | Functional | [DEC-008](../decision-log.md#dec-008); [SCP-IN-07](../scope.md) | logged |
| R15 | No tax/VAT checks | Scope | [DEC-008](../decision-log.md#dec-008); [SCP-OUT-04](../scope.md) | logged |
| R16 | PoC: the result is only displayed; no posting to the ERP, no export | Scope | change [SCP-IN-05](../scope.md); [SCP-OUT-08](../scope.md) | logged |
| R17 | Invoices with a total amount above 300 USD, tax included, need Accounting Manager approval | Functional | [DEC-009](../decision-log.md#dec-009); [SCP-IN-06](../scope.md) | logged |
| R18 | Payment is out of the project scope | Scope | [SCP-OUT-03](../scope.md) | logged |
| R19 | Exception types for the PoC: EX1 invoice unreadable; EX2 non-PO invoice (manual review); EX3 invalid PO number; EX4 PO not found; EX5 mixed trade and non-trade POs; EX6 unit price outside tolerance; EX7 quantity mismatch; EX8 missing goods receipt; EX9 duplicate invoice | Functional | change [SCP-IN-04](../scope.md); feature spec (Linear key TBD) | logged |
| R20 | Notifications are shown in the application only | Functional | [SCP-IN-08](../scope.md) | logged |
| R21 | If a manual update changes a field used in matching, the system re-runs matching | Functional | [DEC-010](../decision-log.md#dec-010); change [SCP-IN-04](../scope.md) | logged |
| R22 | PoC sign-in uses simple user accounts (no SSO) | NFR | [NFR-SEC-001](../nfr.md#nfr-sec-001); [SCP-OUT-10](../scope.md) | logged |
| R23 | UI language is English | NFR | [NFR-USAB-001](../nfr.md#nfr-usab-001) | logged |
| R24 | Extraction details (file formats, pages, languages, fields, accuracy, AI/OCR services) are not relevant to the PoC | Scope | MTG-20261114 Q7, Q8, Q10–Q12, Q28 deferred | logged |
| R25 | The PoC runs locally; cloud deployment comes later | Scope | [SCP-IN-10](../scope.md); [SCP-OUT-09](../scope.md) | logged |

> **Note on R19:** the SA proposed the list in the meeting; "no PO" and "non-PO invoice" were merged into EX2,
> and EX3 / EX5 were added from C4 and the R13 proposal. The customer must confirm the merged list (Q8).

### 7.1 Conflicts with existing items
| # | Existing item | Conflict | Proposed resolution |
|---|---|---|---|
| K1 | [SCP-IN-02](../scope.md#31-functional-capabilities) "The system automatically extracts the information on the invoice" | The PoC uses dummy extraction data (R2) | Change SCP-IN-02 to dummy extraction in the PoC; add SCP-OUT-01 for real extraction |
| K2 | [SCP-IN-05](../scope.md#31-functional-capabilities) and kickoff R6: one role only | A second role, Accounting Manager, approves invoices above 300 USD (R17) | Add SCP-IN-06 and SCP-IN-12; order of approval and final review is open (Q2) |
| K3 | [Glossary](../../02-architecture/arc42/12-glossary.md) "1-way matching": validation on own data | In the PoC, non-PO invoices go straight to manual review (R9) | Glossary updated with the PoC behavior |
| K4 | [scope.md AS1](../scope.md#5-assumptions): manual upload is the only intake channel | Still valid, but how an upload maps to dummy extraction data is unclear | Open question Q1 |

### 7.2 ADR needs
| # | Need | Driver |
|---|---|---|
| [ADR-0001](../../02-architecture/adr/0001-isolate-extraction-and-erp-behind-ports.md) | Put invoice extraction and ERP data access behind replaceable interfaces, so dummy data can later be swapped for a real extraction service and MuleSoft APIs / MCP Tools | R2, R3, R4 |
| [ADR-0002](../../02-architecture/adr/0002-use-python-fastapi-and-react.md) | PoC technology stack (database and local runtime: follow-up ADR) | R1, R25 |

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Send attendee list, organization and key contacts (carried over from MTG-20261114 A2) | Customer representative (Customer) | 2026-11-28 | open |
| A2 | Draft the end-to-end PoC flow (invoice states, approval, final review) as a Mermaid diagram for review | Solution Architect (our company) | 2026-11-27 | done → [§6 Runtime View](../../02-architecture/arc42/06-runtime-view.md) |
| A3 | Send the meeting summary and proposed decisions to the customer | Solution Architect (our company) | 2026-11-21 | open |
| A4 | Prepare ADR-0001 and ADR-0002 drafts | Solution Architect (our company) | 2026-11-28 | done → [§9 Architecture Decisions](../../02-architecture/arc42/09-architecture-decisions.md) |

## 9. Open Questions
All questions are asked to the Customer representative (Customer), due 2026-11-28.

| # | Question | Asked to | Due | Answer / status |
|---|---|---|---|---|
| Q1 | How does an upload work with dummy extraction? Proposal: a set of dummy invoices, each with a PDF/image and predefined extracted data; uploading one of these files loads its data. | Customer representative (Customer) | 2026-11-28 | open |
| Q2 | Order of steps after matching? Proposal: matching passed → if total > 300 USD, Accounting Manager approval → Accounting Member final review → completed. | Customer representative (Customer) | 2026-11-28 | open |
| Q3 | What happens when the Accounting Manager rejects an invoice, or the Accounting Member rejects it at final review? | Customer representative (Customer) | 2026-11-28 | open |
| Q4 | Does the 300 USD approval rule apply to all invoice types, including non-PO invoices? | Customer representative (Customer) | 2026-11-28 | open |
| Q5 | Should the 0.5 USD tolerance and the 300 USD threshold be configurable settings (proposal: yes, with these defaults)? | Customer representative (Customer) | 2026-11-28 | open |
| Q6 | With several Accounting Members, how are exceptions assigned? Proposal: one shared queue; any Accounting Member can pick an item. | Customer representative (Customer) | 2026-11-28 | open |
| Q7 | Exact PoC end date and demo date? 3 months from 2026-11-21 is 2027-02-21. Any interim milestones or demos? | Customer representative (Customer) | 2026-11-28 | open |
| Q8 | Do you confirm the merged exception list EX1–EX9 (R19)? | Customer representative (Customer) | 2026-11-28 | open |

## 10. Next Meeting
- Date: 2026-11-28, time TBD
- Planned topics: end-to-end PoC flow review (A2), open questions Q1–Q8, ADR drafts.

## 11. Customer Confirmation
| Field | Value |
|---|---|
| Summary sent on | 2026-11-21 by Solution Architect (our company) |
| Confirmed on | pending |
| Reference | email "[Smart-AP-Suite] Workshop 2026-11-21: PoC scope and proposed decisions" |
| Corrections received | none |
