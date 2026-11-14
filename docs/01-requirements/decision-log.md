---
title: Decision Log
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["PM (TBD)"]
last_updated: 2026-11-21
related: [MTG-20261114, MTG-20261121]
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
MuleSoft MCP Tools. The design should let dummy sources be replaced (ADR need ADR-N1). How an upload maps to dummy
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
