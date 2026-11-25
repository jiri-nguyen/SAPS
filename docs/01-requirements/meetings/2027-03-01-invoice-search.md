---
id: MTG-20270301-7
title: "MTG-20270301-7 — Invoice search details (SAPS-46)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2027-03-01
related: [SAPS-46, SAPS-45, DEC-057, DEC-055]
---

# MTG-20270301-7 — Invoice search details (SAPS-46)

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
| Recording / slides | [SAPS-46 feature spec](../../03-features/SAPS-46-invoice-search.md) |

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
| [SAPS-45](../../03-features/SAPS-45-mailbox-intake.md) | PDF attachments marked inline by some mail clients | Answered → R4 |
| [SAPS-46](../../03-features/SAPS-46-invoice-search.md#7-open-questions) #Q1, #Q2, #Q3 | How text filters match, time zone of the upload date, result columns | Answered → R1 – R3 |

## 4. Agenda
1. Open questions Q1 to Q3 of the SAPS-46 feature spec
2. PDF files marked inline in a mail (SAPS-45)

## 5. Discussion
- Text filters: the vendor filter matches part of the vendor name or the vendor code, ignoring case. The invoice number
  filter matches part of the number, ignoring case, spaces and the characters `-` `.` `/`. The PO number filter is exact
  (7 digits) and finds any line of the invoice.
- The upload date is the day in the time zone of the company, for example Singapore time for Demo Singapore.
- The result list shows the invoice number, vendor, invoice date, total amount, status, channel (upload or mail), upload
  date, open exceptions and the member who claimed the invoice.
- A PDF that a mail client marks as inline is still not taken as an attachment: the mail is skipped and logged, as for
  any mail without a valid attachment ([DEC-055](../decision-log.md#dec-055)).

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| — | None at decision-log level; the answers refine [DEC-057](../decision-log.md#dec-057) and [DEC-055](../decision-log.md#dec-055) and are recorded in the SAPS-46 and SAPS-45 specs | — | — |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Text filters: vendor = part of name or code, case-insensitive; invoice number = part of the number ignoring case, spaces and `-` `.` `/`; PO number = exact 7 digits on any line | Functional | SAPS-46 BR-03 | logged |
| R2 | The upload date filter uses the time zone of the company | Functional | SAPS-46 BR-04 | logged |
| R3 | Result columns: invoice number, vendor, invoice date, total, status, channel, upload date, open exceptions, claimed by | Functional | SAPS-46 BR-06 | logged |
| R4 | A PDF marked inline in a mail is not an invoice: the mail is skipped and logged | Functional | SAPS-45 BR-02, EC-04 | logged |

### 7.1 Conflicts with existing items
None.

### 7.2 ADR needs
None.

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Update the SAPS-46 spec with the answers | Solution Architect (our company) | 2027-03-01 | done |

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
