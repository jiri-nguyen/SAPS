---
id: MTG-20261208
title: "MTG-20261208 — Matching rules clarification (SAPS-19)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2026-12-08
related: [MTG-20261205, SAPS-19, DEC-005, DEC-006, DEC-007, DEC-018, DEC-025]
---

# MTG-20261208 — Matching rules clarification (SAPS-19)

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2026-12-08 |
| Time | TBD |
| Type | requirements workshop |
| Channel | TBD |
| Facilitator | Solution Architect (our company) |
| Note taker | Solution Architect (our company) |
| Recording / slides | [SAPS-19 feature spec](../../03-features/SAPS-19-invoice-matching.md) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20261205](2026-12-05-poc-architecture-review.md) #A1, #A2 | Multi-tenancy ADR; document updates | Done (ADR-0007 accepted; scope v0.4, NFR v0.3) |
| [MTG-20261205](2026-12-05-poc-architecture-review.md) #Q1 | Peak periods | Still open; after the PoC |
| [MTG-20261205](2026-12-05-poc-architecture-review.md) #Q2 | Time zone of business hours | Still open; after the PoC |
| [MTG-20261205](2026-12-05-poc-architecture-review.md) #Q3 | Retention periods | Still open; the Product Owner discusses it later |
| [SAPS-19](../../03-features/SAPS-19-invoice-matching.md#7-open-questions) #Q1 | Lines with and without PO number on one invoice | Answered → R1 |
| [SAPS-19](../../03-features/SAPS-19-invoice-matching.md#7-open-questions) #Q2 | Quantity rule | Answered → R2 |
| [SAPS-19](../../03-features/SAPS-19-invoice-matching.md#7-open-questions) #Q3 | Vendor on invoice differs from vendor on PO | Answered → R3 |

## 4. Agenda
1. Open questions Q1–Q3 of the SAPS-19 feature spec

## 5. Discussion
### 5.1 Lines with and without PO number
- The Product Owner agreed to the proposal: lines without a PO number on a PO invoice raise EX3; the type comes from the lines with a PO number.

### 5.2 Quantity rule
- The SA presented two readings: (a) the invoice quantity must equal the expected quantity; (b) it must not exceed it.
- The Product Owner first chose (a) for the PoC, then asked how invoice processing and payment work in practice.
- The SA explained common AP practice (SAP-style):
  - A matched invoice is posted and becomes an open item; it is paid in a payment run when due under the payment terms,
    not immediately. Invoices with variances are posted with a payment block until the variance is cleared.
    In the PoC, payment is out of scope (SCP-OUT-03); status Completed means "ready for posting".
  - One PO is commonly paid through several invoices (partial invoicing); each invoice is paid for its own amount.
    Received but not yet invoiced quantities wait in the GR/IR clearing account. Partial payment of one invoice is rare.
  - Standard 3-way matching blocks only when the invoice quantity exceeds the received-not-invoiced quantity;
    a smaller quantity is normal. Option (a) is stricter than standard practice.
  - A delivery order (DO) is the vendor's delivery document; the goods receipt (GR) is created in the ERP from it.
    Matching references the GR. Two approaches exist: cumulative per PO line (no reference on the invoice), or
    GR-based invoice verification (each invoice line references a GR / DO).
- After the explanation, the Product Owner changed the choice to (b): the invoice quantity must not exceed the expected quantity.
- The Product Owner agreed to match cumulatively per PO line in the PoC, without DO / GR references on the invoice.

### 5.3 Vendor mismatch
- The Product Owner chose a new exception type: EX10 "Vendor does not match the PO".

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | Lines without a PO number on a PO invoice raise EX3; the invoice type comes from the lines with a PO number | Product Owner (Customer) | pending |
| D2 | Quantity rule: the invoice quantity must not exceed the expected quantity (received-not-invoiced for 3-way, PO quantity not yet invoiced for 2-way); a smaller quantity passes | Product Owner (Customer) | pending |
| D3 | New exception type EX10 "Vendor does not match the PO"; a demo scenario for it is added | Product Owner (Customer) | pending |
| D4 | The PoC matches cumulatively per PO line; no DO / GR reference on the invoice | Product Owner (Customer) | pending |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Lines without a PO number on a PO invoice → EX3 on those lines; type from the lines with a PO number | Functional | DEC-031 (refines DEC-005); SAPS-19 BR-02, EC-04 | proposed |
| R2 | Invoice quantity must not exceed the expected quantity; smaller quantities pass (partial invoicing) | Functional | DEC-032 (partly supersedes DEC-006, refines DEC-007); SAPS-19 BR-09 | proposed |
| R3 | EX10 "Vendor does not match the PO": the vendor on the invoice differs from the vendor of the PO | Functional | DEC-033 (supersedes DEC-018 and DEC-025); scope SCP-IN-04; demo scenario DS-20; OpenAPI `ExceptionCode`; data model | proposed |
| R4 | Matching is cumulative per PO line; no DO / GR reference on the invoice in the PoC; GR-based invoice verification is a candidate after the PoC | Scope | DEC-034; SCP-OUT-13 | proposed |
| R5 | Status Completed means "ready for posting"; posting and payment happen outside the system (out of scope) | Scope | Glossary (Completed); SCP-OUT-03 unchanged | proposed |

### 7.1 Conflicts with existing items
| # | Existing item | Conflict | Proposed resolution |
|---|---|---|---|
| K1 | [DEC-006](../decision-log.md#dec-006): "Quantity must match exactly" | R2 allows smaller quantities | DEC-032 partly supersedes DEC-006 (quantity rule only) |
| K2 | [DEC-018](../decision-log.md#dec-018): exception types EX1–EX9 | R3 adds EX10 | DEC-033 lists EX1–EX10 and supersedes DEC-018 |
| K3 | [DEC-025](../decision-log.md#dec-025): DS-01 … DS-19 define "all flows" | R3 adds DS-20 | DEC-033 extends the catalog to DS-01 … DS-20 and supersedes DEC-025 |
| K4 | [saps-api.openapi.yaml](../../02-architecture/api/saps-api.openapi.yaml) `ExceptionCode` enum EX1–EX9 | New value EX10 | Add EX10; API version 0.2.0 (no client implemented yet) |

### 7.2 ADR needs
None.

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Apply the confirmed decisions to the decision log, scope, SAPS-19 spec, OpenAPI, data model, glossary and test strategy | Solution Architect (our company) | 2026-12-09 | open |

## 9. Open Questions
None new. Open items from MTG-20261205 (Q1–Q3) stay open until after the PoC.

## 10. Next Meeting
- On demand ([DEC-027](../decision-log.md#dec-027)).

## 11. Customer Confirmation
| Field | Value |
|---|---|
| Summary sent on | not sent; the Product Owner reviews the minutes directly |
| Confirmed on | pending |
| Reference | this document |
| Corrections received | none |
