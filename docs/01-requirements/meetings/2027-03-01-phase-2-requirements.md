---
id: MTG-20270301-2
title: "MTG-20270301-2 — Phase 2 requirements (Q1–Q6 of the kickoff)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2027-03-01
related: [MTG-20270301, DEC-048, DEC-052, DEC-053, DEC-054, DEC-055, DEC-056, DEC-057, DEC-049, DEC-050, DEC-051, ADR-0007, ADR-0008, NFR-MAINT-001]
---

# MTG-20270301-2 — Phase 2 requirements (Q1–Q6 of the kickoff)

> **Assumption:** this meeting continued the Phase 2 kickoff on the same day (2027-03-01). To be confirmed by the
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
| [MTG-20270301](2027-03-01-phase-2-kickoff.md) #A1 | Apply the kickoff decisions | Done (DEC-047 … DEC-051, scope 0.7, nfr 0.4, NFR-MAINT-001) |
| [MTG-20270301](2027-03-01-phase-2-kickoff.md) #Q1 | Demo date, go-live, budget | Answered (demo) → R1; go-live and budget still open → Q1 |
| [MTG-20270301](2027-03-01-phase-2-kickoff.md) #Q2 | Environment of the Phase 2 demo | Answered → R2 |
| [MTG-20270301](2027-03-01-phase-2-kickoff.md) #Q3 | Keycloak: hosting, realm, user management | Partly answered → R3; realm per company or shared → Q2 |
| [MTG-20270301](2027-03-01-phase-2-kickoff.md) #Q4 | Mailbox intake | Answered → R4 |
| [MTG-20270301](2027-03-01-phase-2-kickoff.md) #Q5 | Multi-tenancy | Partly answered → R5; database model → Q3 |
| [MTG-20270301](2027-03-01-phase-2-kickoff.md) #Q6 | Invoice list and search | Answered → R6 |
| [MTG-20270301](2027-03-01-phase-2-kickoff.md) #Q7 – #Q12 | Priorities of other items, NFR targets, peaks, retention, load test, UI language | Still open |

## 4. Agenda
1. Open questions Q1–Q6 of the Phase 2 kickoff

