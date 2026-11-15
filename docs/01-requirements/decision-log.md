---
title: Decision Log
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["PM (TBD)"]
last_updated: 2026-11-28
related: [MTG-20261114, MTG-20261121, MTG-20261128]
---

# Decision Log

## 1. Index
| ID | Date | Title | Category | Status |
|---|---|---|---|---|
| [DEC-001](#dec-001) | 2026-11-14 | Project name Smart-AP-Suite, project code SAPS | Project | confirmed |
| [DEC-002](#dec-002) | 2026-11-14 | Track work items in Linear | Process | confirmed |
| [DEC-003](#dec-003) | 2026-11-21 | Deliver a Proof of Concept first | Scope | confirmed |
| [DEC-004](#dec-004) | 2026-11-21 | Use dummy data for extraction and ERP data in the PoC | Scope | confirmed |
| [DEC-005](#dec-005) | 2026-11-21 | Derive the invoice type from the PO number | Business | confirmed |
| [DEC-006](#dec-006) | 2026-11-21 | PoC matching rules and tolerance | Business | confirmed |
| [DEC-007](#dec-007) | 2026-11-21 | Partial deliveries and multi-document invoices | Business | confirmed |
| [DEC-008](#dec-008) | 2026-11-21 | Duplicate invoice detection; no tax/VAT checks | Business | confirmed |
| [DEC-009](#dec-009) | 2026-11-21 | Accounting Manager approval above 300 USD | Business | confirmed |
| [DEC-010](#dec-010) | 2026-11-21 | Re-run matching after a manual update of matching fields | Business | confirmed |
| [DEC-011](#dec-011) | 2026-11-28 | Product Owner is the customer's decision maker and PoC sign-off owner | Project | confirmed |
| [DEC-012](#dec-012) | 2026-11-28 | Upload from a dummy sample set; unknown files raise EX1 | Scope | confirmed |
| [DEC-013](#dec-013) | 2026-11-28 | Approval before final review, for all invoice types | Business | confirmed |
| [DEC-014](#dec-014) | 2026-11-28 | Rejected is a final state; three rejection points | Business | confirmed |
| [DEC-015](#dec-015) | 2026-11-28 | Configurable tolerance and approval threshold | Business | confirmed |
| [DEC-016](#dec-016) | 2026-11-28 | Shared exception queue | Business | confirmed |
| [DEC-017](#dec-017) | 2026-11-28 | PoC demo on 2027-02-22 | Project | confirmed |
| [DEC-018](#dec-018) | 2026-11-28 | Exception types EX1–EX9 for the PoC | Business | confirmed |
| [DEC-019](#dec-019) | 2026-11-28 | Customer agrees the PoC technology stack | Technical | confirmed |
| [DEC-020](#dec-020) | 2026-11-28 | PoC success criterion: all flows run successfully | Scope | confirmed |
| [DEC-021](#dec-021) | 2026-11-28 | Notification recipients by notification type | Business | confirmed |

## 2. Decisions

### DEC-001
**Project name Smart-AP-Suite, project code SAPS**

| Field | Value |
|---|---|
| Date | 2026-11-14 |
| Category | Project |
| Status | confirmed |
| Decided by | Customer representative (Customer); Solution Architect (our company) |
| Source | [MTG-20261114](meetings/2026-11-14-kickoff.md) D1 |
| Impacts | Project Context in `CLAUDE.md`; all document IDs and issue keys |
| Supersedes / Superseded by | — |

**Context:** The project needs a name and a short code for documents and issue keys.

**Decision:** The project is named "Smart-AP-Suite". The project code is `SAPS`.

**Rationale:** The customer gave the name at kickoff. `SAP` was rejected as a code because it clashes with the SAP ERP product name.

**Consequences & follow-ups:** Issue keys and feature spec file names use `SAPS-NNN`.

### DEC-002
**Track work items in Linear**

| Field | Value |
|---|---|
| Date | 2026-11-14 |
| Category | Process |
| Status | confirmed |
| Decided by | Solution Architect (our company) |
| Source | [MTG-20261114](meetings/2026-11-14-kickoff.md) D2 |
| Impacts | Project Context in `CLAUDE.md`; backlog epic links in [scope.md](scope.md) |
| Supersedes / Superseded by | — |

**Context:** The documentation standard assumes Jira or Azure Boards as the work tracker.

**Decision:** This project tracks epics, stories and bugs in Linear. Where the standard says "Jira key", read "Linear issue key".

**Rationale:** Linear is the tracker the team uses.

**Consequences & follow-ups:** The Linear workspace base URL is TBD. The Solution Architect adds it to the Project Context once the Linear team `SAPS` exists.

### DEC-003
**Deliver a Proof of Concept first**

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Category | Scope |
| Status | confirmed |
| Decided by | Customer representative (Customer) |
| Source | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) D1 |
| Impacts | [scope.md](scope.md) v0.2 (BO2, SCP-IN-10, SCP-IN-11, SCP-OUT-09) |
| Supersedes / Superseded by | — |

**Context:** The kickoff described the full AP flow. Phases and timeline were open (MTG-20261114 Q26).

**Decision:** The project starts with a Proof of Concept (PoC). The PoC lasts 3 months from 2026-11-21 and runs locally.
It succeeds when the end-to-end flow is demonstrated for different cases, including exception cases.

**Rationale:** The customer is currently interested in the automated business flow.

**Consequences & follow-ups:** Scope v0.2 describes the PoC. Exact end date and demo date are open
([MTG-20261121](meetings/2026-11-21-requirements-workshop.md) Q7). Scope after the PoC is decided later.

### DEC-004
**Use dummy data for extraction and ERP data in the PoC**

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Category | Scope |
| Status | confirmed |
| Decided by | Customer representative (Customer) |
| Source | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) D2 |
| Impacts | [scope.md](scope.md) SCP-IN-02 (changed), SCP-IN-09, SCP-OUT-01, SCP-OUT-02 |
| Supersedes / Superseded by | — |

**Context:** Real extraction needs sample invoices and OCR/AI services; real ERP data needs SAP integration.

**Decision:** In the PoC, invoice extraction results and the minimum ERP data needed by the flow
(purchase orders, goods receipts, vendors) are dummy data.

**Rationale:** The PoC focuses on the automated business flow, not on extraction.

**Consequences & follow-ups:** Later phases get ERP data from SAP ECC or SAP S/4HANA through MuleSoft APIs or
MuleSoft MCP Tools. The design lets dummy sources be replaced ([ADR-0001](../02-architecture/adr/0001-isolate-extraction-and-erp-behind-ports.md)). How an upload maps to dummy
extraction data is open ([MTG-20261121](meetings/2026-11-21-requirements-workshop.md) Q1).

### DEC-005
**Derive the invoice type from the PO number**

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Category | Business |
| Status | confirmed |
| Decided by | Customer representative (Customer) |
| Source | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) D3 |
| Impacts | [scope.md](scope.md) SCP-IN-03, SCP-IN-04 |
| Supersedes / Superseded by | — |

**Context:** The matching method depends on the invoice type (MTG-20261114 Q13).

**Decision:** A PO number has 7 characters, digits only. The invoice type comes from the PO number on the invoice:

| PO number on invoice | Invoice type | Matching |
|---|---|---|
| Starts with `0` | Trade PO invoice | 3-way |
| Starts with `1` | Non-trade PO invoice | 2-way |
| None | Non-PO invoice | 1-way (manual review in the PoC, see DEC-006) |
| Any other value | — | Exception, sent to the Accounting Member |

**Rationale:** Keeps the PoC simple (customer).

**Consequences & follow-ups:** The rule may change when real ERP data is used.

### DEC-006
**PoC matching rules and tolerance**

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Category | Business |
| Status | confirmed |
| Decided by | Customer representative (Customer) |
| Source | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) D4 |
| Impacts | [scope.md](scope.md) SCP-IN-03, SCP-OUT-06, SCP-OUT-07 |
| Supersedes / Superseded by | — |

**Context:** Matching level and tolerances were open (MTG-20261114 Q14–Q16).

**Decision:**
- 2-way and 3-way matching compare line by line.
- The invoice unit price may differ from the PO unit price by at most 0.5 USD per line, for all vendors and categories.
- Quantity must match exactly.
- The PoC handles USD only.
- Non-PO invoices go directly to the Accounting Member for manual review and update; no automated checks in the PoC.

**Rationale:** Keeps the PoC simple (customer).

**Consequences & follow-ups:** Whether the tolerance is configurable is open
([MTG-20261121](meetings/2026-11-21-requirements-workshop.md) Q5).

### DEC-007
**Partial deliveries and multi-document invoices**

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Category | Business |
| Status | confirmed |
| Decided by | Customer representative (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) D5 |
| Impacts | [scope.md](scope.md) SCP-IN-03, SCP-IN-04, SCP-OUT-05 |
| Supersedes / Superseded by | — |

**Context:** The customer asked the SA to propose handling in line with common AP practice (MTG-20261114 Q17).

**Decision:**

| Case | Handling |
|---|---|
| Partial delivery (3-way) | Invoice quantity is compared with the received-not-invoiced quantity of the PO line; above it → exception |
| Several goods receipts for one PO line | Their quantities are summed |
| One invoice for several POs | Each invoice line references its own PO line |
| Trade and non-trade POs on one invoice | Exception, manual review |
| 2-way (non-trade) | Invoice quantity is compared with the PO quantity not yet invoiced |
| Credit note | Out of the PoC scope |

**Rationale:** Common practice in AP automation systems; accepted by the customer.

**Consequences & follow-ups:** The system must keep the invoiced quantity per PO line.

### DEC-008
**Duplicate invoice detection; no tax/VAT checks**

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Category | Business |
| Status | confirmed |
| Decided by | Customer representative (Customer) |
| Source | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) D6 |
| Impacts | [scope.md](scope.md) SCP-IN-07, SCP-OUT-04 |
| Supersedes / Superseded by | — |

**Context:** Duplicate detection and tax checks were open (MTG-20261114 Q18).

**Decision:** An invoice with the same vendor and invoice number as an existing invoice is a duplicate.
A duplicate becomes an exception for the Accounting Member; it is not rejected automatically. There are no tax/VAT checks.

**Rationale:** Duplicate definition proposed by the SA and accepted by the customer; tax checks not required (customer).

**Consequences & follow-ups:** None.

### DEC-009
**Accounting Manager approval above 300 USD**

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Category | Business |
| Status | confirmed |
| Decided by | Customer representative (Customer) |
| Source | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) D7 |
| Impacts | [scope.md](scope.md) SCP-IN-06, SCP-IN-12, SCP-OUT-03 |
| Supersedes / Superseded by | — |

**Context:** An approval workflow was open (MTG-20261114 Q21). The kickoff had one role only.

**Decision:** An invoice whose total amount, tax included, is above 300 USD needs approval by a new role,
the Accounting Manager. Payment is out of the project scope.

**Rationale:** Stated by the customer.

**Consequences & follow-ups:** Open: order of approval and final review, rejection handling, whether the rule applies to
non-PO invoices, and whether the threshold is configurable ([MTG-20261121](meetings/2026-11-21-requirements-workshop.md) Q2–Q5).

### DEC-010
**Re-run matching after a manual update of matching fields**

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Category | Business |
| Status | confirmed |
| Decided by | Customer representative (Customer) |
| Source | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) D8 |
| Impacts | [scope.md](scope.md) SCP-IN-04 |
| Supersedes / Superseded by | — |

**Context:** Behavior after a manual update was open (MTG-20261114 Q25).

**Decision:** When an Accounting Member changes a field used in matching, the system re-runs matching.

**Rationale:** Stated by the customer.

**Consequences & follow-ups:** The feature spec lists which fields are matching fields.

### DEC-011
**Product Owner is the customer's decision maker and PoC sign-off owner**

| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Category | Project |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D1, R14 |
| Impacts | [scope.md](scope.md) §8, §10; [arc42 §1.3](../02-architecture/arc42/01-introduction-and-goals.md) |
| Supersedes / Superseded by | — |

**Context:** The customer attendee list and the PoC sign-off owner were open (MTG-20261114 Q26, MTG-20261121 A1).

**Decision:** The Product Owner is the customer's single representative in all meetings, its decision maker,
and the sign-off owner for the PoC acceptance.

**Rationale:** Stated by the customer.

**Consequences & follow-ups:** Earlier documents name the same person "Customer representative"; they stay unchanged.
New and updated documents use "Product Owner (Customer)".

### DEC-012
**Upload from a dummy sample set; unknown files raise EX1**

| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Category | Scope |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D2 |
| Impacts | [scope.md](scope.md) SCP-IN-02; [ADR-0001](../02-architecture/adr/0001-isolate-extraction-and-erp-behind-ports.md) Dummy Extraction Adapter |
| Supersedes / Superseded by | — |

**Context:** How an upload maps to dummy extraction data was open (MTG-20261121 Q1).

**Decision:** Our team prepares a dummy sample set: each sample is an invoice file (PDF or image) with predefined
extraction data. Uploading a file from the set loads its data. Uploading any other file raises exception EX1.

**Rationale:** Proposed by the SA; the Product Owner added the rule for unknown files.

**Consequences & follow-ups:** The sample set is part of the demo scenario catalog (SAPS-32).

### DEC-013
**Approval before final review, for all invoice types**

| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D3 |
| Impacts | [scope.md](scope.md) SCP-IN-06; [§6.2 Runtime View](../02-architecture/arc42/06-runtime-view.md) |
| Supersedes / Superseded by | — |

**Context:** The order of approval and final review, and the scope of the approval rule, were open (MTG-20261121 Q2, Q4).

**Decision:** When approval is required ([DEC-009](#dec-009)), it comes before the Accounting Member's final review.
The approval rule applies to all invoice types, including non-PO invoices.

**Rationale:** Proposed by the SA; accepted by the Product Owner.

**Consequences & follow-ups:** None.

### DEC-014
**Rejected is a final state; three rejection points**

| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D4, R15 |
| Impacts | [scope.md](scope.md) SCP-IN-14 |
| Supersedes / Superseded by | — |

**Context:** Handling of rejected invoices was open (MTG-20261121 Q3).

**Decision:** Rejected is a final state; a rejected invoice is not processed further. An invoice can be rejected:
- by the Accounting Manager at approval;
- by an Accounting Member during exception handling (e.g. a real duplicate);
- by an Accounting Member at the final review.

**Rationale:** Stated by the Product Owner; rejection points proposed by the SA and confirmed.

**Consequences & follow-ups:** None.

### DEC-015
**Configurable tolerance and approval threshold**

| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D5, R16 |
| Impacts | [scope.md](scope.md) SCP-IN-13; refines [DEC-006](#dec-006), [DEC-009](#dec-009) |
| Supersedes / Superseded by | — |

**Context:** Whether the 0.5 USD tolerance and 300 USD threshold are fixed was open (MTG-20261121 Q5).

**Decision:** The price tolerance and the approval threshold are settings. Defaults: 0.5 USD and 300 USD.
Only the Accounting Manager can change them.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** None.

### DEC-016
**Shared exception queue**

| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D6 |
| Impacts | [scope.md](scope.md) SCP-IN-04 |
| Supersedes / Superseded by | — |

**Context:** Assignment of exceptions was open (MTG-20261114 Q23, MTG-20261121 Q6).

**Decision:** Invoices in status Exception go to one shared queue. Any available Accounting Member picks one up.

**Rationale:** Proposed by the SA; accepted by the Product Owner.

**Consequences & follow-ups:** None.

### DEC-017
**PoC demo on 2027-02-22**

| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Category | Project |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D7 |
| Impacts | [scope.md](scope.md) SCP-IN-11; [CON-02](../02-architecture/arc42/02-constraints.md); refines [DEC-003](#dec-003) |
| Supersedes / Superseded by | — |

**Context:** DEC-003 set a 3-month PoC from 2026-11-21 without an exact end date (MTG-20261121 Q7).

**Decision:** The PoC demo is on 2027-02-22. There is no interim demo.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** The demo date is one day after the 3-month mark (2027-02-21).

### DEC-018
**Exception types EX1–EX9 for the PoC**

| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D8 |
| Impacts | [scope.md](scope.md) SCP-IN-04 |
| Supersedes / Superseded by | — |

**Context:** The SA proposed a merged exception list ([MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R19, Q8).

**Decision:** The PoC supports these exception types:

| Code | Exception |
|---|---|
| EX1 | Invoice unreadable: extraction failed or file not in the dummy sample set |
| EX2 | Non-PO invoice (manual review) |
| EX3 | Invalid PO number (not 7 digits, or prefix other than 0 / 1) |
| EX4 | PO not found |
| EX5 | Trade and non-trade POs on one invoice |
| EX6 | Unit price outside tolerance |
| EX7 | Quantity mismatch |
| EX8 | Missing goods receipt |
| EX9 | Duplicate invoice |

**Rationale:** Confirmed by the Product Owner "for now"; the list may grow after the PoC.

**Consequences & follow-ups:** One demo scenario per exception type (SAPS-32).

### DEC-019
**Customer agrees the PoC technology stack**

| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Category | Technical |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D9 |
| Impacts | [ADR-0002](../02-architecture/adr/0002-use-python-fastapi-and-react.md), [ADR-0003](../02-architecture/adr/0003-use-postgresql-and-docker-compose.md) |
| Supersedes / Superseded by | — |

**Context:** ADR-0002 and ADR-0003 left customer agreement TBD; accepted ADRs cannot be edited.

**Decision:** The customer agrees the PoC stack: Python/FastAPI, React, PostgreSQL, Docker Compose.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** None.

### DEC-020
**PoC success criterion: all flows run successfully**

| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Category | Scope |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D10 |
| Impacts | [scope.md](scope.md) BO2; refines [DEC-003](#dec-003) |
| Supersedes / Superseded by | — |

**Context:** Business objectives are not defined yet (MTG-20261114 Q3).

**Decision:** At this point, the PoC is successful when all flows run successfully in the demo.
"All flows" means every scenario in the demo scenario catalog: happy paths per invoice type and one scenario per
exception type EX1–EX9.

**Rationale:** Stated by the Product Owner; the meaning of "all flows" was proposed by the SA and confirmed.

**Consequences & follow-ups:** The demo scenario catalog is defined in the test strategy (SAPS-32).

### DEC-021
**Notification recipients by notification type**

| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D11, R17 |
| Impacts | [scope.md](scope.md) SCP-IN-08 |
| Supersedes / Superseded by | — |

**Context:** Who receives in-app notifications was open (MTG-20261128 Q4).

**Decision:**

| Notification | Recipients |
|---|---|
| Invoice in status Exception | Accounting Members |
| Invoice waiting for approval (above the approval threshold) | Accounting Manager |
| Invoice ready for final review | Accounting Members |

**Rationale:** Stated by the Product Owner; matches the flow in §6.2.

**Consequences & follow-ups:** None.
