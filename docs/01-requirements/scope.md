---
title: Scope Statement
version: "0.1"           # 1.0 = first customer-approved version
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)", "Customer representative (Customer)"]
last_updated: 2026-11-14
related: [MTG-20261114, DEC-001, DEC-002]
---

# Scope Statement

## 1. Background
The customer wants to automate its Accounts Payable (AP) flow with a system named Smart-AP-Suite.
The current AP process and its pain points are TBD (MTG-20261114 Q2).
Smart-AP-Suite receives invoices, extracts their data, matches them according to their invoice type,
and routes exceptions and final results to an Accounting Member.
Terms are defined in the [§12 Glossary](../02-architecture/arc42/12-glossary.md).

## 2. Business Objectives
| # | Objective | Success measure |
|---|---|---|
| BO1 | Automate the AP flow | TBD (MTG-20261114 Q3) |

## 3. In Scope

### 3.1 Functional Capabilities
> **Assumption:** all items below are priority Must for the first release (AS2).

| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-01 | Invoice upload | A user uploads an invoice (PDF or image) to the system manually | Must | TBD | [MTG-20261114](meetings/2026-11-14-kickoff.md) R1 |
| SCP-IN-02 | Invoice data extraction | The system automatically extracts the information on the invoice | Must | TBD | [MTG-20261114](meetings/2026-11-14-kickoff.md) R2 |
| SCP-IN-03 | Invoice matching | The system automatically performs 1-way, 2-way or 3-way matching for non-PO, non-trade PO and trade PO invoices | Must | TBD | [MTG-20261114](meetings/2026-11-14-kickoff.md) R3, R4 |
| SCP-IN-04 | Exception handling | On an exception, the flow pauses and an Accounting Member is notified to review and update the invoice manually | Must | TBD | [MTG-20261114](meetings/2026-11-14-kickoff.md) R5 |
| SCP-IN-05 | Final result review | At the end of the flow, an Accounting Member is notified to check the result | Must | TBD | [MTG-20261114](meetings/2026-11-14-kickoff.md) R6 |

### 3.2 Integrations
None agreed yet. The source of POs, goods receipts and vendor data, and the target of matched invoices, are open (MTG-20261114 Q19, Q20).

### 3.3 Infrastructure & Environments
None agreed yet. Cloud provider and account ownership are open (MTG-20261114 Q27).

### 3.4 Deliverables & Services
None agreed yet. Phases, UAT and handover are open (MTG-20261114 Q26).

### 3.5 Non-Functional Scope
Quality requirements will be specified in the Non-Functional Requirements (`nfr.md`, not yet created).

## 4. Out of Scope
None agreed yet. Candidates are open questions: e-invoice XML and other intake channels (MTG-20261114 Q9), approval workflow and payment (MTG-20261114 Q21).

## 5. Assumptions
| # | Assumption | To be confirmed by | Status |
|---|---|---|---|
| AS1 | Manual upload is the only invoice intake channel (no email intake, no e-invoice XML intake) | Customer representative (Customer), MTG-20261114 Q9 | open |
| AS2 | SCP-IN-01 to SCP-IN-05 are all priority Must for the first release | Customer representative (Customer), MTG-20261114 Q26 | open |

## 6. Constraints
Constraints will be listed in arc42 §2 Constraints (`../02-architecture/arc42/02-constraints.md`, not yet created).

## 7. Dependencies
| # | Dependency | Owner | Needed by | Status |
|---|---|---|---|---|
| DP1 | Anonymized sample invoices, at least 3 per invoice type, PDF and image ([MTG-20261114](meetings/2026-11-14-kickoff.md) A1) | Customer representative (Customer) | 2026-11-21 | open |
| DP2 | Description of the as-is AP process, ERP landscape and key contacts ([MTG-20261114](meetings/2026-11-14-kickoff.md) A2) | Customer representative (Customer) | 2026-11-21 | open |

## 8. Acceptance Approach
- Acceptance approach and sign-off owner: TBD (MTG-20261114 Q26).
- Test approach: will be defined in the Test Strategy (`../05-testing/test-strategy.md`, not yet created).

## 9. Open Questions
Scope-relevant questions are tracked in [MTG-20261114](meetings/2026-11-14-kickoff.md) §9 and answered there first.

| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| MTG-20261114 Q3 | Business objectives and success measures | Customer representative (Customer) | 2026-11-21 | open |
| MTG-20261114 Q9 | Intake channels other than manual upload; e-invoice XML | Customer representative (Customer) | 2026-11-21 | open |
| MTG-20261114 Q19 | ERP integration for POs, goods receipts, vendor master | Customer representative (Customer) | 2026-11-21 | open |
| MTG-20261114 Q20 | Target of matched invoices: post to ERP, export, or display only | Customer representative (Customer) | 2026-11-21 | open |
| MTG-20261114 Q21 | Approval workflow and payment in scope? | Customer representative (Customer) | 2026-11-21 | open |
| MTG-20261114 Q26 | Go-live date, phases, UAT and sign-off owner | Customer representative (Customer) | 2026-11-21 | open |
| MTG-20261114 Q27 | Cloud provider and account ownership | Customer representative (Customer) | 2026-11-21 | open |

## 10. Approval
| Name | Role | Organization | Date | Reference |
|---|---|---|---|---|
| TBD | Sign-off owner (MTG-20261114 Q26) | Customer | — | pending |

## 11. Change History
| Version | Date | Author | Change | Decision |
|---|---|---|---|---|
| 0.1 | 2026-11-14 | Solution Architect (our company) | Initial draft from kickoff | [DEC-001](decision-log.md#dec-001) |
