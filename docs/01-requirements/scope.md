---
title: Scope Statement
version: "0.11"           # 1.0 = first customer-approved version
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)", "Product Owner (Customer)"]
last_updated: 2027-03-01
related: [MTG-20261114, MTG-20261121, MTG-20261128, DEC-003, DEC-004, DEC-011, DEC-012, DEC-013, DEC-014, DEC-015, DEC-016, DEC-017, DEC-018, DEC-020, DEC-021, DEC-022, DEC-023, DEC-024, DEC-025, DEC-026, DEC-031, DEC-032, DEC-033, DEC-034, DEC-039, DEC-041, DEC-047, DEC-048, DEC-049, DEC-050, DEC-051, DEC-052, DEC-053, DEC-054, DEC-055, DEC-056, DEC-057, DEC-062, DEC-063, DEC-064, DEC-065, DEC-066, DEC-067, DEC-068, DEC-070, MTG-20270301, MTG-20270301-2, MTG-20270301-4, MTG-20270301-9, MTG-20270301-11]
---

# Scope Statement

## 1. Background
The customer wants to automate its Accounts Payable (AP) flow with a system named Smart-AP-Suite.
Today every step of invoice processing is manual. When invoice volume is high, processing takes a long time,
and human errors sometimes reduce accuracy.
Smart-AP-Suite receives invoices, extracts their data, matches them according to their invoice type,
routes exceptions and approvals, and posts the result to the ERP (Phase 2; in the PoC it presented the final result to an Accounting Member).

