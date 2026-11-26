---
id: MTG-20270301-11
title: "MTG-20270301-11 — Straight-through posting details (SAPS-49)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2027-03-01
related: [SAPS-49, DEC-062, DEC-063, DEC-064, DEC-070, MTG-20270301-9]
---

# MTG-20270301-11 — Straight-through posting details (SAPS-49)

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
| Recording / slides | [SAPS-49 feature spec](../../03-features/SAPS-49-straight-through-posting.md) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20270301-9](2027-03-01-po-invoice-posting-and-matching.md) #A3 | Feature specs for SAPS-51 and SAPS-49; ADR-0013 | SAPS-51 merged. SAPS-49 written; its questions answered → R1 – R4. ADR-0013 proposed |
| [MTG-20270301-9](2027-03-01-po-invoice-posting-and-matching.md) #A4 | Demo scenario catalog for the new flows (SAPS-47) | Still open |
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #Q4 | Kickoff Q8 – Q12: NFR targets, peaks, retention, load test, UI language; priority of SAPS-50 | Still open |
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #Q1 | Go-live date and budget | Still open |
| [MTG-20270301-3](2027-03-01-tenancy-and-identity.md) #Q1 | Data residency per country | Still open |

## 4. Agenda
1. Open questions Q1 to Q4 of the SAPS-49 feature spec

## 5. Discussion
The Product Owner accepted the Solution Architect's proposals for all four questions:
- On a closed day of the processing calendar, an invoice that reaches Posting waits and is posted on the first open day.
- Nobody is notified when an invoice is posted.
- Invoices that were Completed before the upgrade stay Completed; they are not posted.
- After posting, the invoice shows the status Posted, the ERP document number and the posting time.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | Posting to the ERP waits on closed days of the processing calendar (refines DEC-062) | Product Owner (Customer), on a proposal by the Solution Architect | [DEC-070](../decision-log.md#dec-070) |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | An invoice that reaches Posting on a closed day is posted on the first open day | Functional | DEC-070; SAPS-49 BR-11 | logged |
| R2 | No notification on posting | Functional | SAPS-49 BR-08 | logged |
| R3 | Completed invoices at the upgrade are not posted | Functional | SAPS-49 BR-10 | logged |
| R4 | Posted invoices show the ERP document number and the posting time | Functional | SAPS-49 §3.4, §3.6 | logged |

### 7.1 Conflicts with existing items
| Existing item | Conflict | Resolution |
|---|---|---|
| [DEC-062](../decision-log.md#dec-062) | Only automatic processing is held; invoices in later steps are "worked on as usual" | DEC-070 refines DEC-062: posting is held too |

### 7.2 ADR needs
[ADR-0013](../../02-architecture/adr/0013-post-invoices-through-an-erp-posting-port.md) (proposed with the spec).

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Update the SAPS-49 spec with the answers | Solution Architect (our company) | 2027-03-01 | done |
| A2 | Accept ADR-0013 | Solution Architect (our company) | with the spec approval | open |

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
