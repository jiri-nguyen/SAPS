---
id: MTG-20270301-5
title: "MTG-20270301-5 — Demo companies of Phase 2 (SAPS-42)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2027-03-01
related: [SAPS-42, DEC-056, DEC-060, DEC-061, DEC-052]
---

# MTG-20270301-5 — Demo companies of Phase 2 (SAPS-42)

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
| Recording / slides | [SAPS-42 feature spec](../../03-features/SAPS-42-companies-and-demo-data.md) |

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
| [SAPS-42](../../03-features/SAPS-42-companies-and-demo-data.md#7-open-questions) #Q1, #Q2, #Q5 | Demo companies, demo users, company name in the header | Answered → R1–R3 |

## 4. Agenda
1. Open questions Q1, Q2 and Q5 of the SAPS-42 feature spec

## 5. Discussion
- The demo shows three subsidiaries: Vietnam, Singapore and Malaysia; the team's proposals for names, codes, demo domains
  (under `example.com`), time zones and mailboxes were accepted.
- Demo users: 2 Accounting Members and 1 Accounting Manager per company.
- The Web App header shows the name of the signed-in user's company.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| — | None at decision-log level; the answers are demo data and a small UI detail, recorded in the SAPS-42 spec | — | — |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Demo companies: Demo Vietnam (`vn`, `vn.example.com`, `Asia/Ho_Chi_Minh`), Demo Singapore (`sg`, `sg.example.com`, `Asia/Singapore`), Demo Malaysia (`my`, `my.example.com`, `Asia/Kuala_Lumpur`); mailbox `ap@<domain>` | Demo data | SAPS-42 BR-02, `fixtures/companies.json` | logged |
| R2 | 2 Accounting Members and 1 Accounting Manager per demo company | Demo data | SAPS-42 BR-02 | logged |
| R3 | The header of the Web App shows the company name | Functional | SAPS-42 §3.4 (`UserAccount.companyName`) | logged |

### 7.1 Conflicts with existing items
None.

### 7.2 ADR needs
None.

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Update and approve the SAPS-42 spec with the answers | Solution Architect (our company) | 2027-03-01 | open |

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