**This version covers the Proof of Concept (PoC) phase** ([DEC-003](decision-log.md#dec-003), accepted: [DEC-047](decision-log.md#dec-047))
**and Phase 2** ([DEC-048](decision-log.md#dec-048) `[CR]`, [DEC-051](decision-log.md#dec-051)): SCP-IN-01 … -14 are the PoC scope, SCP-IN-15 … -23 are new in Phase 2. Terms are defined in the [§12 Glossary](../02-architecture/arc42/12-glossary.md).
Backlog items live in the Linear project
[Smart-AP-Suite](https://linear.app/jiringuyen/project/smart-ap-suite-766faab061af/overview).

## 2. Business Objectives
| # | Objective | Success measure |
|---|---|---|
| BO1 | Automate the AP flow and grow into an AP system serving many customer companies on AWS ([DEC-026](decision-log.md#dec-026)) | TBD |
| BO2 | Prove the automated AP business flow in a PoC | All flows run successfully in the demo on 2027-02-22: every scenario in the demo scenario catalog, i.e. happy paths per invoice type and one scenario per exception type EX1–EX10 ([DEC-033](decision-log.md#dec-033), [DEC-020](decision-log.md#dec-020), [DEC-017](decision-log.md#dec-017)) — **met** ([DEC-047](decision-log.md#dec-047)) |
| BO3 | Extend the AP system for several customer companies in Phase 2 ([DEC-048](decision-log.md#dec-048), [DEC-051](decision-log.md#dec-051)) | The new features run in the Phase 2 demo for about 3 companies; demo on 2027-08-30 ([DEC-052](decision-log.md#dec-052)) |

## 3. In Scope

### 3.1 Functional Capabilities
All PoC items are priority Must (AS2, confirmed). Priorities of Phase 2 items follow [DEC-050](decision-log.md#dec-050).

| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-01 | Invoice upload | An Accounting Member uploads an invoice (PDF or image) to the system manually | Must | [SAPS-17](https://linear.app/jiringuyen/issue/SAPS-17) | [MTG-20261114](meetings/2026-11-14-kickoff.md) R1 |
| SCP-IN-02 | Invoice data extraction | Dummy extraction in the PoC: uploading a file from the dummy sample set loads its predefined data; any other file raises EX1 | Must | [SAPS-18](https://linear.app/jiringuyen/issue/SAPS-18) | [DEC-004](decision-log.md#dec-004), [DEC-012](decision-log.md#dec-012) |
| SCP-IN-03 | Invoice matching | Invoice type derived from the PO number; line-level 2-way / 3-way matching with price tolerance; non-PO invoices to manual review. Phase 2: trade PO invoices are matched per received lot (PO or DO number) and their unit price is checked against the purchasing info record | Must | [SAPS-19](https://linear.app/jiringuyen/issue/SAPS-19) | [DEC-005](decision-log.md#dec-005), [DEC-006](decision-log.md#dec-006), [DEC-007](decision-log.md#dec-007), [DEC-031](decision-log.md#dec-031), [DEC-032](decision-log.md#dec-032), [DEC-034](decision-log.md#dec-034); [DEC-065](decision-log.md#dec-065), [DEC-066](decision-log.md#dec-066) |
| SCP-IN-04 | Exception handling | On an exception (EX1–EX13) the flow pauses; the invoice goes to a shared queue; an Accounting Member reviews and updates it; matching re-runs when a matching field changes. Phase 2: when the last exception is closed, the workflow (without extraction) runs again and the invoice is posted if it passes | Must | [SAPS-20](https://linear.app/jiringuyen/issue/SAPS-20) | [DEC-033](decision-log.md#dec-033), [DEC-010](decision-log.md#dec-010), [DEC-016](decision-log.md#dec-016); [DEC-063](decision-log.md#dec-063), [DEC-068](decision-log.md#dec-068) |
| SCP-IN-05 | Final result review | **withdrawn** in Phase 2: invoices are posted automatically, no final review. In the PoC: at the end of the flow, an Accounting Member checks and confirms the result; the result is displayed in the application only | Must | [SAPS-21](https://linear.app/jiringuyen/issue/SAPS-21) | [MTG-20261114](meetings/2026-11-14-kickoff.md) R6; [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R16; [DEC-063](decision-log.md#dec-063) |
| SCP-IN-06 | Invoice approval | Invoices of any type with a total amount (tax included) above the approval threshold are approved by an Accounting Manager, before the final review (PoC) or before posting (Phase 2) | Must | [SAPS-22](https://linear.app/jiringuyen/issue/SAPS-22) | [DEC-009](decision-log.md#dec-009), [DEC-013](decision-log.md#dec-013); [DEC-063](decision-log.md#dec-063) |
| SCP-IN-07 | Duplicate invoice detection | An invoice with the same vendor and invoice number as an existing one becomes an exception | Must | [SAPS-23](https://linear.app/jiringuyen/issue/SAPS-23) | [DEC-008](decision-log.md#dec-008) |
| SCP-IN-08 | In-app notifications | In-app notifications by type: exceptions to Accounting Members, approvals to the Accounting Manager; final reviews to Accounting Members in the PoC only | Must | [SAPS-24](https://linear.app/jiringuyen/issue/SAPS-24) | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R20; [DEC-021](decision-log.md#dec-021); [DEC-063](decision-log.md#dec-063) |
| SCP-IN-12 | User roles | Two roles: Accounting Member and Accounting Manager; sign-in with simple user accounts | Must | [SAPS-27](https://linear.app/jiringuyen/issue/SAPS-27) | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R7, R22 |
| SCP-IN-13 | Matching settings | The Accounting Manager can change the price tolerance (default 0.5 USD) and the approval threshold (default 300 USD) | Must | [SAPS-28](https://linear.app/jiringuyen/issue/SAPS-28) | [DEC-015](decision-log.md#dec-015) |
| SCP-IN-14 | Invoice rejection | The Accounting Manager (at approval) or an Accounting Member (during exception handling; at final review in the PoC only) can reject an invoice; Rejected is a final state | Must | [SAPS-29](https://linear.app/jiringuyen/issue/SAPS-29) | [DEC-014](decision-log.md#dec-014); [DEC-063](decision-log.md#dec-063) |
| SCP-IN-16 | Automated checks for non-PO invoices | Phase 2 (from SCP-OUT-07); the checks are to be defined | TBD ([MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) Q7) | [SAPS-50](https://linear.app/jiringuyen/issue/SAPS-50) | [DEC-048](decision-log.md#dec-048) |
| SCP-IN-18 | Single Sign-On | Phase 2 (from SCP-OUT-10): users sign in through Keycloak ([DEC-049](decision-log.md#dec-049)); replaces the simple user accounts of SCP-IN-12; users and roles are managed in the Keycloak admin console, no user management screens ([DEC-054](decision-log.md#dec-054)) | Must; first ([DEC-050](decision-log.md#dec-050)) | [SAPS-39](https://linear.app/jiringuyen/issue/SAPS-39), [SAPS-43](https://linear.app/jiringuyen/issue/SAPS-43), [SAPS-44](https://linear.app/jiringuyen/issue/SAPS-44) | [DEC-048](decision-log.md#dec-048), [DEC-049](decision-log.md#dec-049) |
| SCP-IN-19 | Invoice intake from a mailbox | Phase 2 (from SCP-OUT-11): one mailbox per company (Outlook later); PDF, PNG and JPG attachments enter the flow like an upload, one attachment = one invoice; mails without a valid attachment are skipped and logged ([DEC-055](decision-log.md#dec-055)) | Must; first ([DEC-050](decision-log.md#dec-050)) | [SAPS-40](https://linear.app/jiringuyen/issue/SAPS-40), [SAPS-45](https://linear.app/jiringuyen/issue/SAPS-45) | [DEC-048](decision-log.md#dec-048) |
| SCP-IN-20 | Multi-tenancy | Phase 2 (from SCP-OUT-12): the system serves several customer companies, about 3 in the Phase 2 demo; a user belongs to one company; matching settings, vendors and ERP data per company ([DEC-056](decision-log.md#dec-056)) | Must; first ([DEC-050](decision-log.md#dec-050)) | [SAPS-41](https://linear.app/jiringuyen/issue/SAPS-41), [SAPS-42](https://linear.app/jiringuyen/issue/SAPS-42) | [DEC-048](decision-log.md#dec-048) |
| SCP-IN-21 | GR-based invoice verification | Phase 2 (from SCP-OUT-13): trade PO invoice lines are matched against one received lot: by PO number when the PO line has one goods receipt, by the DO number recorded on the goods receipt when it has several; new exceptions EX11 – EX13 | Must | [SAPS-51](https://linear.app/jiringuyen/issue/SAPS-51) | [DEC-048](decision-log.md#dec-048); [DEC-065](decision-log.md#dec-065), [DEC-068](decision-log.md#dec-068) |
| SCP-IN-22 | Invoice list and search | Phase 2 (new): Accounting Members and Accounting Managers see and search all invoices of their company in every status, with filters; no export ([DEC-057](decision-log.md#dec-057)) | TBD ([MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) Q6) | [SAPS-46](https://linear.app/jiringuyen/issue/SAPS-46) | [DEC-048](decision-log.md#dec-048), [DEC-057](decision-log.md#dec-057) |
| SCP-IN-23 | Processing calendar | Phase 2 (new): the Accounting Manager sets closed periods for the company (monthly day ranges, weekdays, specific dates, local time zone); new invoices received in a closed period are held (On hold) and processed when it ends; a manager can release one invoice at once; automatic posting to the ERP waits on closed days too | Must | [SAPS-52](https://linear.app/jiringuyen/issue/SAPS-52) | [DEC-062](decision-log.md#dec-062) `[CR]`; [DEC-070](decision-log.md#dec-070) |

### 3.2 Integrations
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-09 | Dummy ERP data | Dummy purchase orders, goods receipts and vendors replace the ERP in the PoC. Phase 2, until SCP-IN-15: the open PO list, goods receipts with DO numbers and purchasing info records per company | Must | [SAPS-25](https://linear.app/jiringuyen/issue/SAPS-25) | [DEC-004](decision-log.md#dec-004); [DEC-067](decision-log.md#dec-067) |
| SCP-IN-15 | ERP integration | Phase 2 (from SCP-OUT-02): purchase orders, goods receipts and vendors from SAP ECC or SAP S/4HANA through MuleSoft APIs / MuleSoft MCP Tools, instead of dummy ERP data | TBD ([MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) Q7) | [SAPS-48](https://linear.app/jiringuyen/issue/SAPS-48) | [DEC-048](decision-log.md#dec-048) |
| SCP-IN-17 | Posting results to the ERP or exporting them | Phase 2 (from SCP-OUT-08): invoices are posted to the ERP through MuleSoft automatically at the end of the workflow (status Posted); a mock posting answers "ok" until MuleSoft and the ERP exist | Must | [SAPS-49](https://linear.app/jiringuyen/issue/SAPS-49) | [DEC-048](decision-log.md#dec-048); [DEC-063](decision-log.md#dec-063), [DEC-064](decision-log.md#dec-064) |

### 3.3 Infrastructure & Environments
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-10 | Local PoC environment | The PoC ran on a local machine with Docker Compose; the Phase 2 demo also runs locally, with a Keycloak container and a local test mail server added; no cloud environment ([DEC-053](decision-log.md#dec-053)) | Must | [SAPS-26](https://linear.app/jiringuyen/issue/SAPS-26) | [DEC-003](decision-log.md#dec-003); [ADR-0003](../02-architecture/adr/0003-use-postgresql-and-docker-compose.md) |

### 3.4 Deliverables & Services
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-11 | PoC end-to-end demo | Demo of all flows on 2027-02-22; no interim demo | Must | Linear milestone "PoC demo" | [DEC-003](decision-log.md#dec-003), [DEC-017](decision-log.md#dec-017) |

### 3.5 Non-Functional Scope
Quality requirements are specified in the [Non-Functional Requirements](nfr.md).

## 4. Out of Scope
| ID | Item | Reason / note | Source |
|---|---|---|---|
| SCP-OUT-01 | Real invoice data extraction (OCR / AI) | Not in the PoC and not in Phase 2: after the Phase 2 demo; the design must make it easy to add later ([DEC-050](decision-log.md#dec-050)) | [DEC-004](decision-log.md#dec-004), [DEC-050](decision-log.md#dec-050) |
| SCP-OUT-02 | ERP integration with SAP ECC or SAP S/4HANA through MuleSoft APIs / MuleSoft MCP Tools | **withdrawn** — moved into scope as SCP-IN-15 in Phase 2 ([DEC-048](decision-log.md#dec-048)) | [DEC-004](decision-log.md#dec-004) |
| SCP-OUT-03 | Payment | Out of the project scope | [DEC-009](decision-log.md#dec-009) |
| SCP-OUT-04 | Tax / VAT validation | Not required | [DEC-008](decision-log.md#dec-008) |
| SCP-OUT-05 | Credit notes | Not in the PoC | [DEC-007](decision-log.md#dec-007) |
| SCP-OUT-06 | Currencies other than USD | Not in the PoC | [DEC-006](decision-log.md#dec-006) |
| SCP-OUT-07 | Automated checks for non-PO invoices | **withdrawn** — moved into scope as SCP-IN-16 in Phase 2 ([DEC-048](decision-log.md#dec-048)) | [DEC-006](decision-log.md#dec-006) |
| SCP-OUT-08 | Posting results to the ERP or exporting them | **withdrawn** — moved into scope as SCP-IN-17 in Phase 2 ([DEC-048](decision-log.md#dec-048)) | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R16 |
| SCP-OUT-09 | Cloud deployment | Not in the PoC and not in Phase 2: after the Phase 2 demo; the design must make it easy to add later ([DEC-050](decision-log.md#dec-050)) | [DEC-003](decision-log.md#dec-003), [DEC-050](decision-log.md#dec-050) |
| SCP-OUT-10 | Single Sign-On | **withdrawn** — moved into scope as SCP-IN-18 in Phase 2 ([DEC-048](decision-log.md#dec-048)) | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R22 |
| SCP-OUT-11 | Invoice intake from a dedicated mailbox | **withdrawn** — moved into scope as SCP-IN-19 in Phase 2 ([DEC-048](decision-log.md#dec-048)) | [MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) R7 |
| SCP-OUT-12 | Serving several customer companies (multi-tenancy) | **withdrawn** — moved into scope as SCP-IN-20 in Phase 2 ([DEC-048](decision-log.md#dec-048)) | [DEC-026](decision-log.md#dec-026) |
| SCP-OUT-13 | GR-based invoice verification (delivery order / goods receipt reference on invoice lines) | **withdrawn** — moved into scope as SCP-IN-21 in Phase 2 ([DEC-048](decision-log.md#dec-048)) | [DEC-034](decision-log.md#dec-034) |
| SCP-OUT-14 | Return an invoice for correction (back to Exception) at approval or final review | After the PoC; reject only in the PoC | [DEC-039](decision-log.md#dec-039) |
| SCP-OUT-15 | Four-eyes rule (segregation of duties) at final review | After the PoC | [DEC-041](decision-log.md#dec-041) |

## 5. Assumptions
| # | Assumption | To be confirmed by | Status |
|---|---|---|---|
| AS1 | Manual upload is the only invoice intake channel in the PoC | Product Owner (Customer) | confirmed ([MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) R7); mailbox intake after the PoC (SCP-OUT-11) |
| AS2 | All in-scope items are priority Must for the PoC | Product Owner (Customer) | confirmed ([MTG-20261128](meetings/2026-11-28-poc-flow-review.md) R18) |

## 6. Constraints
Constraints are listed in [arc42 §2 Constraints](../02-architecture/arc42/02-constraints.md).

## 7. Dependencies
| # | Dependency | Owner | Needed by | Status |
|---|---|---|---|---|
| DP1 | Anonymized sample invoices ([MTG-20261114](meetings/2026-11-14-kickoff.md) A1) | Customer | — | not needed for the PoC ([DEC-004](decision-log.md#dec-004)) |
| DP2 | As-is AP process, ERP landscape and key contacts ([MTG-20261114](meetings/2026-11-14-kickoff.md) A2) | Customer | — | provided: the Product Owner is the single contact ([DEC-011](decision-log.md#dec-011)) |

## 8. Acceptance Approach
- PoC acceptance: all flows run successfully in the demo on 2027-02-22 (BO2, [DEC-020](decision-log.md#dec-020)).
- PoC accepted on 2027-03-01 ([DEC-047](decision-log.md#dec-047)).
- Phase 2 acceptance ([SAPS-47](https://linear.app/jiringuyen/issue/SAPS-47)): demo of the new features on 2027-08-30 (BO3, [DEC-051](decision-log.md#dec-051), [DEC-052](decision-log.md#dec-052)); demo scenarios TBD.
- Sign-off by: Product Owner (Customer) ([DEC-011](decision-log.md#dec-011)).
- Test approach and demo scenario catalog: [Test Strategy](../05-testing/test-strategy.md).

## 9. Open Questions
Scope-relevant questions are tracked and answered in the meeting minutes listed in the first column.

| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| MTG-20261114 Q3 | Success measures for the phase after the PoC | Product Owner (Customer) | after PoC | partly answered (direction: [DEC-026](decision-log.md#dec-026)) |
| MTG-20261114 Q9 | Intake channels other than manual upload | Product Owner (Customer) | — | answered: mailbox after the PoC ([MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) R7) |
| MTG-20261114 Q26 | Go-live date, phases after the PoC, budget | Product Owner (Customer) | after PoC | partly answered (PoC; Phase 2 start and length, [DEC-051](decision-log.md#dec-051)); demo date, go-live and budget → MTG-20270301 Q1 |
| [MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) Q1–Q12 | Phase 2 details: demo date, environment, Keycloak, mailbox, tenancy, invoice search, priorities, NFR targets, retention | Product Owner (Customer) | next meeting | open |
| MTG-20261114 Q27 | Cloud provider and account ownership after the PoC | Product Owner (Customer) | — | answered: AWS, Product Owner's account ([DEC-026](decision-log.md#dec-026)) |

## 10. Approval
| Name | Role | Organization | Date | Reference |
|---|---|---|---|---|
| TBD | Product Owner (sign-off owner) | Customer | — | pending |

## 11. Change History
| Version | Date | Author | Change | Decision |
|---|---|---|---|---|
| 0.1 | 2026-11-14 | Solution Architect (our company) | Initial draft from kickoff | [DEC-001](decision-log.md#dec-001) |
| 0.2 | 2026-11-21 | Solution Architect (our company) | Scope set to the PoC phase; SCP-IN-02, -04, -05 changed; SCP-IN-06 to -12 and SCP-OUT-01 to -10 added; BO2 added | [DEC-003](decision-log.md#dec-003) to [DEC-010](decision-log.md#dec-010) |
| 0.3 | 2026-11-28 | Solution Architect (our company) | SCP-IN-02, -04, -06, -08, -10, -11 and BO2 changed; SCP-IN-13, -14 added; AS2 confirmed; sign-off owner set; Linear epics linked | [DEC-011](decision-log.md#dec-011) to [DEC-021](decision-log.md#dec-021) |
| 0.4 | 2026-12-05 | Solution Architect (our company) | BO1 changed; AS1 confirmed for the PoC; SCP-OUT-11, -12 added; open questions updated | [DEC-026](decision-log.md#dec-026) |
| 0.5 | 2026-12-08 | Solution Architect (our company) | SCP-IN-03, -04 and BO2 changed (EX10, quantity rule); SCP-OUT-13 added | [DEC-031](decision-log.md#dec-031) to [DEC-034](decision-log.md#dec-034) |
| 0.6 | 2026-12-11 | Solution Architect (our company) | SCP-OUT-14, -15 added | [DEC-039](decision-log.md#dec-039), [DEC-041](decision-log.md#dec-041) |
| 0.7 | 2027-03-01 | Solution Architect (our company) | PoC accepted (BO2 met); Phase 2 `[CR]`: BO3, SCP-IN-15 to -22 added; SCP-OUT-02, -07, -08, -10, -11, -12, -13 withdrawn (moved into scope); SCP-OUT-01, -09 after the Phase 2 demo | [DEC-047](decision-log.md#dec-047) to [DEC-051](decision-log.md#dec-051) |
| 0.8 | 2027-03-01 | Solution Architect (our company) | BO3 demo date; SCP-IN-10, -18, -19, -20, -22 detailed | [DEC-052](decision-log.md#dec-052) to [DEC-057](decision-log.md#dec-057) |
| 0.9 | 2027-03-01 | Solution Architect (our company) | `[CR]` SCP-IN-23 processing calendar added | [DEC-062](decision-log.md#dec-062) |
| 0.10 | 2027-03-01 | Solution Architect (our company) | `[CR]` straight-through posting: SCP-IN-05 withdrawn; SCP-IN-03, -04, -06, -08, -09, -14 changed; SCP-IN-17, -21 detailed, priority Must | [DEC-063](decision-log.md#dec-063) to [DEC-068](decision-log.md#dec-068) |
| 0.11 | 2027-03-01 | Solution Architect (our company) | SCP-IN-23 detailed: posting waits on closed days | [DEC-070](decision-log.md#dec-070) |
