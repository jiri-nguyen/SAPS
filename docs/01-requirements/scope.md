---
title: Scope Statement
version: "0.6"           # 1.0 = first customer-approved version
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)", "Product Owner (Customer)"]
last_updated: 2026-12-11
related: [MTG-20261114, MTG-20261121, MTG-20261128, DEC-003, DEC-004, DEC-011, DEC-012, DEC-013, DEC-014, DEC-015, DEC-016, DEC-017, DEC-018, DEC-020, DEC-021, DEC-022, DEC-023, DEC-024, DEC-025, DEC-026, DEC-031, DEC-032, DEC-033, DEC-034, DEC-039, DEC-041]
---

# Scope Statement

## 1. Background
The customer wants to automate its Accounts Payable (AP) flow with a system named Smart-AP-Suite.
Today every step of invoice processing is manual. When invoice volume is high, processing takes a long time,
and human errors sometimes reduce accuracy.
Smart-AP-Suite receives invoices, extracts their data, matches them according to their invoice type,
routes exceptions and approvals, and presents the final result to an Accounting Member.

**This version covers the Proof of Concept (PoC) phase** ([DEC-003](decision-log.md#dec-003)).
Scope after the PoC is decided later. Terms are defined in the [§12 Glossary](../02-architecture/arc42/12-glossary.md).
Backlog items live in the Linear project
[Smart-AP-Suite](https://linear.app/jiringuyen/project/smart-ap-suite-766faab061af/overview).

## 2. Business Objectives
| # | Objective | Success measure |
|---|---|---|
| BO1 | Automate the AP flow and grow into an AP system serving many customer companies on AWS ([DEC-026](decision-log.md#dec-026)) | TBD |
| BO2 | Prove the automated AP business flow in a PoC | All flows run successfully in the demo on 2027-02-22: every scenario in the demo scenario catalog, i.e. happy paths per invoice type and one scenario per exception type EX1–EX10 ([DEC-033](decision-log.md#dec-033), [DEC-020](decision-log.md#dec-020), [DEC-017](decision-log.md#dec-017)) |

## 3. In Scope

### 3.1 Functional Capabilities
All items are priority Must for the PoC (AS2, confirmed).

| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-01 | Invoice upload | An Accounting Member uploads an invoice (PDF or image) to the system manually | Must | [SAPS-17](https://linear.app/jiringuyen/issue/SAPS-17) | [MTG-20261114](meetings/2026-11-14-kickoff.md) R1 |
| SCP-IN-02 | Invoice data extraction | Dummy extraction in the PoC: uploading a file from the dummy sample set loads its predefined data; any other file raises EX1 | Must | [SAPS-18](https://linear.app/jiringuyen/issue/SAPS-18) | [DEC-004](decision-log.md#dec-004), [DEC-012](decision-log.md#dec-012) |
| SCP-IN-03 | Invoice matching | Invoice type derived from the PO number; line-level 2-way / 3-way matching with price tolerance; non-PO invoices to manual review | Must | [SAPS-19](https://linear.app/jiringuyen/issue/SAPS-19) | [DEC-005](decision-log.md#dec-005), [DEC-006](decision-log.md#dec-006), [DEC-007](decision-log.md#dec-007), [DEC-031](decision-log.md#dec-031), [DEC-032](decision-log.md#dec-032), [DEC-034](decision-log.md#dec-034) |
| SCP-IN-04 | Exception handling | On an exception (EX1–EX10) the flow pauses; the invoice goes to a shared queue; an Accounting Member reviews and updates it; matching re-runs when a matching field changes | Must | [SAPS-20](https://linear.app/jiringuyen/issue/SAPS-20) | [DEC-033](decision-log.md#dec-033), [DEC-010](decision-log.md#dec-010), [DEC-016](decision-log.md#dec-016) |
| SCP-IN-05 | Final result review | At the end of the flow, an Accounting Member checks and confirms the result; the result is displayed in the application only | Must | [SAPS-21](https://linear.app/jiringuyen/issue/SAPS-21) | [MTG-20261114](meetings/2026-11-14-kickoff.md) R6; [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R16 |
| SCP-IN-06 | Invoice approval | Invoices of any type with a total amount (tax included) above the approval threshold are approved by an Accounting Manager, before the final review | Must | [SAPS-22](https://linear.app/jiringuyen/issue/SAPS-22) | [DEC-009](decision-log.md#dec-009), [DEC-013](decision-log.md#dec-013) |
| SCP-IN-07 | Duplicate invoice detection | An invoice with the same vendor and invoice number as an existing one becomes an exception | Must | [SAPS-23](https://linear.app/jiringuyen/issue/SAPS-23) | [DEC-008](decision-log.md#dec-008) |
| SCP-IN-08 | In-app notifications | In-app notifications by type: exceptions and final reviews to Accounting Members, approvals to the Accounting Manager | Must | [SAPS-24](https://linear.app/jiringuyen/issue/SAPS-24) | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R20; [DEC-021](decision-log.md#dec-021) |
| SCP-IN-12 | User roles | Two roles: Accounting Member and Accounting Manager; sign-in with simple user accounts | Must | [SAPS-27](https://linear.app/jiringuyen/issue/SAPS-27) | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R7, R22 |
| SCP-IN-13 | Matching settings | The Accounting Manager can change the price tolerance (default 0.5 USD) and the approval threshold (default 300 USD) | Must | [SAPS-28](https://linear.app/jiringuyen/issue/SAPS-28) | [DEC-015](decision-log.md#dec-015) |
| SCP-IN-14 | Invoice rejection | The Accounting Manager (at approval) or an Accounting Member (during exception handling or at final review) can reject an invoice; Rejected is a final state | Must | [SAPS-29](https://linear.app/jiringuyen/issue/SAPS-29) | [DEC-014](decision-log.md#dec-014) |

### 3.2 Integrations
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-09 | Dummy ERP data | Dummy purchase orders, goods receipts and vendors replace the ERP in the PoC | Must | [SAPS-25](https://linear.app/jiringuyen/issue/SAPS-25) | [DEC-004](decision-log.md#dec-004) |

### 3.3 Infrastructure & Environments
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-10 | Local PoC environment | The PoC runs on a local machine with Docker Compose; no cloud environment | Must | [SAPS-26](https://linear.app/jiringuyen/issue/SAPS-26) | [DEC-003](decision-log.md#dec-003); [ADR-0003](../02-architecture/adr/0003-use-postgresql-and-docker-compose.md) |

### 3.4 Deliverables & Services
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-11 | PoC end-to-end demo | Demo of all flows on 2027-02-22; no interim demo | Must | Linear milestone "PoC demo" | [DEC-003](decision-log.md#dec-003), [DEC-017](decision-log.md#dec-017) |

### 3.5 Non-Functional Scope
Quality requirements are specified in the [Non-Functional Requirements](nfr.md).

## 4. Out of Scope
| ID | Item | Reason / note | Source |
|---|---|---|---|
| SCP-OUT-01 | Real invoice data extraction (OCR / AI) | Not in the PoC; dummy extraction data is used | [DEC-004](decision-log.md#dec-004) |
| SCP-OUT-02 | ERP integration with SAP ECC or SAP S/4HANA through MuleSoft APIs / MuleSoft MCP Tools | Not in the PoC; candidate for a later phase | [DEC-004](decision-log.md#dec-004) |
| SCP-OUT-03 | Payment | Out of the project scope | [DEC-009](decision-log.md#dec-009) |
| SCP-OUT-04 | Tax / VAT validation | Not required | [DEC-008](decision-log.md#dec-008) |
| SCP-OUT-05 | Credit notes | Not in the PoC | [DEC-007](decision-log.md#dec-007) |
| SCP-OUT-06 | Currencies other than USD | Not in the PoC | [DEC-006](decision-log.md#dec-006) |
| SCP-OUT-07 | Automated checks for non-PO invoices | Not in the PoC; candidate for a later phase | [DEC-006](decision-log.md#dec-006) |
| SCP-OUT-08 | Posting results to the ERP or exporting them | Not in the PoC; the result is only displayed | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R16 |
| SCP-OUT-09 | Cloud deployment | Not in the PoC; the PoC runs locally | [DEC-003](decision-log.md#dec-003) |
| SCP-OUT-10 | Single Sign-On | Not in the PoC; simple user accounts are used | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R22 |
| SCP-OUT-11 | Invoice intake from a dedicated mailbox | After the PoC; the PoC covers manual upload only | [MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) R7 |
| SCP-OUT-12 | Serving several customer companies (multi-tenancy) | After the PoC; the PoC serves one company and only prepares the data model ([ADR-0007](../02-architecture/adr/0007-prepare-data-model-for-tenants.md)) | [DEC-026](decision-log.md#dec-026) |
| SCP-OUT-13 | GR-based invoice verification (delivery order / goods receipt reference on invoice lines) | After the PoC; the PoC matches cumulatively per PO line | [DEC-034](decision-log.md#dec-034) |
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
- Sign-off by: Product Owner (Customer) ([DEC-011](decision-log.md#dec-011)).
- Test approach and demo scenario catalog: [Test Strategy](../05-testing/test-strategy.md).

## 9. Open Questions
Scope-relevant questions are tracked and answered in the meeting minutes listed in the first column.

| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| MTG-20261114 Q3 | Success measures for the phase after the PoC | Product Owner (Customer) | after PoC | partly answered (direction: [DEC-026](decision-log.md#dec-026)) |
| MTG-20261114 Q9 | Intake channels other than manual upload | Product Owner (Customer) | — | answered: mailbox after the PoC ([MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) R7) |
| MTG-20261114 Q26 | Go-live date, phases after the PoC, budget | Product Owner (Customer) | after PoC | partly answered (PoC, demo date, sign-off owner) |
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
