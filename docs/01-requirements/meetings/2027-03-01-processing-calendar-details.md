---
id: MTG-20270301-8
title: "MTG-20270301-8 — Processing calendar details (SAPS-52)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2027-03-01
related: [SAPS-52, DEC-062, MTG-20270301-4]
---

# MTG-20270301-8 — Processing calendar details (SAPS-52)

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
| Recording / slides | [SAPS-52 feature spec](../../03-features/SAPS-52-processing-calendar.md) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20270301-4](2027-03-01-processing-calendar.md) #A2 | Feature spec of SAPS-52 | Written; details answered → R1 – R4 |
| [MTG-20270301-3](2027-03-01-tenancy-and-identity.md) #Q1 | Data residency per country | Still open |
| [SAPS-52](../../03-features/SAPS-52-processing-calendar.md#7-open-questions) #Q1 – #Q4 | Monthly ranges, invoices waiting at the start of a closed day, what can be done with a held invoice, banner | Answered → R1 – R4 |

## 4. Agenda
1. Open questions Q1 to Q4 of the SAPS-52 feature spec

## 5. Discussion
- A monthly range includes both days; a range such as 25 → 5 runs into the next month; a day number after the end of a
  month means its last day (31 in February is the 28th or 29th).
- An invoice received on an open day but not yet processed when a closed day starts is held as well: the calendar is
  checked when processing starts.
- An invoice On hold can be opened and found in All invoices. Only the Accounting Manager's "Process now" lets it
  through; it cannot be claimed, corrected or rejected while held.
- Every user of the company sees the banner "{Company} is in a closed period until {first open day}: new invoices are
  held." ("until further notice" when no open day comes within a year). Only Accounting Managers see and change the
  calendar screen.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| — | None at decision-log level; the answers refine [DEC-062](../decision-log.md#dec-062) and are recorded in the SAPS-52 spec | — | — |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Monthly ranges include both days, may run into the next month, and a day after the end of a month means its last day | Functional | SAPS-52 BR-01, BR-02 | logged |
| R2 | Invoices waiting for processing when a closed day starts are held too | Functional | SAPS-52 BR-03 | logged |
| R3 | A held invoice can be opened and searched; only "Process now" by a manager releases it; no claim, correction or rejection while held | Functional | SAPS-52 BR-06, BR-09 | logged |
| R4 | Banner for every user with the first open day; the calendar screen is for Accounting Managers | Functional | SAPS-52 BR-08 | logged |

### 7.1 Conflicts with existing items
None.

### 7.2 ADR needs
None.

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Update the SAPS-52 spec with the answers | Solution Architect (our company) | 2027-03-01 | done |

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
