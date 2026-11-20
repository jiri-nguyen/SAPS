---
id: MTG-20261215
title: "MTG-20261215 — Matching settings rules (SAPS-28)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2026-12-15
related: [MTG-20261214, SAPS-28, DEC-015, DEC-045, DEC-046]
---

# MTG-20261215 — Matching settings rules (SAPS-28)

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2026-12-15 |
| Time | TBD |
| Type | requirements workshop |
| Channel | TBD |
| Facilitator | Solution Architect (our company) |
| Note taker | Solution Architect (our company) |
| Recording / slides | [SAPS-28 feature spec](../../03-features/SAPS-28-matching-settings.md) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20261214](2026-12-14-duplicate-detection-rules.md) #A1 | Apply duplicate detection decisions | Done (DEC-042, DEC-043 logged; SAPS-23 approved and implemented) |
| [MTG-20261205](2026-12-05-poc-architecture-review.md) #Q1, #Q2, #Q3 | Peak periods, time zone, retention | Still open; after the PoC |
| [SAPS-28](../../03-features/SAPS-28-matching-settings.md#7-open-questions) #Q1 | Allowed values of the price tolerance and the approval threshold | Answered → R1 |
| [SAPS-28](../../03-features/SAPS-28-matching-settings.md#7-open-questions) #Q2 | History of changes of the settings | Answered → R2 |

## 4. Agenda
1. Open questions Q1–Q2 of the SAPS-28 feature spec

## 5. Discussion
- Allowed values: the SA presented the proposal of SAPS-28 Q1. A tolerance of 0 means the unit price must equal the PO
  price; a threshold of 0 means every invoice with a positive total needs approval. Values with too many decimals or
  outside the range are refused with a message naming the field. The Product Owner agreed to the proposal, with no
  upper limit.
- History: the screen shows who changed the settings last and when. The Product Owner said the last change is enough for
  the PoC; no history screen is needed. The application log keeps the old and new values of each change.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | Price tolerance: 0 USD or more, up to 4 decimals. Approval threshold: 0 USD or more, up to 2 decimals. No upper limit for either. | Product Owner (Customer) | [DEC-045](../decision-log.md#dec-045) |
| D2 | Only the last change of the matching settings is kept (who, when); no history of changes in the PoC | Product Owner (Customer) | [DEC-046](../decision-log.md#dec-046) |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Allowed values of the matching settings (rule in D1) | Functional | DEC-045 (refines DEC-015); SAPS-28 BR-03, EC-02, EC-03 | logged |
| R2 | Last change only, no history (rule in D2) | Scope | DEC-046 (refines DEC-015); SAPS-28 BR-05; data model unchanged | logged |

### 7.1 Conflicts with existing items
None. Both refine [DEC-015](../decision-log.md#dec-015) and match the column types of
[MatchingSettings](../../02-architecture/data-model.md#matchingsettings) (`decimal(18,4)`, `decimal(18,2)`).

### 7.2 ADR needs
None.

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Apply the confirmed decisions to the decision log and the SAPS-28 spec | Solution Architect (our company) | 2026-12-16 | done (DEC-045, DEC-046 logged; SAPS-28 spec updated) |

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
