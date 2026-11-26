---
title: Decision Log
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["PM (TBD)"]
last_updated: 2027-03-01
related: [MTG-20261114, MTG-20261121, MTG-20261128, MTG-20261205, MTG-20261208, MTG-20261210, MTG-20261211, MTG-20261214]
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
| [DEC-018](#dec-018) | 2026-11-28 | Exception types EX1–EX9 for the PoC | Business | superseded |
| [DEC-019](#dec-019) | 2026-11-28 | Customer agrees the PoC technology stack | Technical | confirmed |
| [DEC-020](#dec-020) | 2026-11-28 | PoC success criterion: all flows run successfully | Scope | confirmed |
| [DEC-021](#dec-021) | 2026-11-28 | Notification recipients by notification type | Business | confirmed |
| [DEC-022](#dec-022) | 2026-12-05 | Redis and SeaweedFS added to the PoC stack | Technical | confirmed |
| [DEC-023](#dec-023) | 2026-12-05 | Already invoiced quantity counts matched, approved and completed invoices | Business | confirmed |
| [DEC-024](#dec-024) | 2026-12-05 | Matching fields that trigger re-matching | Business | confirmed |
| [DEC-025](#dec-025) | 2026-12-05 | Demo scenario catalog defines "all flows" | Scope | superseded |
| [DEC-026](#dec-026) | 2026-12-05 | Product direction: multi-company AP system on AWS | Business | confirmed |
| [DEC-027](#dec-027) | 2026-12-05 | Meetings only when there are questions | Process | confirmed |
| [DEC-028](#dec-028) | 2026-12-05 | Code and documentation in one public GitHub repository | Process | confirmed |
| [DEC-029](#dec-029) | 2026-12-05 | Solution Architect is Tech Lead; Claude Code is the only developer | Project | confirmed |
| [DEC-030](#dec-030) | 2026-12-05 | Repository license: MIT | Business | confirmed |
| [DEC-031](#dec-031) | 2026-12-08 | Lines without a PO number on a PO invoice raise EX3 | Business | confirmed |
| [DEC-032](#dec-032) | 2026-12-08 | Invoice quantity must not exceed the expected quantity | Business | confirmed |
| [DEC-033](#dec-033) | 2026-12-08 | Exception types EX1–EX10 and demo scenarios DS-01 … DS-20 | Business | confirmed |
| [DEC-034](#dec-034) | 2026-12-08 | Match cumulatively per PO line; no DO / GR reference in the PoC | Scope | superseded |
| [DEC-035](#dec-035) | 2026-12-10 | Exception types that may be accepted as is | Business | confirmed |
| [DEC-036](#dec-036) | 2026-12-10 | Accounting Manager may release any claim | Business | confirmed |
| [DEC-037](#dec-037) | 2026-12-10 | Repeated exception after re-matching notifies the claimant only | Business | confirmed |
| [DEC-038](#dec-038) | 2026-12-11 | Any Accounting Manager may decide an approval; first decision is final | Business | confirmed |
| [DEC-039](#dec-039) | 2026-12-11 | No return for correction in the PoC; reject only | Scope | confirmed |
| [DEC-040](#dec-040) | 2026-12-11 | No notification on rejection in the PoC | Business | confirmed |
| [DEC-041](#dec-041) | 2026-12-11 | No four-eyes rule at final review in the PoC | Scope | superseded |
| [DEC-042](#dec-042) | 2026-12-14 | Normalize invoice numbers for duplicate detection | Business | confirmed |
| [DEC-043](#dec-043) | 2026-12-14 | Duplicate check ignores rejected invoices | Business | confirmed |
| [DEC-044](#dec-044) | 2026-12-15 | Dependency audit gate: runtime blocking, dev-only report when no fix exists | Process | confirmed |
| [DEC-045](#dec-045) | 2026-12-15 | Allowed values of the matching settings | Business | confirmed |
| [DEC-046](#dec-046) | 2026-12-15 | Only the last change of the matching settings is kept | Scope | confirmed |
| [DEC-047](#dec-047) | 2027-03-01 | PoC accepted | Project | confirmed |
| [DEC-048](#dec-048) | 2027-03-01 | [CR] Scope of Phase 2 | Scope | confirmed |
| [DEC-049](#dec-049) | 2027-03-01 | Single Sign-On with Keycloak | Technical | confirmed |
| [DEC-050](#dec-050) | 2027-03-01 | Phase 2 priorities; OCR / AI and AWS after the Phase 2 demo | Project | confirmed |
| [DEC-051](#dec-051) | 2027-03-01 | Phase 2 timeline and demo | Project | confirmed |
| [DEC-052](#dec-052) | 2027-03-01 | Phase 2 demo on 2027-08-30 | Project | confirmed |
| [DEC-053](#dec-053) | 2027-03-01 | Local Docker Compose environment for the Phase 2 demo | Technical | confirmed |
| [DEC-054](#dec-054) | 2027-03-01 | Users and roles managed in Keycloak | Business | confirmed |
| [DEC-055](#dec-055) | 2027-03-01 | Mailbox intake rules | Business | confirmed |
| [DEC-056](#dec-056) | 2027-03-01 | One company per user; settings, vendors and ERP data per company | Business | confirmed |
| [DEC-057](#dec-057) | 2027-03-01 | Invoice list and search rules | Business | confirmed |
| [DEC-058](#dec-058) | 2027-03-01 | Tenant data in one shared database with row-level security | Technical | confirmed |
| [DEC-059](#dec-059) | 2027-03-01 | One Keycloak realm with a group per company; Entra ID brokered later | Technical | confirmed |
| [DEC-060](#dec-060) | 2027-03-01 | Customers are subsidiaries of one group in several countries | Business | confirmed |
| [DEC-061](#dec-061) | 2027-03-01 | One shared Entra ID; one e-mail domain per subsidiary | Business | confirmed |
| [DEC-062](#dec-062) | 2027-03-01 | [CR] Processing calendar per company | Scope | confirmed |
| [DEC-063](#dec-063) | 2027-03-01 | [CR] Straight-through posting; no final review | Scope | confirmed |
| [DEC-064](#dec-064) | 2027-03-01 | Post invoices through an ERP posting port; mock posting; status Posted | Business | confirmed |
| [DEC-065](#dec-065) | 2027-03-01 | [CR] Trade PO invoices are matched per received lot (PO or DO number) | Scope | confirmed |
| [DEC-066](#dec-066) | 2027-03-01 | Trade PO unit price checked against the purchasing info record | Business | confirmed |
| [DEC-067](#dec-067) | 2027-03-01 | Dummy ERP data in Phase 2: open PO list, DO numbers, PIR prices | Scope | confirmed |
| [DEC-068](#dec-068) | 2027-03-01 | Exception types EX11 – EX13 | Business | confirmed |
| [DEC-069](#dec-069) | 2027-03-01 | DO number and invoice date are matching fields | Business | confirmed |
| [DEC-070](#dec-070) | 2027-03-01 | Posting to the ERP waits on closed days of the processing calendar | Business | confirmed |

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
| Supersedes / Superseded by | Extended to Phase 2 by [DEC-067](#dec-067) |

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
| Supersedes / Superseded by | Quantity rule partly superseded by [DEC-032](#dec-032); price reference for trade PO invoices partly superseded by [DEC-066](#dec-066) |

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
| Supersedes / Superseded by | Refined by [DEC-065](#dec-065) for trade PO invoices |

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
| Supersedes / Superseded by | Refined by [DEC-063](#dec-063) (re-run after the last exception is closed) |

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
| Supersedes / Superseded by | Partly superseded by [DEC-063](#dec-063) (no final review; approval stays, before posting) |

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
| Supersedes / Superseded by | Partly superseded by [DEC-063](#dec-063) (no rejection at final review) |

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
| Status | superseded |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) D8 |
| Impacts | [scope.md](scope.md) SCP-IN-04 |
| Supersedes / Superseded by | Superseded by [DEC-033](#dec-033) |

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
| Supersedes / Superseded by | Partly superseded by [DEC-063](#dec-063) (no final review notification) |

**Context:** Who receives in-app notifications was open (MTG-20261128 Q4).

**Decision:**

| Notification | Recipients |
|---|---|
| Invoice in status Exception | Accounting Members |
| Invoice waiting for approval (above the approval threshold) | Accounting Manager |
| Invoice ready for final review | Accounting Members |

**Rationale:** Stated by the Product Owner; matches the flow in §6.2.

**Consequences & follow-ups:** None.

### DEC-022
**Redis and SeaweedFS added to the PoC stack**

| Field | Value |
|---|---|
| Date | 2026-12-05 |
| Category | Technical |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) D1 |
| Impacts | [ADR-0004](../02-architecture/adr/0004-process-invoices-in-background-worker.md), [ADR-0006](../02-architecture/adr/0006-store-invoice-files-in-seaweedfs.md); extends [DEC-019](#dec-019) |
| Supersedes / Superseded by | — |

**Context:** ADR-0004 and ADR-0006 add Redis and SeaweedFS to the stack the customer agreed in DEC-019.

**Decision:** The customer agrees to Redis (SAPS Message Broker) and SeaweedFS (SAPS File Storage) in the PoC stack.

**Rationale:** Presented with the C4 L2 diagram; accepted by the Product Owner.

**Consequences & follow-ups:** None.

### DEC-023
**Already invoiced quantity counts matched, approved and completed invoices**

| Field | Value |
|---|---|
| Date | 2026-12-05 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) D2 |
| Impacts | [data-model.md §4.2](../02-architecture/data-model.md#42-external-entities-read-through-ports-not-stored); refines [DEC-007](#dec-007) |
| Supersedes / Superseded by | Refined by [DEC-064](#dec-064) (Posted counts) |

**Context:** Received-not-invoiced and PO-not-yet-invoiced quantities need an "already invoiced" quantity per PO line.
In SAP it grows only when an invoice is posted and is checked again at posting; the PoC has no posting step.

**Decision:** The already invoiced quantity of a PO line counts invoices in status PendingApproval, PendingReview or
Completed (option b). Invoices in Exception or Rejected do not count; a rejected invoice releases its quantity.

**Rationale:** Prevents two invoices from consuming the same quantity while both are in flight (the second one gets EX7).
This replaces the check at posting that the PoC does not have.

**Consequences & follow-ups:** An invoice in Exception does not reserve quantity; after its correction it can get EX7 if
another invoice was matched first.

### DEC-024
**Matching fields that trigger re-matching**

| Field | Value |
|---|---|
| Date | 2026-12-05 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) D3 |
| Impacts | [data-model.md](../02-architecture/data-model.md); refines [DEC-010](#dec-010) |
| Supersedes / Superseded by | Refined by [DEC-069](#dec-069) (invoice date and DO number added) |

**Context:** DEC-010 re-runs matching when a matching field changes; the field list was open.

**Decision:** Matching fields are: vendor code, invoice number, PO number, PO line number, quantity, unit price.
Changes to other fields (e.g. description, invoice date) do not trigger re-matching.

**Rationale:** These fields feed duplicate detection, type derivation and line matching.

**Consequences & follow-ups:** None.

### DEC-025
**Demo scenario catalog defines "all flows"**

| Field | Value |
|---|---|
| Date | 2026-12-05 |
| Category | Scope |
| Status | superseded |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) D4 |
| Impacts | [test-strategy.md §11](../05-testing/test-strategy.md#11-poc-demo-acceptance); refines [DEC-020](#dec-020) |
| Supersedes / Superseded by | Superseded by [DEC-033](#dec-033) |

**Context:** DEC-020 sets "all flows run successfully" as the PoC success criterion.

**Decision:** The demo scenario catalog DS-01 … DS-19 in the test strategy is the complete list of flows for the PoC demo.

**Rationale:** Confirmed by the Product Owner.

**Consequences & follow-ups:** Changes to the catalog need a new decision.

### DEC-026
**Product direction: multi-company AP system on AWS**

| Field | Value |
|---|---|
| Date | 2026-12-05 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) D5, R5, R6, R8 |
| Impacts | [scope.md](scope.md) BO1; [nfr.md](nfr.md) Workload Profile; [CON-06](../02-architecture/arc42/02-constraints.md); [ADR-0007](../02-architecture/adr/0007-prepare-data-model-for-tenants.md) |
| Supersedes / Superseded by | — |

**Context:** Business objectives, volume and cloud were open (MTG-20261114 Q3, Q5, Q27).

**Decision:** After the PoC, Smart-AP-Suite becomes an AP system serving many customer companies, deployed on AWS in the
Product Owner's company account (accounts given to the team when needed). Each company processes on average
1,000–2,000 invoices per day. The PoC serves one company with at most 1,000 invoices per day; this number is design
information only, not an acceptance criterion.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** The multi-tenancy model needs more analysis after the PoC; the PoC only prepares the data
model ([ADR-0007](../02-architecture/adr/0007-prepare-data-model-for-tenants.md)).

### DEC-027
**Meetings only when there are questions**

| Field | Value |
|---|---|
| Date | 2026-12-05 |
| Category | Process |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) D6 |
| Impacts | Meeting cadence until the demo on 2027-02-22 |
| Supersedes / Superseded by | — |

**Context:** Requirements for the PoC are mostly settled; weekly meetings were used so far.

**Decision:** There is no fixed weekly meeting. A meeting is held when there are questions for the Product Owner.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** Our team collects open questions and requests a meeting when needed.

### DEC-028
**Code and documentation in one public GitHub repository**

| Field | Value |
|---|---|
| Date | 2026-12-05 |
| Category | Process |
| Status | confirmed |
| Decided by | Solution Architect (our company) |
| Source | Solution Architect, written answer to [Developer Guide](../04-development/developer-guide.md#12-open-questions) Q1 |
| Impacts | [Developer Guide](../04-development/developer-guide.md) §1, §2.2, §4.5 |
| Supersedes / Superseded by | — |

**Context:** Code hosting and the relation between code and documentation were open.

**Decision:** Code and documentation live in one public GitHub repository: https://github.com/jiri-nguyen/SAPS.

**Rationale:** Stated by the Solution Architect.

**Consequences & follow-ups:** Everything committed is public: no secrets, real customer or vendor data, real invoices or
confidential information in code or docs. Secret scanning, push protection and branch protection are turned on.
The repository license is open (Developer Guide Q4).

### DEC-029
**Solution Architect is Tech Lead; Claude Code is the only developer**

| Field | Value |
|---|---|
| Date | 2026-12-05 |
| Category | Project |
| Status | confirmed |
| Decided by | Solution Architect (our company) |
| Source | Solution Architect, written answer to [Developer Guide](../04-development/developer-guide.md#12-open-questions) Q2 |
| Impacts | [Developer Guide](../04-development/developer-guide.md) §4.3, §4.6; [Test Strategy](../05-testing/test-strategy.md) §12 |
| Supersedes / Superseded by | — |

**Context:** Tech Lead and developer roles were open.

**Decision:** The Solution Architect also acts as Tech Lead (and QA, see the test strategy). Claude Code is the only developer.

**Rationale:** Stated by the Solution Architect.

**Consequences & follow-ups:** Claude Code writes code and opens pull requests; the Solution Architect / Tech Lead reviews and merges every pull request.

### DEC-030
**Repository license: MIT**

| Field | Value |
|---|---|
| Date | 2026-12-05 |
| Category | Business |
| Status | confirmed |
| Decided by | Solution Architect (our company) |
| Source | Solution Architect, written answer to [Developer Guide](../04-development/developer-guide.md#12-open-questions) Q4 |
| Impacts | `LICENSE` in the repository root; [Developer Guide](../04-development/developer-guide.md) §5.6 |
| Supersedes / Superseded by | — |

**Context:** The repository is public ([DEC-028](#dec-028)). The Solution Architect wants a license that allows commercial use
with no restrictions related to the source code.

**Decision:** The repository is licensed under the MIT License.

**Rationale:** MIT is a permissive license: commercial use, modification and closed-source distribution are allowed; the only
condition is to keep the copyright and license notice. Copyleft licenses (GPL, AGPL) were excluded because they require
publishing source code. Apache-2.0 was the alternative (adds an explicit patent grant, but more conditions).

**Consequences & follow-ups:** Anyone, including competitors, may also use the published code commercially. The copyright holder
can still license future versions differently; code already published under MIT stays under MIT. Dependencies must stay
compatible: no AGPL / SSPL in shipped code (Developer Guide §5.6).

### DEC-031
**Lines without a PO number on a PO invoice raise EX3**

| Field | Value |
|---|---|
| Date | 2026-12-08 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261208](meetings/2026-12-08-matching-rules.md) D1 |
| Impacts | [SAPS-19](../03-features/SAPS-19-invoice-matching.md) BR-02; refines [DEC-005](#dec-005) |
| Supersedes / Superseded by | — |

**Context:** DEC-005 derives the invoice type from PO numbers but did not cover invoices where only some lines carry a PO number.

**Decision:** On an invoice where at least one line has a PO number, every line without a PO number raises EX3.
The invoice type comes from the lines with a PO number.

**Rationale:** Proposed by the SA; accepted by the Product Owner.

**Consequences & follow-ups:** None.

### DEC-032
**Invoice quantity must not exceed the expected quantity**

| Field | Value |
|---|---|
| Date | 2026-12-08 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261208](meetings/2026-12-08-matching-rules.md) D2 |
| Impacts | [SAPS-19](../03-features/SAPS-19-invoice-matching.md) BR-09; partly supersedes [DEC-006](#dec-006) (quantity rule); refines [DEC-007](#dec-007) |
| Supersedes / Superseded by | Partly supersedes [DEC-006](#dec-006) (quantity rule only); refined by [DEC-065](#dec-065) (per lot) |

**Context:** DEC-006 said "quantity must match exactly", DEC-007 said "above it → exception"; the two readings differ for partial invoicing.

**Decision:** The invoice quantity of a PO line must not exceed the expected quantity: received-not-invoiced quantity
(3-way) or PO quantity not yet invoiced (2-way). A smaller quantity passes (partial invoicing). A larger quantity raises EX7.

**Rationale:** Standard AP practice: one PO is often invoiced in several parts; only over-invoicing is blocked. The
Product Owner first chose exact matching, then changed to this rule after the SA explained the practice ([MTG-20261208](meetings/2026-12-08-matching-rules.md) §5.2).

**Consequences & follow-ups:** The remaining quantity stays available for later invoices of the same PO line.

### DEC-033
**Exception types EX1–EX10 and demo scenarios DS-01 … DS-20**

| Field | Value |
|---|---|
| Date | 2026-12-08 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261208](meetings/2026-12-08-matching-rules.md) D3 |
| Impacts | [scope.md](scope.md) SCP-IN-04; [SAPS-19](../03-features/SAPS-19-invoice-matching.md); [saps-api.openapi.yaml](../02-architecture/api/saps-api.openapi.yaml); [test-strategy.md §11](../05-testing/test-strategy.md#11-poc-demo-acceptance) |
| Supersedes / Superseded by | Supersedes [DEC-018](#dec-018) and [DEC-025](#dec-025); extended by [DEC-068](#dec-068) |

**Context:** The vendor on an invoice can differ from the vendor of the PO it refers to; EX1–EX9 had no type for this.

**Decision:** The PoC supports these exception types:

| Code | Exception |
|---|---|
| EX1 | Invoice unreadable: extraction failed or file not in the dummy sample set |
| EX2 | Non-PO invoice (manual review) |
| EX3 | Invalid or missing PO number (not 7 digits, prefix other than 0 / 1, or no PO number on a PO invoice line — DEC-031) |
| EX4 | PO or PO line not found |
| EX5 | Trade and non-trade POs on one invoice |
| EX6 | Unit price outside tolerance |
| EX7 | Quantity above the expected quantity (DEC-032) |
| EX8 | Missing goods receipt |
| EX9 | Duplicate invoice |
| EX10 | Vendor does not match the PO |

The demo scenario catalog DS-01 … DS-20 in the test strategy (DS-20 covers EX10) is the complete list of flows for the PoC demo.

**Rationale:** Chosen by the Product Owner over reusing EX4: a dedicated type is clearer for the Accounting Member.

**Consequences & follow-ups:** Changes to the exception list or the catalog need a new decision.

### DEC-034
**Match cumulatively per PO line; no DO / GR reference in the PoC**

| Field | Value |
|---|---|
| Date | 2026-12-08 |
| Category | Scope |
| Status | superseded |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261208](meetings/2026-12-08-matching-rules.md) D4 |
| Impacts | [scope.md](scope.md) SCP-OUT-13; [SAPS-19](../03-features/SAPS-19-invoice-matching.md); confirms [DEC-007](#dec-007) |
| Supersedes / Superseded by | Superseded by [DEC-065](#dec-065) |

**Context:** Matching can be cumulative per PO line, or GR-based (each invoice line references a goods receipt or delivery order).

**Decision:** The PoC matches cumulatively per PO line (sum of goods receipts minus already invoiced quantity).
Invoices carry no delivery order (DO) or goods receipt (GR) reference. GR-based invoice verification is a candidate after the PoC.

**Rationale:** Simpler extraction and matching; enough for the demo scenarios.

**Consequences & follow-ups:** Deliveries of the same PO line at different prices cannot be told apart in the PoC.

### DEC-035
**Exception types that may be accepted as is**

| Field | Value |
|---|---|
| Date | 2026-12-10 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261210](meetings/2026-12-10-exception-handling-rules.md) D1 |
| Impacts | [SAPS-20](../03-features/SAPS-20-exception-handling.md) BR-06; `resolveInvoiceExceptions` in [saps-api.openapi.yaml](../02-architecture/api/saps-api.openapi.yaml) |
| Supersedes / Superseded by | Refined by [DEC-063](#dec-063) (accepted exceptions on a re-run) |

**Context:** An Accounting Member can correct the data, accept the invoice as is, or reject it. Which exception types
allow acceptance without correction was open.

**Decision:** An invoice can be accepted as is only when every open exception is one of:

| Code | May be accepted as is |
|---|---|
| EX2 Non-PO invoice | Yes (manual review is the only path) |
| EX6 Unit price outside tolerance | Yes |
| EX7 Quantity above the expected quantity | Yes |
| EX9 Duplicate invoice (found not to be a duplicate) | Yes |
| EX1, EX3, EX4, EX5, EX8, EX10 | No — correct the data or reject |

Accepted invoices above the approval threshold still need Accounting Manager approval ([DEC-009](#dec-009), [DEC-013](#dec-013)).

**Rationale:** Price and quantity variances can be accepted by an authorized person (common AP practice); errors in the
source data (PO, vendor, goods receipt) must be corrected.

**Consequences & follow-ups:** None.

### DEC-036
**Accounting Manager may release any claim**

| Field | Value |
|---|---|
| Date | 2026-12-10 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261210](meetings/2026-12-10-exception-handling-rules.md) D2 |
| Impacts | [SAPS-20](../03-features/SAPS-20-exception-handling.md) BR-03; `releaseInvoiceClaim`; refines [DEC-016](#dec-016) |
| Supersedes / Superseded by | — |

**Context:** A claimed invoice is blocked when the claimant is absent.

**Decision:** The claimant can release their own claim; an Accounting Manager can release any claim. The invoice returns
to the shared exception queue.

**Rationale:** Proposed by the SA; accepted by the Product Owner.

**Consequences & follow-ups:** None.

### DEC-037
**Repeated exception after re-matching notifies the claimant only**

| Field | Value |
|---|---|
| Date | 2026-12-10 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261210](meetings/2026-12-10-exception-handling-rules.md) D3 |
| Impacts | [SAPS-20](../03-features/SAPS-20-exception-handling.md) BR-10; refines [DEC-021](#dec-021) |
| Supersedes / Superseded by | — |

**Context:** DEC-021 sends exception notifications to Accounting Members. After re-matching, the invoice is still claimed.

**Decision:** When re-matching of a claimed invoice raises exceptions again, only the claimant is notified. A new
exception on an unclaimed invoice still notifies all Accounting Members.

**Rationale:** Only the claimant can act on the invoice; notifying everyone would be noise.

**Consequences & follow-ups:** None.

### DEC-038
**Any Accounting Manager may decide an approval; first decision is final**

| Field | Value |
|---|---|
| Date | 2026-12-11 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261211](meetings/2026-12-11-approval-review-rules.md) D1 |
| Impacts | [SAPS-22](../03-features/SAPS-22-invoice-approval.md) BR-03; refines [DEC-009](#dec-009) |
| Supersedes / Superseded by | — |

**Context:** A tenant can have several Accounting Managers; who decides an approval was open.

**Decision:** Any Accounting Manager of the tenant may approve or reject an invoice in PendingApproval. The first decision is final; a later attempt is refused.

**Rationale:** Same shared-queue approach as for exceptions (DEC-016); no assignment needed.

**Consequences & follow-ups:** None.

### DEC-039
**No return for correction in the PoC; reject only**

| Field | Value |
|---|---|
| Date | 2026-12-11 |
| Category | Scope |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261211](meetings/2026-12-11-approval-review-rules.md) D2 |
| Impacts | [SAPS-22](../03-features/SAPS-22-invoice-approval.md) BR-06; [SAPS-21](../03-features/SAPS-21-final-result-review.md) BR-05; [SCP-OUT-14](scope.md#4-out-of-scope); refines [DEC-014](#dec-014) |
| Supersedes / Superseded by | — |

**Context:** An approver or reviewer may find a correctable error; returning the invoice to Exception was an option.

**Decision:** At approval and at final review, the only alternative to approving or confirming is rejection. Return for correction is a candidate after the PoC.

**Rationale:** Keeps the PoC lifecycle and API unchanged; the Product Owner agreed it fits a real product later.

**Consequences & follow-ups:** A corrected invoice must be uploaded again.

### DEC-040
**No notification on rejection in the PoC**

| Field | Value |
|---|---|
| Date | 2026-12-11 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20261211](meetings/2026-12-11-approval-review-rules.md) D3 |
| Impacts | [SAPS-22](../03-features/SAPS-22-invoice-approval.md) BR-05; [SAPS-21](../03-features/SAPS-21-final-result-review.md) BR-04; refines [DEC-021](#dec-021) |
| Supersedes / Superseded by | — |

**Context:** DEC-021 defines notifications for exceptions, approvals and reviews, not for rejections.

**Decision:** No notification is sent when an invoice is rejected. Status Rejected and the reason stay visible in the invoice list.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** None.

### DEC-041
**No four-eyes rule at final review in the PoC**

| Field | Value |
|---|---|
| Date | 2026-12-11 |
| Category | Scope |
| Status | superseded |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261211](meetings/2026-12-11-approval-review-rules.md) D4 |
| Impacts | [SAPS-21](../03-features/SAPS-21-final-result-review.md) BR-02; [SCP-OUT-15](scope.md#4-out-of-scope) |
| Supersedes / Superseded by | Superseded by [DEC-063](#dec-063) (no final review) |

**Context:** Segregation of duties would forbid the member who uploaded an invoice or accepted its exceptions from confirming it.

**Decision:** Any Accounting Member may confirm an invoice at final review, including the member who uploaded it or accepted its exceptions. A four-eyes rule is a candidate after the PoC.

**Rationale:** The PoC has only a few demo users; the control matters for production.

**Consequences & follow-ups:** One person can take an invoice below the approval threshold from upload to Completed in the PoC.

### DEC-042
**Normalize invoice numbers for duplicate detection**

| Field | Value |
|---|---|
| Date | 2026-12-14 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261214](meetings/2026-12-14-duplicate-detection-rules.md) D1 |
| Impacts | [SAPS-23](../03-features/SAPS-23-duplicate-invoice-detection.md) BR-02; [data model](../02-architecture/data-model.md#invoice) `invoice_number_normalized`; refines [DEC-008](#dec-008) |
| Supersedes / Superseded by | — |

**Context:** The same invoice number can be written differently ("INV-0001", "INV0001", "inv 0001"); an exact comparison misses such duplicates.

**Decision:** Before comparing, invoice numbers are normalized: case is ignored; spaces, `-`, `.` and `/` are removed;
leading zeros are kept ("INV-0001" and "INV-001" stay different).

**Rationale:** Catches more real duplicates; false positives are harmless because EX9 may be accepted as is ([DEC-035](#dec-035)).

**Consequences & follow-ups:** None.

### DEC-043
**Duplicate check ignores rejected invoices**

| Field | Value |
|---|---|
| Date | 2026-12-14 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261214](meetings/2026-12-14-duplicate-detection-rules.md) D2 |
| Impacts | [SAPS-23](../03-features/SAPS-23-duplicate-invoice-detection.md) BR-03; refines [DEC-008](#dec-008) |
| Supersedes / Superseded by | — |

**Context:** A corrected invoice is uploaded again with the same number after a rejection ([DEC-039](#dec-039)); comparing
it with the rejected invoice would always raise EX9.

**Decision:** Invoices in status Rejected are not compared by the duplicate check.

**Rationale:** A rejected invoice is never paid, so ignoring it creates no double-payment risk.

**Consequences & follow-ups:** None.

### DEC-044
**Dependency audit gate: runtime blocking, dev-only report when no fix exists**

| Field | Value |
|---|---|
| Date | 2026-12-15 |
| Category | Process |
| Status | confirmed |
| Decided by | Solution Architect / Tech Lead (our company) |
| Source | Solution Architect, written approval during [SAPS-26](https://linear.app/jiringuyen/issue/SAPS-26) (CI set-up), 2026-12-15 |
| Impacts | [Test Strategy §5, §10](../05-testing/test-strategy.md#5-quality-gates); `.github/workflows/ci.yml` |
| Supersedes / Superseded by | — |

**Context:** The PR gate required "no high findings from dependency scan". At SAPS-26, `npm audit` reported 13 high
findings, all caused by one ReDoS advisory in `picomatch` (≤ 4.0.7) pulled in by dev tools (Vite, Vitest,
typescript-eslint). No fixed version exists; npm suggested downgrading major versions. Runtime dependencies were clean.

**Decision:** High findings in runtime dependencies block the pull request (pip-audit; `npm audit --omit=dev`).
High findings in dev-only dependencies are reported but do not block when no fixed version is available.
Python SAST uses Ruff's security rules (`S`, ported from Bandit) instead of a separate Bandit run.

**Rationale:** Dev tools do not ship in the SAPS Web App image and process only trusted project files; blocking every
PR on an unfixable dev-tool advisory gives no security benefit.

**Consequences & follow-ups:** Findings are rechecked with each weekly Dependabot update; when a fix exists, it is applied.

### DEC-045
**Allowed values of the matching settings**

| Field | Value |
|---|---|
| Date | 2026-12-15 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261215](meetings/2026-12-15-matching-settings-rules.md) D1 |
| Impacts | [SAPS-28](../03-features/SAPS-28-matching-settings.md) BR-03, EC-02, EC-03; refines [DEC-015](#dec-015) |
| Supersedes / Superseded by | — |

**Context:** [DEC-015](#dec-015) makes the price tolerance and the approval threshold settings but does not say which
values are allowed.

**Decision:** The price tolerance is 0 USD or more, with up to 4 decimals. The approval threshold is 0 USD or more, with
up to 2 decimals. There is no upper limit for either. A value with too many decimals is refused with `400`; a negative
value is refused with `422` naming the field.

**Rationale:** 0 is a valid business choice (the unit price must equal the PO price; every invoice with a positive total
needs approval). The decimals match the stored columns of
[MatchingSettings](../02-architecture/data-model.md#matchingsettings).

**Consequences & follow-ups:** None.

### DEC-046
**Only the last change of the matching settings is kept**

| Field | Value |
|---|---|
| Date | 2026-12-15 |
| Category | Scope |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20261215](meetings/2026-12-15-matching-settings-rules.md) D2 |
| Impacts | [SAPS-28](../03-features/SAPS-28-matching-settings.md) BR-05; data model unchanged; refines [DEC-015](#dec-015) |
| Supersedes / Superseded by | — |

**Context:** The Matching settings screen shows who changed the settings and when. A full history of changes would need a
new entity and a history screen.

**Decision:** In the PoC, only the last change is kept (`updated_by`, `updated_at` on MatchingSettings). There is no
history of changes and no history screen. The application log records the old and new values of each change
(`matching_settings_updated`).

**Rationale:** The settings change rarely; the log is enough for the PoC.

**Consequences & follow-ups:** A history of changes may be requested after the PoC; it would add a new entity.

### DEC-047
**PoC accepted**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Project |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) D1, R1 |
| Impacts | [scope.md](scope.md) BO2, SCP-IN-11 |
| Supersedes / Superseded by | — |

**Context:** The PoC demo of all scenarios of the demo scenario catalog took place ([Test Strategy §11](../05-testing/test-strategy.md#11-poc-demo-acceptance)).

**Decision:** The Product Owner accepts the PoC: BO2 is met.

**Rationale:** Stated by the Product Owner, the sign-off owner ([DEC-011](#dec-011)).

**Consequences & follow-ups:** Phase 2 starts ([DEC-051](#dec-051)).


### DEC-048
**[CR] Scope of Phase 2**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Scope |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) D2, R3, R4, R9 |
| Impacts | [scope.md](scope.md) version 0.7: SCP-IN-15 to SCP-IN-22; SCP-OUT-02, -07, -08, -10, -11, -12, -13 withdrawn (moved); SCP-OUT-01, -09 changed |
| Supersedes / Superseded by | — |

**Context:** After the PoC, the Product Owner names the items of Phase 2. Most were out of the PoC scope (SCP-OUT). Users also miss a view of invoices that finished processing: Completed and Rejected invoices disappear from the Web App.

**Decision:** In scope of Phase 2: ERP integration via MuleSoft (from SCP-OUT-02), automated checks for non-PO invoices (SCP-OUT-07), posting results to the ERP or exporting them (SCP-OUT-08), Single Sign-On (SCP-OUT-10, [DEC-049](#dec-049)), invoice intake from a mailbox (SCP-OUT-11), multi-tenancy (SCP-OUT-12), GR-based invoice verification (SCP-OUT-13), and the new invoice list and search. Real extraction with OCR / AI (SCP-OUT-01) and cloud deployment (SCP-OUT-09) stay out until after the Phase 2 demo ([DEC-050](#dec-050)). SCP-OUT-03, -04, -05, -06, -14 and -15 stay out.

**Rationale:** Stated by the Product Owner; OCR / AI and AWS are not available to the Product Owner yet.

**Consequences & follow-ups:** Linear issues for the new scope items (listed by the team, created by the Solution Architect). Feature specs and ADRs for SSO, mailbox intake and multi-tenancy first. Open questions in [MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) Q1–Q12.


### DEC-049
**Single Sign-On with Keycloak**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Technical |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) D3, R3 |
| Impacts | SCP-IN-18; [ADR-0008](../02-architecture/adr/0008-use-session-cookies-for-authentication.md) (to be superseded in part by a new ADR); [NFR-SEC-001](nfr.md#nfr-sec-001) (new version); SCP-IN-12 |
| Supersedes / Superseded by | — |

**Context:** The PoC signs users in with simple accounts stored in the SAPS Database ([ADR-0008](../02-architecture/adr/0008-use-session-cookies-for-authentication.md)).

**Decision:** Single Sign-On uses Keycloak.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** A new ADR describes the sign-in with Keycloak (protocol, roles, sessions, Origin check). Who runs Keycloak and the realm per company are open ([MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) Q3).


### DEC-050
**Phase 2 priorities; OCR / AI and AWS after the Phase 2 demo**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Project |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) D4, R5, R9 |
| Impacts | [scope.md](scope.md) SCP-OUT-01, SCP-OUT-09, priorities of SCP-IN-15 to -22; refines the timing of [DEC-026](#dec-026); [NFR-MAINT-001](nfr.md#nfr-maint-001) |
| Supersedes / Superseded by | — |

**Context:** The Product Owner has no AWS account and no OCR / AI extraction service yet; a working end-to-end flow for several companies matters more.

**Decision:** Single Sign-On (Keycloak), invoice intake from a mailbox and multi-tenancy are built first. Real extraction with OCR / AI and the deployment on AWS move after the Phase 2 demo. The design of Phase 2 must make it easy to add both later.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** The direction of [DEC-026](#dec-026) (AWS, many companies) is unchanged; only its timing moves. The design requirement is [NFR-MAINT-001](nfr.md#nfr-maint-001). Priority of the other Phase 2 items is open ([MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) Q6, Q7).


### DEC-051
**Phase 2 timeline and demo**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Project |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) D5, R2, R6 |
| Impacts | [scope.md](scope.md) BO3; [Test Strategy](../05-testing/test-strategy.md) (Phase 2 demo scenarios, later) |
| Supersedes / Superseded by | — |

**Context:** The PoC ended with one demo and no interim release ([DEC-017](#dec-017)).

**Decision:** Phase 2 starts on 2027-03-01 and lasts about 6 months. It ends with a demo of the new features; no interim release is planned.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** The demo date, the go-live date and the budget are open ([MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) Q1).

### DEC-052
**Phase 2 demo on 2027-08-30**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Project |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-2](meetings/2027-03-01-phase-2-requirements.md) D1, R1 |
| Impacts | [scope.md](scope.md) BO3; refines [DEC-051](#dec-051) |
| Supersedes / Superseded by | — |

**Context:** [DEC-051](#dec-051) set the start and the length of Phase 2 but not the demo date.

**Decision:** The Phase 2 demo takes place on 2027-08-30. The go-live date is decided later.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** Go-live date and budget stay open ([MTG-20270301-2](meetings/2027-03-01-phase-2-requirements.md) Q1).


### DEC-053
**Local Docker Compose environment for the Phase 2 demo**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Technical |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-2](meetings/2027-03-01-phase-2-requirements.md) D2, R2 |
| Impacts | [scope.md](scope.md) SCP-IN-10; arc42 §7 Deployment View |
| Supersedes / Superseded by | — |

**Context:** AWS moves after the Phase 2 demo ([DEC-050](#dec-050)); the PoC ran locally with Docker Compose ([DEC-003](#dec-003)).

**Decision:** The Phase 2 demo runs locally with Docker Compose like the PoC, extended with a Keycloak container and a local test mail server. The deployment on AWS follows after the demo.

**Rationale:** Proposed by the Solution Architect, accepted by the Product Owner; keeps the Phase 2 design ready for AWS ([NFR-MAINT-001](nfr.md#nfr-maint-001)).

**Consequences & follow-ups:** Keycloak and the test mail server are added to `compose.yaml`; the choice of the test mail server is part of the mailbox intake ADR.


### DEC-054
**Users and roles managed in Keycloak**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-2](meetings/2027-03-01-phase-2-requirements.md) D3, R3 |
| Impacts | [scope.md](scope.md) SCP-IN-18; [DEC-049](#dec-049) |
| Supersedes / Superseded by | — |

**Context:** Single Sign-On uses Keycloak ([DEC-049](#dec-049)); the PoC created demo users with a seed script.

**Decision:** The team runs Keycloak for the Phase 2 demo. Users and their roles (Accounting Member, Accounting Manager) are managed in the Keycloak admin console. The Web App has no user management screens and no system administrator role that sees all companies in Phase 2.

**Rationale:** Proposed by the Solution Architect, accepted by the Product Owner.

**Consequences & follow-ups:** One realm for all companies or one per company is open ([MTG-20270301-2](meetings/2027-03-01-phase-2-requirements.md) Q2).


### DEC-055
**Mailbox intake rules**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-2](meetings/2027-03-01-phase-2-requirements.md) D4, R4 |
| Impacts | [scope.md](scope.md) SCP-IN-19 |
| Supersedes / Superseded by | — |

**Context:** Invoices can arrive by mail in Phase 2 ([DEC-048](#dec-048)).

**Decision:** Each company has its own mailbox; the real mail system later is Outlook (Microsoft 365). The mailbox that receives a mail tells the company of its invoices. Only PDF, PNG and JPG attachments are taken; each attachment is one invoice. A mail without a valid attachment is skipped and logged. The sender is not checked in Phase 2.

**Rationale:** Stated by the Product Owner; formats and the handling of mails without invoices proposed by the Solution Architect and accepted.

**Consequences & follow-ups:** An ADR chooses the mail access (Microsoft Graph for Outlook, a local test mail server for the demo, both behind a port).


### DEC-056
**One company per user; settings, vendors and ERP data per company**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-2](meetings/2027-03-01-phase-2-requirements.md) D5, R5 |
| Impacts | [scope.md](scope.md) SCP-IN-20, SCP-IN-09, SCP-IN-13; [ADR-0007](../02-architecture/adr/0007-prepare-data-model-for-tenants.md) |
| Supersedes / Superseded by | — |

**Context:** The system serves several companies in Phase 2 ([DEC-048](#dec-048)); the PoC data model already carries a tenant on every table ([ADR-0007](../02-architecture/adr/0007-prepare-data-model-for-tenants.md)).

**Decision:** A user belongs to exactly one company. Matching settings, vendors and ERP data are kept per company.

**Rationale:** Stated by the Product Owner; settings, vendors and ERP data per company proposed by the Solution Architect and accepted.

**Consequences & follow-ups:** The dummy ERP data must be split per company until the ERP integration (SCP-IN-15). The database model is open ([MTG-20270301-2](meetings/2027-03-01-phase-2-requirements.md) Q3).


### DEC-057
**Invoice list and search rules**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-2](meetings/2027-03-01-phase-2-requirements.md) D6, R6 |
| Impacts | [scope.md](scope.md) SCP-IN-22 |
| Supersedes / Superseded by | — |

**Context:** Completed and Rejected invoices disappear from the Web App ([DEC-048](#dec-048)).

**Decision:** Accounting Members and Accounting Managers see all invoices of their own company in every status. Filters: status, vendor, invoice number, invoice date range, upload date range, total amount range, PO number and intake channel (upload or mail). Newest first, 20 per page. No export.

**Rationale:** Proposed by the Solution Architect, accepted by the Product Owner.

**Consequences & follow-ups:** A feature spec describes the screen and the API (`listInvoices` filters).

### DEC-058
**Tenant data in one shared database with row-level security**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Technical |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20270301-3](meetings/2027-03-01-tenancy-and-identity.md) D1, R1 |
| Impacts | [ADR-0009](../02-architecture/adr/0009-isolate-tenant-data-in-a-shared-database.md); [scope.md](scope.md) SCP-IN-20; TD-02 |
| Supersedes / Superseded by | — |

**Context:** The database model for several companies was open ([MTG-20270301-2](meetings/2027-03-01-phase-2-requirements.md) Q3); the options are in [ADR-0009](../02-architecture/adr/0009-isolate-tenant-data-in-a-shared-database.md).

**Decision:** All companies share one database; every tenant-owned table keeps `tenant_id` and gets PostgreSQL row-level security in addition to the filter in the application ([ADR-0009](../02-architecture/adr/0009-isolate-tenant-data-in-a-shared-database.md)).

**Rationale:** No legal need for physical separation, the same retention and infrastructure for all subsidiaries, and more subsidiaries later ([DEC-060](#dec-060)): the shared model costs the least and builds on the PoC data.

**Consequences & follow-ups:** If data-residency rules or customers outside the group appear, the same stack is deployed per region or per customer group. Data residency is open ([MTG-20270301-3](meetings/2027-03-01-tenancy-and-identity.md) Q1).


### DEC-059
**One Keycloak realm with a group per company; Entra ID brokered later**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Technical |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20270301-3](meetings/2027-03-01-tenancy-and-identity.md) D2, R3 |
| Impacts | [ADR-0010](../02-architecture/adr/0010-use-one-keycloak-realm-with-company-groups.md); [scope.md](scope.md) SCP-IN-18; [DEC-054](#dec-054) |
| Supersedes / Superseded by | — |

**Context:** One Keycloak realm or one per company was open ([MTG-20270301-2](meetings/2027-03-01-phase-2-requirements.md) Q2); all subsidiaries share one Entra ID ([DEC-061](#dec-061)).

**Decision:** One Keycloak realm; one group per company; roles Accounting Member and Accounting Manager as realm roles. The SAPS API accepts a user only with exactly one company group whose e-mail domain matches. Microsoft Entra ID is added later as an identity provider of the realm (Keycloak stays the broker), so the SAPS code does not change ([ADR-0010](../02-architecture/adr/0010-use-one-keycloak-realm-with-company-groups.md)).

**Rationale:** With one shared Entra ID, realms or Organizations per company bring no benefit; groups are the simplest model to manage in the admin console.

**Consequences & follow-ups:** The sign-in flow of the SAPS Web App with Keycloak is a separate ADR.


### DEC-060
**Customers are subsidiaries of one group in several countries**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-3](meetings/2027-03-01-tenancy-and-identity.md) D3, R2 |
| Impacts | Refines [DEC-026](#dec-026); [ADR-0009](../02-architecture/adr/0009-isolate-tenant-data-in-a-shared-database.md); [nfr.md](nfr.md) Workload Profile |
| Supersedes / Superseded by | — |

**Context:** [DEC-026](#dec-026) describes the product as an AP system for many customer companies.

**Decision:** The companies served are subsidiaries of one group, in several countries: about 3 now, more subsidiaries later. There is no legal or contractual need to keep a subsidiary's data physically apart, no plan to sell or split off a subsidiary, no group-wide reporting across subsidiaries, and the same retention and infrastructure for all. Customers outside the group are a possible later direction, not certain.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** Whether the countries require invoice data to stay in the country is open ([MTG-20270301-3](meetings/2027-03-01-tenancy-and-identity.md) Q1).


### DEC-061
**One shared Entra ID; one e-mail domain per subsidiary**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-3](meetings/2027-03-01-tenancy-and-identity.md) D4, R3 |
| Impacts | [ADR-0010](../02-architecture/adr/0010-use-one-keycloak-realm-with-company-groups.md); [DEC-049](#dec-049), [DEC-054](#dec-054) |
| Supersedes / Superseded by | — |

**Context:** Single Sign-On uses Keycloak ([DEC-049](#dec-049)); the group's own identity system was not known.

**Decision:** All subsidiaries sign in with one shared Microsoft Entra ID of the group. Each subsidiary has its own e-mail domain (for example `vn.xxx.com`, `sg.xxx.com`). Integration with Entra ID comes in a later phase; the Phase 2 demo uses local Keycloak users.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** The e-mail domain of a user identifies the subsidiary and is checked by the SAPS API ([DEC-059](#dec-059)).

### DEC-062
**[CR] Processing calendar per company**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Scope |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20270301-4](meetings/2027-03-01-processing-calendar.md) D1, R1 |
| Impacts | [scope.md](scope.md) version 0.9: SCP-IN-23; invoice lifecycle (new status On hold); [SAPS-37](../03-features/SAPS-37-stuck-invoice-sweeper.md) sweeper; Phase 2 demo scenarios ([SAPS-47](https://linear.app/jiringuyen/issue/SAPS-47)) |
| Supersedes / Superseded by | Refined by [DEC-070](#dec-070) (posting is held too) |

**Context:** The Product Owner wants companies to stop invoice processing in some periods, for example from the 25th of a
month to the 5th of the next month, and on weekends. This was not in the Phase 2 scope ([DEC-048](#dec-048)).

**Decision:** Accounting Managers set a processing calendar for their company:
- Rule types: monthly day ranges (e.g. 25th → 5th of the next month), weekdays, and specific dates; in the company's local time zone; no times of day.
- In a closed period, new invoices (upload or mail) are received but held with the new status On hold. Invoices already in exception handling, approval or final review are worked on as usual.
- When the period ends, held invoices are processed automatically, oldest first. An Accounting Manager can release one held invoice at once ("process now").
- The Web App shows a banner for a closed period; no notification when a period starts or ends.
- Only the Accounting Manager of the company changes its calendar; changes apply at once, also to held invoices.
- Part of the demo on 2027-08-30; built after the invoice list and search ([SAPS-46](https://linear.app/jiringuyen/issue/SAPS-46)).

**Rationale:** Requested by the Product Owner; the details are the team's proposals, accepted in [MTG-20270301-4](meetings/2027-03-01-processing-calendar.md) (Q1–Q9).

**Consequences & follow-ups:** Feature spec and Linear issue [SAPS-52](https://linear.app/jiringuyen/issue/SAPS-52). The
new status On hold changes the invoice lifecycle; the sweeper ignores held invoices.

### DEC-063
**[CR] Straight-through posting; no final review**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Scope |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-9](meetings/2027-03-01-po-invoice-posting-and-matching.md) D1, R2, R11, R12, Q1 – Q3, Q12, Q13 |
| Impacts | [scope.md](scope.md) version 0.10: SCP-IN-03, -04, -05 (withdrawn), -06, -08, -14, -17; [SAPS-21](../03-features/SAPS-21-final-result-review.md), [SAPS-20](../03-features/SAPS-20-exception-handling.md), [SAPS-22](../03-features/SAPS-22-invoice-approval.md); invoice lifecycle; [SAPS-49](https://linear.app/jiringuyen/issue/SAPS-49) |
| Supersedes / Superseded by | Supersedes [DEC-041](#dec-041); partly supersedes [DEC-013](#dec-013) (order with final review), [DEC-014](#dec-014) (rejection at final review), [DEC-021](#dec-021) (final review notification); refines [DEC-010](#dec-010), [DEC-035](#dec-035) |

**Context:** Every invoice ends at a final review by an Accounting Member ([DEC-013](#dec-013)). The Product Owner wants invoices
without problems, or whose problems were corrected, posted to the ERP without anybody reviewing them.

**Decision:**
- The workflow ends with posting to the ERP ([DEC-064](#dec-064)) for every invoice type. There is no final review any more.
- An invoice whose workflow passes is posted automatically. Above the approval threshold it is posted after the
  Accounting Manager approves ([DEC-009](#dec-009) stays).
- When an Accounting Member closes the last open exception (correction or acceptance as is), the workflow runs again
  with fresh ERP data. If it passes, the invoice is posted automatically (or goes to approval). Non-PO invoices are
  posted after the manual review (EX2) in the same way.
- "Workflow" here means the processing after extraction: duplicate detection, type derivation, matching, the approval
  decision and posting. A re-run never repeats extraction (OCR / AI later), because of its cost.
- An exception accepted as is stays accepted on a re-run while the values it was raised on are unchanged (line,
  quantity, unit price, vendor, invoice number); the re-run does not raise it again. A changed value or a new problem
  raises a new exception.
- Invoices in Pending review at the upgrade are posted by a one-time run. The final review screen and the notification
  "ready for final review" are removed; the outcome stays visible in the invoice detail and All invoices.
- An invoice can be rejected at approval and during exception handling (two rejection points).

**Rationale:** Stated by the Product Owner: touchless processing; people act only on exceptions and approvals.
The details are the Solution Architect's proposals, accepted by the Product Owner.

**Consequences & follow-ups:** The four-eyes candidate SCP-OUT-15 no longer applies to a final review. Feature spec
[SAPS-49](https://linear.app/jiringuyen/issue/SAPS-49). Phase 2 demo scenarios change ([SAPS-47](https://linear.app/jiringuyen/issue/SAPS-47)).

### DEC-064
**Post invoices through an ERP posting port; mock posting; status Posted**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20270301-9](meetings/2027-03-01-po-invoice-posting-and-matching.md) D2, R3, Q9, Q10 |
| Impacts | [scope.md](scope.md) SCP-IN-17; invoice lifecycle (new status Posted); [glossary](../02-architecture/arc42/12-glossary.md) Completed; ADR-0013 (to write) |
| Supersedes / Superseded by | Refines [DEC-023](#dec-023) |

**Context:** Posting goes to the ERP through MuleSoft. There is no MuleSoft flow and no ERP yet.

**Decision:**
- The system posts invoices through an ERP posting port. Until MuleSoft and the ERP exist, a mock adapter accepts
  every posting ("ok") and returns a mock ERP document number.
- A posted invoice gets the new final status **Posted**, with the ERP document number and the posting time.
  Invoices completed before this change stay Completed.
- Posted counts as invoiced for the already invoiced quantity ([DEC-023](#dec-023)).
- A posting rejected by the real ERP raises a new exception "Posting failed"; it is built with the MuleSoft adapter,
  not now.

**Rationale:** The port lets the MuleSoft adapter replace the mock later without changes to the workflow
([ADR-0001](../02-architecture/adr/0001-isolate-extraction-and-erp-behind-ports.md)).

**Consequences & follow-ups:** ADR-0013 on the posting port and posting exactly once.

### DEC-065
**[CR] Trade PO invoices are matched per received lot (PO or DO number)**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Scope |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-9](meetings/2027-03-01-po-invoice-posting-and-matching.md) D3, R5, R6, R8, Q4 – Q6, Q8, Q14 |
| Impacts | [scope.md](scope.md) SCP-IN-03, SCP-IN-21; [SAPS-19](../03-features/SAPS-19-invoice-matching.md); [SAPS-51](https://linear.app/jiringuyen/issue/SAPS-51) |
| Supersedes / Superseded by | Supersedes [DEC-034](#dec-034); refines [DEC-007](#dec-007), [DEC-032](#dec-032) |

**Context:** The PoC matches cumulatively per PO line, without a delivery order (DO) or goods receipt (GR) reference
([DEC-034](#dec-034)). The Product Owner wants each invoice to pay exactly the lot that was received.

**Decision:**
- A trade PO invoice line is matched 3-way against one received lot:
  - the PO line has one goods receipt → matched by PO number;
  - the PO line has several goods receipts → the invoice line must carry the DO number of one of them.
- The DO number is recorded on the goods receipt in the ERP at goods receipt; the system only reads it.
- The invoice quantity must not exceed the not yet invoiced quantity of that lot; a larger quantity raises EX7.
  A smaller quantity passes ([DEC-032](#dec-032)).
- One invoice may cover several lots, one DO number per line.
- Exceptions: no DO number when one is required → EX11; a DO number that no goods receipt of the PO line carries
  → EX13; a PO line without any goods receipt → EX8 ([DEC-068](#dec-068)).
- Non-trade PO invoices keep 2-way matching ([DEC-007](#dec-007)).

**Rationale:** Stated by the Product Owner; the rule for one versus several deliveries is the Solution Architect's
proposal, accepted.

**Consequences & follow-ups:** Extraction delivers a DO number per invoice line (dummy sample set). Feature spec
[SAPS-51](https://linear.app/jiringuyen/issue/SAPS-51).

### DEC-066
**Trade PO unit price checked against the purchasing info record**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-9](meetings/2027-03-01-po-invoice-posting-and-matching.md) D4, R6, R7, Q7 |
| Impacts | [SAPS-19](../03-features/SAPS-19-invoice-matching.md); [SAPS-51](https://linear.app/jiringuyen/issue/SAPS-51); [data-model.md](../02-architecture/data-model.md) ERP entities |
| Supersedes / Superseded by | Partly supersedes [DEC-006](#dec-006) (price reference for trade PO invoices) |

**Context:** The PoC checks the invoice unit price against the PO unit price ([DEC-006](#dec-006)).

**Decision:**
- The unit price of a trade PO invoice line is checked against the price of the purchasing info record (PIR) valid on
  the invoice date. A PIR is identified by vendor, material and company and has a validity period.
- PO lines carry a material number.
- The configurable price tolerance applies (default 0.5 USD, [DEC-015](#dec-015), [DEC-045](#dec-045)); outside it → EX6.
- No valid PIR → EX12 ([DEC-068](#dec-068)).
- Non-trade PO invoices keep the check against the PO unit price.

**Rationale:** Stated by the Product Owner.

**Consequences & follow-ups:** PIR data comes from the dummy ERP until the ERP integration ([DEC-067](#dec-067)).

### DEC-067
**Dummy ERP data in Phase 2: open PO list, DO numbers, PIR prices**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Scope |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20270301-9](meetings/2027-03-01-po-invoice-posting-and-matching.md) D5, R4, R8, Q11 |
| Impacts | [scope.md](scope.md) SCP-IN-09; dummy ERP adapter; [SAPS-51](https://linear.app/jiringuyen/issue/SAPS-51) |
| Supersedes / Superseded by | Extends [DEC-004](#dec-004) to Phase 2 |

**Context:** MuleSoft and the ERP are not available yet (SCP-IN-15).

**Decision:** Until the ERP integration, the dummy ERP data per company holds the open PO list, goods receipts with DO
numbers, and PIR prices. Only open POs are matched: a PO that is closed or fully invoiced raises EX4 with the message
"PO is not open".

**Rationale:** The ERP is already behind a port with dummy data
([ADR-0001](../02-architecture/adr/0001-isolate-extraction-and-erp-behind-ports.md)); the MuleSoft adapter replaces it later.

**Consequences & follow-ups:** None.

### DEC-068
**Exception types EX11 – EX13**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer) |
| Source | [MTG-20270301-9](meetings/2027-03-01-po-invoice-posting-and-matching.md) D6, R13, Q4, Q6, Q7, Q14 |
| Impacts | [scope.md](scope.md) SCP-IN-04; [saps-api.openapi.yaml](../02-architecture/api/saps-api.openapi.yaml) `ExceptionCode`; [SAPS-20](../03-features/SAPS-20-exception-handling.md) |
| Supersedes / Superseded by | Extends [DEC-033](#dec-033) |

**Context:** Matching per lot and the PIR check need new exception types; changes to the list need a new decision
([DEC-033](#dec-033)).

**Decision:**

| Code | Exception | May be accepted as is ([DEC-035](#dec-035)) |
|---|---|---|
| EX11 | DO number missing: the PO line has several goods receipts and the invoice line has no DO number | No |
| EX12 | No purchasing info record valid on the invoice date | No |
| EX13 | Invalid DO number: no goods receipt of the PO line carries the DO number on the invoice line | No |

EX8 stays for a PO line without any goods receipt.

**Rationale:** Proposed by the Solution Architect, accepted by the Product Owner. EX11 – EX13 are errors in the source
data, so they are corrected, not accepted (as EX4 and EX8).

**Consequences & follow-ups:** "Posting failed" ([DEC-064](#dec-064)) gets its code when it is built.

### DEC-069
**DO number and invoice date are matching fields**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20270301-10](meetings/2027-03-01-trade-po-lot-matching-details.md) D1, R1 |
| Impacts | [SAPS-51](../03-features/SAPS-51-trade-po-lot-matching.md) BR-12; [SAPS-20](../03-features/SAPS-20-exception-handling.md) |
| Supersedes / Superseded by | Refines [DEC-024](#dec-024) |

**Context:** Trade PO invoices are matched per lot by DO number ([DEC-065](#dec-065)) and priced with the PIR valid on
the invoice date ([DEC-066](#dec-066)). [DEC-024](#dec-024) lists the invoice date as a field that does not trigger
re-matching.

**Decision:** Matching fields are: vendor code, invoice number, invoice date, PO number, PO line number, DO number,
quantity, unit price. A change of any of them during exception handling re-runs matching.

**Rationale:** Both fields now change the matching result.

**Consequences & follow-ups:** None.

### DEC-070
**Posting to the ERP waits on closed days of the processing calendar**

| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Category | Business |
| Status | confirmed |
| Decided by | Product Owner (Customer), on a proposal by the Solution Architect (our company) |
| Source | [MTG-20270301-11](meetings/2027-03-01-straight-through-posting-details.md) D1, R1 |
| Impacts | [SAPS-49](../03-features/SAPS-49-straight-through-posting.md) BR-11; [SAPS-52](../03-features/SAPS-52-processing-calendar.md); [scope.md](scope.md) SCP-IN-23 |
| Supersedes / Superseded by | Refines [DEC-062](#dec-062) |

**Context:** [DEC-062](#dec-062) holds new invoices on closed days and says invoices in later steps are worked on as usual.
Invoices are now posted to the ERP automatically ([DEC-063](#dec-063), [DEC-064](#dec-064)); a closed period such as a month-end
closing may also mean that nothing is posted.

**Decision:** An invoice that reaches Posting on a closed day of the company's processing calendar waits in Posting and is
posted on the first open day, oldest first. Exception handling and approval are worked on as usual. Nobody is notified when an
invoice is posted.

**Rationale:** Proposed by the Solution Architect; accepted by the Product Owner.

**Consequences & follow-ups:** The release timer of [SAPS-52](../03-features/SAPS-52-processing-calendar.md) also sends
`post_invoice` for invoices waiting in Posting.
