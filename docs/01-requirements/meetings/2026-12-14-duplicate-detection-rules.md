---
id: MTG-20261214
title: "MTG-20261214 — Duplicate detection rules (SAPS-23)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2026-12-14
related: [MTG-20261211, SAPS-23, DEC-008, DEC-035, DEC-039, DEC-042, DEC-043]
---

# MTG-20261214 — Duplicate detection rules (SAPS-23)

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2026-12-14 |
| Time | TBD |
| Type | requirements workshop |
| Channel | TBD |
| Facilitator | Solution Architect (our company) |
| Note taker | Solution Architect (our company) |
| Recording / slides | [SAPS-23 feature spec](../../03-features/SAPS-23-duplicate-invoice-detection.md) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20261211](2026-12-11-approval-review-rules.md) #A1 | Apply approval and review decisions | Done (DEC-038 … DEC-041 logged; SAPS-21, SAPS-22 approved) |
| [MTG-20261205](2026-12-05-poc-architecture-review.md) #Q1, #Q2, #Q3 | Peak periods, time zone, retention | Still open; after the PoC |
| [SAPS-23](../../03-features/SAPS-23-duplicate-invoice-detection.md#7-open-questions) #Q1 | Normalize invoice numbers | Answered → R1 |
| [SAPS-23](../../03-features/SAPS-23-duplicate-invoice-detection.md#7-open-questions) #Q2 | Ignore rejected invoices | Answered → R2 |

## 4. Agenda
1. Open questions Q1–Q2 of the SAPS-23 feature spec

## 5. Discussion
- Normalization: the SA showed examples ("INV-0001", "INV0001", "inv 0001" are the same invoice; "INV-0001" and
  "INV-001" may not be). False positives are acceptable because EX9 may be accepted as is (DEC-035).
  The Product Owner agreed to the proposed normalization.
- Rejected invoices: a corrected invoice is uploaded again with the same number (DEC-039); comparing it with the
  rejected invoice would always raise EX9. A rejected invoice is never paid, so there is no double-payment risk.
  The Product Owner chose to ignore rejected invoices.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | Invoice numbers are compared after normalization: case ignored; spaces, `-`, `.` and `/` removed; leading zeros kept | Product Owner (Customer) | [DEC-042](../decision-log.md#dec-042) |
| D2 | Rejected invoices are ignored by the duplicate check | Product Owner (Customer) | [DEC-043](../decision-log.md#dec-043) |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Normalize invoice numbers before the duplicate comparison (rule in D1) | Functional | DEC-042 (refines DEC-008); SAPS-23 BR-02; data model `Invoice.invoice_number_normalized` | logged |
| R2 | The duplicate check ignores invoices in status Rejected | Functional | DEC-043 (refines DEC-008); SAPS-23 BR-03 | logged |

### 7.1 Conflicts with existing items
None.

### 7.2 ADR needs
None.

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Apply the confirmed decisions to the decision log, SAPS-23 spec and data model | Solution Architect (our company) | 2026-12-15 | done (SAPS-23 approved) |

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
