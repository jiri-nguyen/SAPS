---
id: MTG-20270301-3
title: "MTG-20270301-3 — Tenancy model and Keycloak realm (Q2, Q3)"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2027-03-01
related: [MTG-20270301, MTG-20270301-2, DEC-026, DEC-054, DEC-056, DEC-058, DEC-059, DEC-060, DEC-061, ADR-0009, ADR-0010]
---

# MTG-20270301-3 — Tenancy model and Keycloak realm (Q2, Q3)

> **Assumption:** this meeting took place on the same day as the Phase 2 kickoff (2027-03-01). To be confirmed by the
> Solution Architect (our company).

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Time | TBD |
| Type | architecture review |
| Channel | TBD |
| Facilitator | Solution Architect (our company) |
| Note taker | Solution Architect (our company) |
| Recording / slides | [ADR-0009](../../02-architecture/adr/0009-isolate-tenant-data-in-a-shared-database.md), [ADR-0010](../../02-architecture/adr/0010-use-one-keycloak-realm-with-company-groups.md) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #A1 | Apply decisions DEC-052 … DEC-057 | Done (scope 0.8) |
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #A2 | Options for Q2 and Q3 | Done: ADR-0009, ADR-0010 presented |
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #Q2 | One Keycloak realm or one per company | Answered → D2 |
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #Q3 | Database model for tenants | Answered → D1 |
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #Q1, #Q4 | Go-live and budget; kickoff Q7–Q12 | Still open |

## 4. Agenda
1. Factors for the database model (Q3) and the options of ADR-0009
2. Keycloak realm options (Q2) and the later move to Microsoft Entra ID (ADR-0010)

## 5. Discussion
- Context given by the Product Owner: the companies are subsidiaries of one group, in several countries; about 3 now, more
  subsidiaries later. Customers outside the group are a possible later direction, not certain.
- Factors for the database model: no legal or contractual need to keep a subsidiary's data physically apart; no plan to
  sell or split off a subsidiary; no group-wide reporting across subsidiaries; the same retention and infrastructure for
  all. Whether data-residency laws of the countries apply is not known (→ Q1).
- The Product Owner chose the shared database with `tenant_id` and row-level security. If residency rules or customers
  outside the group appear, the same stack is deployed once per region or per customer group.
- Identity: all subsidiaries sign in with one shared Microsoft Entra ID of the group; each subsidiary has its own e-mail
  domain (for example `vn.xxx.com`, `sg.xxx.com`). Entra ID integration is expected in a later phase; the demo uses local
  Keycloak users. The team keeps assigning company and role in Keycloak (DEC-054).
- The Product Owner asked whether moving to Entra ID later is simple. Answer: yes, if Keycloak stays the broker: Entra ID is
  added to the realm as an identity provider and the SAPS code does not change (ADR-0010).
- The Product Owner chose one realm with a group per company.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | Tenant data in one shared database with `tenant_id` and PostgreSQL row-level security (ADR-0009) | Product Owner (Customer), on a proposal by the Solution Architect | [DEC-058](../decision-log.md#dec-058) |
| D2 | One Keycloak realm, one group per company, e-mail domain checked; Entra ID brokered by Keycloak later (ADR-0010) | Product Owner (Customer), on a proposal by the Solution Architect | [DEC-059](../decision-log.md#dec-059) |
| D3 | The companies are subsidiaries of one group in several countries; more subsidiaries later; customers outside the group are a possible direction, not certain | Product Owner (Customer) | [DEC-060](../decision-log.md#dec-060) |
| D4 | One shared Entra ID for the group; one e-mail domain per subsidiary; Entra ID integration in a later phase, not for the demo | Product Owner (Customer) | [DEC-061](../decision-log.md#dec-061) |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Database model D1 | Architecture | [DEC-058](../decision-log.md#dec-058); [ADR-0009](../../02-architecture/adr/0009-isolate-tenant-data-in-a-shared-database.md) accepted | logged |
| R2 | Customer context D3, including: no physical separation, no divestment, no group reporting, same retention | Business | [DEC-060](../decision-log.md#dec-060) (refines [DEC-026](../decision-log.md#dec-026)) | logged |
| R3 | Identity model D2 and identity facts D4 | Architecture / Business | [DEC-059](../decision-log.md#dec-059), [DEC-061](../decision-log.md#dec-061); [ADR-0010](../../02-architecture/adr/0010-use-one-keycloak-realm-with-company-groups.md) accepted | logged |

### 7.1 Conflicts with existing items
| Existing item | Conflict | Proposal |
|---|---|---|
| [DEC-026](../decision-log.md#dec-026) "many customer companies" | The companies are subsidiaries of one group; outside customers uncertain | Refined by DEC-060; direction unchanged |
| [TD-02](../../02-architecture/arc42/11-risks-and-technical-debt.md#td-02) no tenant isolation | Resolved by ADR-0009 once implemented | TD-02 stays open until the multi-tenancy issue is done |

### 7.2 ADR needs
- Sign-in flow of the SAPS Web App with Keycloak (session cookie through the SAPS API as in ADR-0008, or tokens in the browser).
- Mailbox intake (Microsoft Graph later, test mail server for the demo).

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Record DEC-058 … DEC-061; set ADR-0009 and ADR-0010 to accepted | Solution Architect (our company) | 2027-03-01 | done |
| A2 | Ask the group legal / IT whether invoice data must stay in its country (Q1) | Product Owner (Customer) | before the deployment on AWS | open |
| A3 | List the Linear issues of Phase 2 for the Solution Architect to create | Solution Architect (our company) | next | open |

## 9. Open Questions
| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| Q1 | Do the laws of the subsidiaries' countries require invoice data to stay in the country? | Product Owner (Customer), group legal / IT | before the deployment on AWS | open |

Still open from earlier minutes: [MTG-20270301-2](2027-03-01-phase-2-requirements.md) Q1 (go-live, budget) and Q4 (kickoff Q7–Q12).

## 10. Next Meeting
- To be agreed; topic: kickoff Q7–Q12.

## 11. Customer Confirmation
| Field | Value |
|---|---|
| Summary sent on | not sent; the Product Owner reviews the minutes directly |
| Confirmed on | pending |
| Reference | this document |
| Corrections received | none |
