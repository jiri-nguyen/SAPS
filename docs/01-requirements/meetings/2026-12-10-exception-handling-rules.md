---
id: MTG-20261210
title: "MTG-20261210 — Exception handling rules (SAPS-20)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2026-12-10
related: [MTG-20261208, SAPS-20, DEC-016, DEC-021, DEC-033, DEC-035, DEC-036, DEC-037]
---

# MTG-20261210 — Exception handling rules (SAPS-20)

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2026-12-10 |
| Time | TBD |
| Type | requirements workshop |
| Channel | TBD |
| Facilitator | Solution Architect (our company) |
| Note taker | Solution Architect (our company) |
| Recording / slides | [SAPS-20 feature spec](../../03-features/SAPS-20-exception-handling.md) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20261208](2026-12-08-matching-rules.md) #A1 | Apply matching decisions | Done (DEC-031 … DEC-034 logged) |
| [MTG-20261205](2026-12-05-poc-architecture-review.md) #Q1, #Q2, #Q3 | Peak periods, time zone, retention | Still open; after the PoC |
| [SAPS-20](../../03-features/SAPS-20-exception-handling.md#7-open-questions) #Q1 | Exception types that may be accepted as is | Answered → R1 |
| [SAPS-20](../../03-features/SAPS-20-exception-handling.md#7-open-questions) #Q2 | Accounting Manager releases claims | Answered → R2 |
| [SAPS-20](../../03-features/SAPS-20-exception-handling.md#7-open-questions) #Q3 | Notification after a repeated exception | Answered → R3 |

## 4. Agenda
1. Open questions Q1–Q3 of the SAPS-20 feature spec

## 5. Discussion
- The SA explained the three ways to handle an exception: correct the data (re-matching), accept as is, or reject.
- The SA presented common practice: price and quantity variances can be accepted by an authorized person; errors in the
  source data (PO, vendor, goods receipt) must be corrected or the invoice rejected.
- Accepted invoices above the approval threshold still need Accounting Manager approval (DEC-009, DEC-013).
- The Product Owner agreed to the proposed list of exception types that may be accepted as is.
- The Product Owner agreed that an Accounting Manager may release any claim.
- The Product Owner chose to notify only the claimant when re-matching raises exceptions again.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | Exceptions that may be accepted as is: EX2, EX6, EX7, EX9. Not allowed: EX1, EX3, EX4, EX5, EX8, EX10 (correct the data or reject) | Product Owner (Customer) | [DEC-035](../decision-log.md#dec-035) |
| D2 | An Accounting Manager may release any claim; the claimant may release their own | Product Owner (Customer) | [DEC-036](../decision-log.md#dec-036) |
| D3 | When re-matching raises exceptions again, only the claimant is notified | Product Owner (Customer) | [DEC-037](../decision-log.md#dec-037) |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Accept as is allowed only when every open exception is EX2, EX6, EX7 or EX9 | Functional | DEC-035; SAPS-20 BR-06; OpenAPI `resolveInvoiceExceptions` | logged |
| R2 | Accounting Manager may release any claim | Functional | DEC-036; SAPS-20 BR-03; OpenAPI `releaseInvoiceClaim` | logged |
| R3 | Repeated exception after re-matching → notify the claimant only | Functional | DEC-037 (refines DEC-021); SAPS-20 BR-10 | logged |

### 7.1 Conflicts with existing items
| # | Existing item | Conflict | Proposed resolution |
|---|---|---|---|
| K1 | [DEC-021](../decision-log.md#dec-021): exceptions are notified to Accounting Members | R3 narrows the recipient for repeated exceptions on a claimed invoice | DEC-037 refines DEC-021 |

### 7.2 ADR needs
None.

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Apply the confirmed decisions to the decision log, SAPS-20 spec and OpenAPI | Solution Architect (our company) | 2026-12-11 | done |

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
