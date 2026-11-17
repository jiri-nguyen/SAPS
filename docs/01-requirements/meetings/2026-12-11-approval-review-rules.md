---
id: MTG-20261211
title: "MTG-20261211 — Approval and final review rules (SAPS-21, SAPS-22)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2026-12-11
related: [MTG-20261210, SAPS-21, SAPS-22, DEC-009, DEC-014, DEC-021]
---

# MTG-20261211 — Approval and final review rules (SAPS-21, SAPS-22)

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2026-12-11 |
| Time | TBD |
| Type | requirements workshop |
| Channel | TBD |
| Facilitator | Solution Architect (our company) |
| Note taker | Solution Architect (our company) |
| Recording / slides | [SAPS-22 feature spec](../../03-features/SAPS-22-invoice-approval.md), [SAPS-21 feature spec](../../03-features/SAPS-21-final-result-review.md) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20261210](2026-12-10-exception-handling-rules.md) #A1 | Apply exception handling decisions | Done (DEC-035 … DEC-037 logged) |
| [MTG-20261205](2026-12-05-poc-architecture-review.md) #Q1, #Q2, #Q3 | Peak periods, time zone, retention | Still open; after the PoC |
| [SAPS-22](../../03-features/SAPS-22-invoice-approval.md#7-open-questions) #Q1 | Several Accounting Managers | Answered → R1 |
| [SAPS-22](../../03-features/SAPS-22-invoice-approval.md#7-open-questions) #Q2 | Return for correction | Answered → R2 |
| [SAPS-22](../../03-features/SAPS-22-invoice-approval.md#7-open-questions) #Q3 | Notification on rejection | Answered → R3 |
| [SAPS-21](../../03-features/SAPS-21-final-result-review.md#7-open-questions) #Q1 | Four-eyes principle at final review | Answered → R4 |

## 4. Agenda
1. Open questions of the SAPS-22 and SAPS-21 feature specs

## 5. Discussion
- Several Accounting Managers: the Product Owner agreed that any of them may decide; the first decision is final.
- Return for correction (back to Exception) instead of rejection: the SA explained the extra API operation, demo
  scenario and lifecycle change. The Product Owner chose reject only for the PoC; return for correction can come later.
- Notification on rejection: none in the PoC; status and reason stay visible in the invoice list.
- Four-eyes principle: the SA explained segregation of duties (the same member uploads, accepts an exception and
  confirms the result). The Product Owner chose no restriction in the PoC.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | Any Accounting Manager of the tenant may decide an approval; the first decision is final | Product Owner (Customer) | pending |
| D2 | No "return for correction" in the PoC; approval and final review offer reject only | Product Owner (Customer) | pending |
| D3 | No notification when an invoice is rejected in the PoC | Product Owner (Customer) | pending |
| D4 | No four-eyes rule at final review in the PoC; any Accounting Member may confirm | Product Owner (Customer) | pending |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Any Accounting Manager decides; first decision wins | Functional | DEC-038; SAPS-22 BR-03 | proposed |
| R2 | Reject only at approval and final review; return for correction after the PoC | Scope | DEC-039; SCP-OUT-14; SAPS-22 BR-06, SAPS-21 BR-05 | proposed |
| R3 | No notification on rejection | Functional | DEC-040 (refines DEC-021) | proposed |
| R4 | No four-eyes rule at final review in the PoC; segregation of duties after the PoC | Scope | DEC-041; SCP-OUT-15; SAPS-21 BR-02 | proposed |

### 7.1 Conflicts with existing items
None.

### 7.2 ADR needs
None.

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Apply the confirmed decisions to the decision log, scope, SAPS-21 and SAPS-22 specs | Solution Architect (our company) | 2026-12-12 | open |

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