## 5. Discussion
- Demo: 2027-08-30. Go-live is decided later.
- Environment: the team's proposal is accepted: the demo runs locally with Docker Compose like the PoC, plus a Keycloak
  container and a local test mail server; AWS after the demo ([NFR-MAINT-001](../nfr.md#nfr-maint-001)).
- Keycloak: the team runs it for the demo; users and roles are managed in the Keycloak admin console, no user management
  screens in the Web App. One realm for all companies or one per company is discussed in the next meeting.
- Mailbox intake: the real mail system later is Outlook (Microsoft 365). One mailbox per company; the mailbox that receives
  the mail tells the company. PDF, PNG and JPG attachments only, one attachment = one invoice. A mail without a valid
  attachment is skipped and logged. No check of the sender in Phase 2.
- Multi-tenancy: a user belongs to exactly one company. Matching settings, vendors and ERP data are kept per company. No
  system administrator role that sees all companies; administration through Keycloak. The database model (shared database
  with `tenant_id`, schema or database per company) is discussed in the next meeting.
- Invoice list and search: Accounting Members and Accounting Managers see all invoices of their own company in every
  status. Filters: status, vendor, invoice number, invoice date range, upload date range, total amount range, PO number,
  intake channel (upload or mail). Newest first, 20 per page. No export.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | Phase 2 demo on 2027-08-30; go-live date later | Product Owner (Customer) | [DEC-052](../decision-log.md#dec-052) |
| D2 | The Phase 2 demo runs locally with Docker Compose, with a Keycloak container and a local test mail server | Product Owner (Customer) | [DEC-053](../decision-log.md#dec-053) |
| D3 | Users and roles are managed in the Keycloak admin console; no user management screens and no system administrator role in the Web App in Phase 2 | Product Owner (Customer) | [DEC-054](../decision-log.md#dec-054) |
| D4 | Mailbox intake: one Outlook (Microsoft 365) mailbox per company; the receiving mailbox sets the company; PDF, PNG, JPG attachments, one attachment = one invoice; mails without a valid attachment are skipped and logged; no sender check in Phase 2 | Product Owner (Customer) | [DEC-055](../decision-log.md#dec-055) |
| D5 | A user belongs to exactly one company; matching settings, vendors and ERP data are per company | Product Owner (Customer) | [DEC-056](../decision-log.md#dec-056) |
| D6 | Invoice list and search: all invoices of the own company for Members and Managers; the filters listed in §5; newest first, 20 per page; no export | Product Owner (Customer) | [DEC-057](../decision-log.md#dec-057) |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Demo on 2027-08-30 | Project | [DEC-052](../decision-log.md#dec-052) (refines DEC-051); scope.md BO3 success measure | logged |
| R2 | Local Docker Compose for the Phase 2 demo with Keycloak and a test mail server | Infrastructure | [DEC-053](../decision-log.md#dec-053); scope.md SCP-IN-10 (covers Phase 2); arc42 §7 | logged |
| R3 | Keycloak run by the team; users and roles in the Keycloak admin console | Functional | [DEC-054](../decision-log.md#dec-054); SCP-IN-18; ADR on Keycloak sign-in | logged |
| R4 | Mailbox intake rules (D4) | Functional | [DEC-055](../decision-log.md#dec-055); SCP-IN-19; ADR on mailbox intake; feature spec | logged |
| R5 | Tenancy rules (D5) | Functional | [DEC-056](../decision-log.md#dec-056); SCP-IN-20; ADR on the tenancy model | logged |
| R6 | Invoice list and search rules (D6) | Functional | [DEC-057](../decision-log.md#dec-057); SCP-IN-22; feature spec | logged |

### 7.1 Conflicts with existing items
| Existing item | Conflict | Proposal |
|---|---|---|
| [SCP-IN-10](../scope.md#33-infrastructure--environments) "Local PoC environment" | Covers the PoC only | Scope 0.8: SCP-IN-10 also covers the Phase 2 demo, with Keycloak and a test mail server |
| [SCP-IN-13](../scope.md#31-functional-capabilities), [DEC-015](../decision-log.md#dec-015) | One set of matching settings | Already one set per tenant (SAPS-28 BR-02); DEC-056 confirms per company; no change |
| [SCP-IN-09](../scope.md#32-integrations) dummy ERP data | All scenarios are loaded together, for one company | Dummy ERP data per company (DEC-056) until the ERP integration (SCP-IN-15) |

### 7.2 ADR needs
- Keycloak sign-in (OIDC) replacing the simple accounts of ADR-0008: waits for the realm decision (Q2) for the tenant part.
- Mailbox intake: Microsoft Graph for Outlook later, a local test mail server for the demo, both behind a mail port
  ([NFR-MAINT-001](../nfr.md#nfr-maint-001)); polling or notifications; which attachments are accepted.
- Tenancy model: waits for Q3.

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Apply the confirmed decisions to the decision log and scope (version 0.8) | Solution Architect (our company) | 2027-03-01 | done (DEC-052 … DEC-057, scope 0.8) |
| A2 | Prepare options for Q2 (realm) and Q3 (database model) with pros and cons for the next meeting | Solution Architect (our company) | next meeting | open |
| A3 | List the Linear issues of Phase 2 for the Solution Architect to create | Solution Architect (our company) | after A1 | open |

## 9. Open Questions
| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| Q1 | Go-live date and budget (MTG-20261114 Q26) | Product Owner (Customer) | later | open |
| Q2 | Keycloak: one realm for all companies or one realm per company? | Product Owner (Customer) | next meeting | open |
| Q3 | Tenancy: shared database with `tenant_id` (ADR-0007), a schema per company, or a database per company? | Product Owner (Customer) | next meeting | open |
| Q4 | Kickoff Q7–Q12: priorities of ERP integration, non-PO checks, posting / export, GR-based verification; NFR targets; peaks; retention; load test; UI language | Product Owner (Customer) | next meeting | open |

## 10. Next Meeting
- To be agreed; topics: Q2 and Q3 with options from the team, then Q4.

## 11. Customer Confirmation
| Field | Value |
|---|---|
| Summary sent on | not sent; the Product Owner reviews the minutes directly |
| Confirmed on | pending |
| Reference | this document |
| Corrections received | none |
