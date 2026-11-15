---
id: MTG-20261205
title: "MTG-20261205 — PoC architecture review and open questions"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2026-12-05
related: [MTG-20261128, ADR-0004, ADR-0006, DEC-019, DEC-020]
---

# MTG-20261205 — PoC architecture review and open questions

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2026-12-05 |
| Time | TBD |
| Type | design review |
| Channel | TBD |
| Facilitator | Solution Architect (our company) |
| Note taker | Solution Architect (our company) |
| Recording / slides | [C4 L2 – Containers](../../02-architecture/diagrams/c4/c4-l2-containers.drawio.svg) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20261128](2026-11-28-poc-flow-review.md) #A1 | Data model (SAPS-31) | Done: [data-model.md](../../02-architecture/data-model.md) |
| [MTG-20261128](2026-11-28-poc-flow-review.md) #A2 | Test strategy and demo scenario catalog (SAPS-32) | Done: [test-strategy.md](../../05-testing/test-strategy.md) |
| [MTG-20261128](2026-11-28-poc-flow-review.md) #A3 | Linear epics | Done: SAPS-17 … SAPS-34 |
| [MTG-20261128](2026-11-28-poc-flow-review.md) #A4 | Processing model ADR (SAPS-33) | Done: ADR-0004 accepted after spike SAPS-34 |
| [data-model.md](../../02-architecture/data-model.md#8-open-questions) #Q1 | Which invoices count as already invoiced | Answered → R2 |
| [data-model.md](../../02-architecture/data-model.md#8-open-questions) #Q5 | Matching fields that trigger re-matching | Answered → R3 |
| [test-strategy.md](../../05-testing/test-strategy.md#14-open-questions) #Q3 | Demo scenario catalog complete? | Answered → R4 |
| [MTG-20261114](2026-11-14-kickoff.md) #Q1 | Organization and legal entities | Closed: not needed (Product Owner) |
| [MTG-20261114](2026-11-14-kickoff.md) #Q3 | Business objectives | Answered → R5 |
| [MTG-20261114](2026-11-14-kickoff.md) #Q5 | Invoice volume | Answered → R6 |
| [MTG-20261114](2026-11-14-kickoff.md) #Q6 | Peak periods | Still open → Q1 below |
| [MTG-20261114](2026-11-14-kickoff.md) #Q9 | Other intake channels | Answered → R7 |
| [MTG-20261114](2026-11-14-kickoff.md) #Q26 | Go-live, phases, budget | Partly answered (PoC, demo, sign-off); go-live and budget still open |
| [MTG-20261114](2026-11-14-kickoff.md) #Q27 | Cloud provider and account | Answered → R8 |
| [MTG-20261114](2026-11-14-kickoff.md) #Q30 | Retention | Still open; the Product Owner discusses it later |
| [MTG-20261114](2026-11-14-kickoff.md) #Q31 | Operating hours | Answered (assumption) → R9 |
| [MTG-20261114](2026-11-14-kickoff.md) #Q7, #Q8, #Q10–#Q12, #Q28 | Extraction details | Deferred (dummy extraction in the PoC) |

## 4. Agenda
1. Follow-up from MTG-20261128
2. PoC architecture: Redis and SeaweedFS added to the stack
3. Data model questions
4. Demo scenario catalog
5. Questions left for after the PoC

## 5. Discussion
### 5.1 PoC architecture
- The SA presented the C4 L2 diagram: Redis (SAPS Message Broker, [ADR-0004](../../02-architecture/adr/0004-process-invoices-in-background-worker.md)) and
  SeaweedFS (SAPS File Storage, [ADR-0006](../../02-architecture/adr/0006-store-invoice-files-in-seaweedfs.md)) are added to the stack agreed in DEC-019.
- The Product Owner agreed.

### 5.2 Data model
- Already invoiced quantity: the SA explained the SAP practice (invoiced quantity grows when an invoice is posted,
  checked again at posting) and the risk of double invoicing without a posting step in the PoC. The Product Owner chose option (b):
  invoices that passed matching and wait for approval or review, plus completed invoices, count as invoiced.
- Matching fields: the proposed list is agreed.

### 5.3 Demo scenario catalog
- DS-01 … DS-19 are complete for "all flows".

### 5.4 Product direction and questions after the PoC
- In the future, the system is deployed on AWS and serves many customer companies. Each company processes on average
  1,000–2,000 invoices per day.
- For the PoC: one customer company, at most 1,000 invoices per day. This number is design information only, not an acceptance criterion.
- Future intake: a dedicated mailbox and manual upload. The PoC covers manual upload only.
- Cloud: AWS, in the Product Owner's company account; accounts are given to the team when needed.
- Retention is not decided yet; the Product Owner discusses it later.
- Assume operation during business hours.
- Organization and legal entities are not needed.
- Meetings are held only when there are questions to discuss.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | Redis and SeaweedFS are added to the PoC stack (ADR-0004, ADR-0006) | Product Owner (Customer) | pending |
| D2 | Already invoiced quantity of a PO line counts invoices in PendingApproval, PendingReview and Completed (option b) | Product Owner (Customer) | pending |
| D3 | Matching fields: vendor code, invoice number, PO number, PO line number, quantity, unit price | Product Owner (Customer) | pending |
| D4 | Demo scenario catalog DS-01 … DS-19 defines "all flows" | Product Owner (Customer) | pending |
| D5 | Product direction: multi-company AP system on AWS (Product Owner's company account) | Product Owner (Customer) | pending |
| D6 | Meetings only when there are questions; no fixed weekly meeting | Product Owner (Customer) | pending |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Redis and SeaweedFS are added to the PoC stack | Constraint | DEC-022 | proposed |
| R2 | Already invoiced = invoices in PendingApproval, PendingReview, Completed; Exception and Rejected do not count | Functional | DEC-023; data-model.md §4.2 | proposed |
| R3 | Matching fields: vendor_code, invoice_number, po_number, po_line_number, quantity, unit_price; other fields do not trigger re-matching | Functional | DEC-024; data-model.md | proposed |
| R4 | DS-01 … DS-19 are complete | Scope | DEC-025; test-strategy.md §11 | proposed |
| R5 | Business objective: grow into an AP system serving many customer companies | Scope | DEC-026; scope.md BO1 | proposed |
| R6 | Future volume: 1,000–2,000 invoices per day per company, many companies. PoC: one company, ≤ 1,000 invoices per day (design information only) | NFR | nfr.md Workload Profile; NFR-SCAL-001 conditions | proposed |
| R7 | Future intake: dedicated mailbox + manual upload; PoC: manual upload only | Scope | scope.md AS1 → confirmed for the PoC; SCP-OUT-11 (mailbox intake) | proposed |
| R8 | After the PoC the system runs on AWS in the Product Owner's company account; accounts are given when needed | Constraint | DEC-026; arc42 §2 CON-06 | proposed |
| R9 | Operation during business hours (assumption) | NFR | nfr.md Workload Profile (operating hours) | proposed |
| R10 | Meetings only when there are questions | Constraint | DEC-027 | proposed |

### 7.1 Conflicts with existing items
| # | Existing item | Conflict | Proposed resolution |
|---|---|---|---|
| K1 | [Data model](../../02-architecture/data-model.md) and ADRs assume one customer (single tenant) | Future multi-company system (R5) needs tenant isolation | ADR need ADR-N1; decide whether the PoC data model carries a tenant key now |
| K2 | [NFR-SCAL-001](../nfr.md#nfr-scal-001): targets TBD | Workload is now known (R6) | Fill in the Workload Profile; NFR-SCAL-001 stays verified by review (design information only) |
| K3 | [scope.md AS1](../scope.md#5-assumptions): manual upload is the only intake channel | Future mailbox intake (R7) | AS1 confirmed for the PoC; mailbox intake added as SCP-OUT-11 |
| K4 | [DEC-019](../decision-log.md#dec-019): stack agreed without Redis and SeaweedFS | Stack extended (R1) | DEC-022 extends DEC-019 |

### 7.2 ADR needs
| # | Need | Driver |
|---|---|---|
| ADR-N1 | Multi-tenancy model (shared database with tenant key, schema per tenant, or database per tenant), and whether the PoC already carries a tenant key | R5, R6, NFR-SCAL-001 |

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Draft ADR-N1 (multi-tenancy model); create a Linear issue under SAPS-30 for it | Solution Architect (our company) | 2026-12-12 | open |
| A2 | Update data model, NFR workload profile, scope and constraints after the decisions are logged | Solution Architect (our company) | 2026-12-08 | open |

## 9. Open Questions
| # | Question | Asked to | Due | Answer / status |
|---|---|---|---|---|
| Q1 | Are there peak periods (e.g. month-end) and how much higher than average? (MTG-20261114 Q6) | Product Owner (Customer) | after PoC | open |
| Q2 | "Business hours" in which time zone(s)? Customer companies may be in different countries | Product Owner (Customer) | after PoC | open |
| Q3 | Retention periods for invoices, files and audit trail (MTG-20261114 Q30) | Product Owner (Customer) | after PoC | open |

## 10. Next Meeting
- On demand, when there are questions ([D6](#6-decisions)).

## 11. Customer Confirmation
| Field | Value |
|---|---|
| Summary sent on | not sent; the Product Owner reviews the minutes directly |
| Confirmed on | pending |
| Reference | this document |
| Corrections received | none |
