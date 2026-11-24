---
id: MTG-20270301-4
title: "MTG-20270301-4 — New requirement: processing calendar per company"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2027-03-01
related: [MTG-20270301, DEC-062, DEC-048, DEC-050, DEC-052, DEC-056, DEC-060, SAPS-52]
---

# MTG-20270301-4 — New requirement: processing calendar per company

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
| Recording / slides | — |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20270301-3](2027-03-01-tenancy-and-identity.md) #Q1 | Data residency per country | Still open |
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #Q1, #Q4 | Go-live, budget; kickoff Q7–Q12 | Still open |

## 4. Agenda
1. New requirement of the Product Owner: a processing calendar per company

## 5. Discussion
- The Product Owner wants Accounting Managers to set a schedule (or something similar) per company, for example: company A
  does not process invoices from the 25th of a month to the 5th of the next month, and not on weekends.
- The team asked Q1–Q9 with a proposal each; the Product Owner accepted every proposal:
  - Q1: invoices are still received (upload, mail) but **held**; when the closed period ends they are processed automatically.
  - Q2: three kinds of rules: a monthly day range (e.g. 25th → 5th of the next month), weekdays (e.g. Saturday, Sunday),
    and specific dates entered by the Accounting Manager (e.g. public holidays); no times of day.
  - Q3: the calendar uses the company's local time zone (e.g. Vietnam UTC+7, Singapore UTC+8).
  - Q4: when the period ends, held invoices are processed automatically, oldest first.
  - Q5: an Accounting Manager can release one held invoice at once ("process now").
  - Q6: the Web App shows a banner "Company is in a closed period until …"; held invoices have a new status **On hold**;
    no notification when a period starts or ends.
  - Q7: only the Accounting Manager of the company changes its calendar; changes apply at once, also to held invoices.
  - Q8: in the demo on 2027-08-30; built after the invoice list and search ([SAPS-46](https://linear.app/jiringuyen/issue/SAPS-46)).
  - Q9: only automatic processing is held; invoices already in exception handling, approval or final review are worked on
    as usual.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | `[CR]` Processing calendar per company in Phase 2 with the rules of §5 | Product Owner (Customer), on a proposal by the Solution Architect | proposed DEC-062 |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Accounting Managers set a processing calendar for their company: periods in which invoices are not processed, e.g. from the 25th to the 5th of the next month, and weekends | Functional | `[CR]` DEC-062; scope.md new SCP-IN-23; Linear [SAPS-52](https://linear.app/jiringuyen/issue/SAPS-52); feature spec SAPS-52 | proposed |

### 7.1 Conflicts with existing items
| Existing item | Conflict | Proposal |
|---|---|---|
| [DEC-048](../decision-log.md#dec-048), [DEC-050](../decision-log.md#dec-050) | New scope item not in the Phase 2 scope and priorities | Scope change `[CR]` (DEC-062); built after SAPS-46 (Q8) |
| [DEC-052](../decision-log.md#dec-052) | Demo on 2027-08-30 | In the demo; the rules stay simple (Q2) |
| [SAPS-37](../../03-features/SAPS-37-stuck-invoice-sweeper.md) sweeper | Invoices held on purpose must not count as "stuck" | Invoices On hold are not stuck: the sweeper ignores them (feature spec SAPS-52) |

### 7.2 ADR needs
- None: the calendar is business logic inside the existing containers. The new status On hold changes the invoice lifecycle (data model, feature spec SAPS-52).

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Answer Q1–Q9 | Product Owner (Customer) | 2027-03-01 | done |
| A2 | Propose the `[CR]` decision, SCP-IN-23 and the feature spec of SAPS-52 | Solution Architect (our company) | after A1 | open |

## 9. Open Questions
| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| Q1 | What does "not processed" mean? (a) invoices are received (upload, mail) but held, and processed automatically when the period ends; (b) uploads and mails are refused or left in the mailbox; (c) also users cannot work on invoices (claim, correct, approve, confirm) during the period | Product Owner (Customer) | next meeting | answered: proposal accepted |
| Q2 | Which kinds of rules: a monthly date range (25th → 5th), weekdays (weekends), specific dates (public holidays per country), times of day? | Product Owner (Customer) | next meeting | answered: proposal accepted |
| Q3 | Time zone of the calendar: the company's own local time (e.g. Vietnam UTC+7, Singapore UTC+8)? | Product Owner (Customer) | next meeting | answered: proposal accepted |
| Q4 | When a closed period ends, are the held invoices processed automatically, oldest first? | Product Owner (Customer) | next meeting | answered: proposal accepted |
| Q5 | Can an Accounting Manager let one urgent invoice through during a closed period? | Product Owner (Customer) | next meeting | answered: proposal accepted |
| Q6 | Must users see that the company is in a closed period (banner, status "On hold" on the invoice)? Any notification when it starts or ends? | Product Owner (Customer) | next meeting | answered: proposal accepted |
| Q7 | Only the Accounting Manager of the company changes its calendar; changes apply at once, also to invoices already held? | Product Owner (Customer) | next meeting | answered: proposal accepted |
| Q8 | Priority and demo: must it be in the demo on 2027-08-30, and is it before or after the invoice list and search (SAPS-46)? | Product Owner (Customer) | next meeting | answered: proposal accepted |
| Q9 | Does a closed period also affect deadlines or notifications (for example no approval requests during the period)? | Product Owner (Customer) | next meeting | answered: proposal accepted |

## 10. Next Meeting
- To be agreed; topic: answers to Q1–Q9.

## 11. Customer Confirmation
| Field | Value |
|---|---|
| Summary sent on | not sent; the Product Owner reviews the minutes directly |
| Confirmed on | pending |
| Reference | this document |
| Corrections received | none |
