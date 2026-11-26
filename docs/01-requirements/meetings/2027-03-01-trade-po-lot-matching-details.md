---
id: MTG-20270301-10
title: "MTG-20270301-10 — Trade PO lot matching details (SAPS-51)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2027-03-01
related: [SAPS-51, DEC-024, DEC-042, DEC-065, DEC-066, DEC-068, DEC-069, MTG-20270301-9]
---

# MTG-20270301-10 — Trade PO lot matching details (SAPS-51)

> **Assumption:** this meeting took place on the same day as the Phase 2 kickoff (2027-03-01). To be confirmed by the
> Solution Architect (our company).

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Time | TBD |
| Type | requirements workshop |
| Channel | TBD |
| Facilitator | Solution Architect (our company) |
| Note taker | Solution Architect (our company) |
| Recording / slides | [SAPS-51 feature spec](../../03-features/SAPS-51-trade-po-lot-matching.md) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20270301-9](2027-03-01-po-invoice-posting-and-matching.md) #A3 | Feature specs for SAPS-51 and SAPS-49; ADR-0013 | SAPS-51 written; its questions answered → R1 – R5. SAPS-49 and ADR-0013 next |
| [MTG-20270301-9](2027-03-01-po-invoice-posting-and-matching.md) #A4 | Demo scenario catalog for the new flows (SAPS-47) | Still open |
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #Q4 | Kickoff Q8 – Q12: NFR targets, peaks, retention, load test, UI language; priority of SAPS-50 | Still open |
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #Q1 | Go-live date and budget | Still open |
| [MTG-20270301-3](2027-03-01-tenancy-and-identity.md) #Q1 | Data residency per country | Still open |

## 4. Agenda
1. Open questions Q1 to Q5 of the SAPS-51 feature spec

## 5. Discussion
The Product Owner accepted the Solution Architect's proposals for all five questions:
- The DO number of a line and the invoice date become matching fields: a change during exception handling re-runs
  matching.
- A trade PO invoice without an invoice date raises EX12 "no invoice date to select the PIR".
- Two goods receipts of the same PO line with the same DO number are one lot; their quantities are added up.
- DO numbers are compared with the normalization of invoice numbers (DEC-042).
- A PO whose lines are all fully invoiced raises EX4 "PO is not open" instead of EX7.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | The DO number of an invoice line and the invoice date are matching fields (refines DEC-024) | Product Owner (Customer), on a proposal by the Solution Architect | [DEC-069](../decision-log.md#dec-069) |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | DO number and invoice date re-run matching when changed | Functional | DEC-069; SAPS-51 BR-12 | logged |
| R2 | No invoice date on a trade PO invoice → EX12 | Functional | SAPS-51 BR-09 | logged |
| R3 | Goods receipts with the same DO number on one PO line form one lot | Functional | SAPS-51 BR-02 | logged |
| R4 | DO numbers compared with the DEC-042 normalization | Functional | SAPS-51 BR-04 | logged |
| R5 | Fully invoiced PO → EX4 "PO is not open" | Functional | SAPS-51 BR-01 | logged |

### 7.1 Conflicts with existing items
| Existing item | Conflict | Resolution |
|---|---|---|
| [DEC-024](../decision-log.md#dec-024) | The invoice date is listed as a field that does not trigger re-matching | DEC-069 refines DEC-024 |

### 7.2 ADR needs
None.

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Update the SAPS-51 spec with the answers | Solution Architect (our company) | 2027-03-01 | done |

## 9. Open Questions
None new.

## 10. Next Meeting
- On demand.

## 11. Customer Confirmation
| Field | Value |
|---|---|
| Summary sent on | not sent; the Product Owner reviews the minutes directly |
| Confirmed on | pending |
| Reference | this document |
| Corrections received | none |
