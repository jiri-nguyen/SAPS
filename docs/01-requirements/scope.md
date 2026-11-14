---
title: Scope Statement
version: "0.2"           # 1.0 = first customer-approved version
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)", "Customer representative (Customer)"]
last_updated: 2026-11-21
related: [MTG-20261114, MTG-20261121, DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-006, DEC-007, DEC-008, DEC-009, DEC-010]
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

## 2. Business Objectives
| # | Objective | Success measure |
|---|---|---|
| BO1 | Automate the AP flow | TBD (MTG-20261114 Q3) |
| BO2 | Prove the automated AP business flow in a PoC | End-to-end demo of the flow for different cases, including exception cases ([DEC-003](decision-log.md#dec-003)) |

## 3. In Scope

### 3.1 Functional Capabilities
> **Assumption:** all items below are priority Must for the PoC (AS2).

| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-01 | Invoice upload | An Accounting Member uploads an invoice (PDF or image) to the system manually | Must | TBD | [MTG-20261114](meetings/2026-11-14-kickoff.md) R1 |
| SCP-IN-02 | Invoice data extraction | Invoice data is provided by dummy extraction data in the PoC; no real OCR/AI extraction | Must | TBD | [MTG-20261114](meetings/2026-11-14-kickoff.md) R2; [DEC-004](decision-log.md#dec-004) |
| SCP-IN-03 | Invoice matching | Invoice type derived from the PO number; line-level 2-way / 3-way matching with price tolerance; non-PO invoices to manual review | Must | TBD | [MTG-20261114](meetings/2026-11-14-kickoff.md) R3, R4; [DEC-005](decision-log.md#dec-005), [DEC-006](decision-log.md#dec-006), [DEC-007](decision-log.md#dec-007) |
| SCP-IN-04 | Exception handling | On an exception (types EX1–EX9, [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R19) the flow pauses; an Accounting Member reviews and updates the invoice; matching re-runs when a matching field changes | Must | TBD | [MTG-20261114](meetings/2026-11-14-kickoff.md) R5; [DEC-010](decision-log.md#dec-010) |
| SCP-IN-05 | Final result review | At the end of the flow, an Accounting Member is notified to check the result; the result is displayed in the application only | Must | TBD | [MTG-20261114](meetings/2026-11-14-kickoff.md) R6; [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R16 |
| SCP-IN-06 | Invoice approval | Invoices with a total amount (tax included) above 300 USD are approved by an Accounting Manager | Must | TBD | [DEC-009](decision-log.md#dec-009) |
| SCP-IN-07 | Duplicate invoice detection | An invoice with the same vendor and invoice number as an existing one becomes an exception | Must | TBD | [DEC-008](decision-log.md#dec-008) |
| SCP-IN-08 | In-app notifications | Exceptions, approvals and final results are notified inside the application | Must | TBD | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R20 |
| SCP-IN-12 | User roles | Two roles: Accounting Member and Accounting Manager; sign-in with simple user accounts | Must | TBD | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R7, R22 |

### 3.2 Integrations
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-09 | Dummy ERP data | Dummy purchase orders, goods receipts and vendors replace the ERP in the PoC | Must | TBD | [DEC-004](decision-log.md#dec-004) |

### 3.3 Infrastructure & Environments
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-10 | Local PoC environment | The PoC runs on a local machine; no cloud environment | Must | TBD | [DEC-003](decision-log.md#dec-003) |

### 3.4 Deliverables & Services
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-11 | PoC end-to-end demo | Demo of the end-to-end flow for different cases, including exception cases, within 3 months from 2026-11-21 | Must | n/a | [DEC-003](decision-log.md#dec-003) |

### 3.5 Non-Functional Scope
Quality requirements will be specified in the Non-Functional Requirements (`nfr.md`, not yet created).

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

## 5. Assumptions
| # | Assumption | To be confirmed by | Status |
|---|---|---|---|
| AS1 | Manual upload is the only invoice intake channel (no email intake, no e-invoice XML intake) | Customer representative (Customer), MTG-20261114 Q9 | open |
| AS2 | All in-scope items are priority Must for the PoC | Customer representative (Customer), MTG-20261114 Q26 | open |

## 6. Constraints
Constraints will be listed in arc42 §2 Constraints (`../02-architecture/arc42/02-constraints.md`, not yet created).

## 7. Dependencies
| # | Dependency | Owner | Needed by | Status |
|---|---|---|---|---|
| DP1 | Anonymized sample invoices ([MTG-20261114](meetings/2026-11-14-kickoff.md) A1) | Customer representative (Customer) | — | not needed for the PoC ([DEC-004](decision-log.md#dec-004)) |
| DP2 | As-is AP process, ERP landscape and key contacts ([MTG-20261114](meetings/2026-11-14-kickoff.md) A2) | Customer representative (Customer) | 2026-11-28 | partly provided: contacts open ([MTG-20261121](meetings/2026-11-21-requirements-workshop.md) A1) |

## 8. Acceptance Approach
- PoC acceptance: end-to-end demo of the flow for different cases, including exception cases ([DEC-003](decision-log.md#dec-003)).
- Demo date and sign-off owner: TBD ([MTG-20261121](meetings/2026-11-21-requirements-workshop.md) Q7; MTG-20261114 Q26).
- Test approach: will be defined in the Test Strategy (`../05-testing/test-strategy.md`, not yet created).

## 9. Open Questions
Scope-relevant questions are tracked and answered in the meeting minutes listed in the first column.

| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| MTG-20261114 Q3 | Business objectives and success measures | Customer representative (Customer) | 2026-11-28 | open |
| MTG-20261114 Q9 | Intake channels other than manual upload; e-invoice XML | Customer representative (Customer) | 2026-11-28 | open |
| MTG-20261114 Q26 | Go-live date, phases after the PoC, budget, UAT and sign-off owner | Customer representative (Customer) | 2026-11-28 | partly answered (PoC first) |
| MTG-20261114 Q27 | Cloud provider and account ownership after the PoC | Customer representative (Customer) | 2026-11-28 | partly answered (PoC local) |
| MTG-20261121 Q1 | How an upload maps to dummy extraction data | Customer representative (Customer) | 2026-11-28 | open |
| MTG-20261121 Q2 | Order of approval and final review | Customer representative (Customer) | 2026-11-28 | open |
| MTG-20261121 Q3 | Handling of rejected invoices | Customer representative (Customer) | 2026-11-28 | open |
| MTG-20261121 Q4 | Does the 300 USD approval rule apply to non-PO invoices? | Customer representative (Customer) | 2026-11-28 | open |
| MTG-20261121 Q7 | Exact PoC end date and demo date | Customer representative (Customer) | 2026-11-28 | open |

## 10. Approval
| Name | Role | Organization | Date | Reference |
|---|---|---|---|---|
| TBD | Sign-off owner (MTG-20261114 Q26) | Customer | — | pending |

## 11. Change History
| Version | Date | Author | Change | Decision |
|---|---|---|---|---|
| 0.1 | 2026-11-14 | Solution Architect (our company) | Initial draft from kickoff | [DEC-001](decision-log.md#dec-001) |
| 0.2 | 2026-11-21 | Solution Architect (our company) | Scope set to the PoC phase; SCP-IN-02, -04, -05 changed; SCP-IN-06 to -12 and SCP-OUT-01 to -10 added; BO2 added | [DEC-003](decision-log.md#dec-003) to [DEC-010](decision-log.md#dec-010) |
