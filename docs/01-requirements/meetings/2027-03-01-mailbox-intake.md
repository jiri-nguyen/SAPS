---
id: MTG-20270301-6
title: "MTG-20270301-6 — Mailbox intake details (SAPS-45)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2027-03-01
related: [SAPS-45, DEC-055, ADR-0012]
---

# MTG-20270301-6 — Mailbox intake details (SAPS-45)

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
| Recording / slides | [SAPS-45 feature spec](../../03-features/SAPS-45-mailbox-intake.md) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20270301-4](2027-03-01-processing-calendar.md) #A2 | Feature spec of SAPS-52 | Still open (after SAPS-46) |
| [MTG-20270301-3](2027-03-01-tenancy-and-identity.md) #Q1 | Data residency per country | Still open |
| [SAPS-45](../../03-features/SAPS-45-mailbox-intake.md#7-open-questions) #Q1, #Q2 | Which mail parts are invoices; what users see of the mail | Answered → R1, R2 |

## 4. Agenda
1. Open questions Q1 and Q2 of the SAPS-45 feature spec

## 5. Discussion
- Vendors attach the invoice file directly to the mail. Only attached PDF, PNG and JPG files are invoices; images inside
  the mail body, such as signature logos, are not. ZIP files and forwarded mails attached as `.eml` are skipped as
  unsupported attachments.
- The invoice detail shows that the invoice came by mail, with the sender, the subject and the date. The invoice lists do
  not change; filtering by channel can come with the invoice search (SAPS-46).

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| — | None at decision-log level; the answers refine [DEC-055](../decision-log.md#dec-055) and are recorded in the SAPS-45 spec | — | — |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Only attached PDF, PNG and JPG files are invoices; inline images are ignored; ZIP and `.eml` attachments are skipped as unsupported | Functional | SAPS-45 BR-02, EC-02, EC-04 | logged |
| R2 | The invoice detail shows "Received by mail from {sender} · {subject} · {date}"; the lists are unchanged | Functional | SAPS-45 BR-04, §3.4 | logged |

### 7.1 Conflicts with existing items
None.

### 7.2 ADR needs
None.

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Update the SAPS-45 spec with the answers | Solution Architect (our company) | 2027-03-01 | done |

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
