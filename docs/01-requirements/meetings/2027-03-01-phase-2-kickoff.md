---
id: MTG-20270301
title: "MTG-20270301 — Phase 2 kickoff"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2027-03-01
related: [MTG-20261205, MTG-20261114, DEC-003, DEC-026, DEC-047, DEC-048, DEC-049, DEC-050, DEC-051, ADR-0007, ADR-0008, NFR-SCAL-001]
---

# MTG-20270301 — Phase 2 kickoff

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Time | TBD |
| Type | kickoff |
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
| PoC demo (2027-02-22) | Sign-off of the PoC by the Product Owner (BO2) | Confirmed by the Product Owner in this meeting → R1 |
| [MTG-20261205](2026-12-05-poc-architecture-review.md) #Q1 | Peak periods | Still open → Q9 |
| [MTG-20261205](2026-12-05-poc-architecture-review.md) #Q2 | Business hours: time zone | Answered: Singapore → R8 |
| [MTG-20261205](2026-12-05-poc-architecture-review.md) #Q3 | Retention of invoices, files and audit trail | Still open → Q10 |
| [MTG-20261114](2026-11-14-kickoff.md) #Q26 | Go-live, phases, budget | Phase 2 dates partly answered (R2, R6); go-live and budget still open → Q1 |
| [nfr.md](../nfr.md) Workload Profile | Users, volumes, locations | Partly answered → R7, R8 |

## 4. Agenda
1. Sign-off of the PoC and goal of Phase 2
2. New requirements and scope of Phase 2
3. Priorities and timeline
4. Volumes, users and time zone

## 5. Discussion
- The Product Owner confirmed that the PoC succeeded. Phase 2 starts today and runs about 6 months.
- Scope: most items that were out of the PoC scope are now in scope (R3). New requirement: after an invoice is
  processed it disappears from the Web App; users need to see and search all invoices (R4).
- Priority: Single Sign-On with Keycloak, invoice intake from a mailbox and multi-tenancy come first. The Product
  Owner has no AWS account and no OCR / AI extraction service yet, so cloud deployment and real extraction have a lower
  priority. "Getting the flow working end to end matters more" (R5).
- Demo: the Product Owner needs a demo of the new features by a deadline, like the PoC; no other release is asked for (R6).
- The demo shows the system for about 3 companies, each processing 1,000 invoices per day; about 30 users in total
  (Accounting Members and Accounting Managers of the 3 companies); time zone Singapore (R7, R8).

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | The PoC is accepted (BO2 met) | Product Owner (Customer) | [DEC-047](../decision-log.md#dec-047) |
| D2 | Phase 2 scope: SCP-OUT-02, -07, -08, -10, -11, -12, -13 move into scope; new: invoice list and search; OCR / AI (SCP-OUT-01) and AWS (SCP-OUT-09) after the Phase 2 demo `[CR]` | Product Owner (Customer) | [DEC-048](../decision-log.md#dec-048) |
| D3 | Single Sign-On uses Keycloak | Product Owner (Customer) | [DEC-049](../decision-log.md#dec-049) |
| D4 | Priorities of Phase 2: SSO (Keycloak), mailbox intake and multi-tenancy first; AWS deployment and OCR / AI extraction move after the Phase 2 demo, and the design must make them easy to add later | Product Owner (Customer) | [DEC-050](../decision-log.md#dec-050) |
| D5 | Phase 2 starts 2027-03-01, about 6 months, ends with a demo of the new features; no interim release | Product Owner (Customer) | [DEC-051](../decision-log.md#dec-051) |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | PoC accepted; BO2 met | Project | [DEC-047](../decision-log.md#dec-047); scope.md BO2 | logged |
| R2 | Phase 2 starts 2027-03-01 and lasts about 6 months | Project | [DEC-051](../decision-log.md#dec-051) | logged |
| R3 | In scope now: ERP integration via MuleSoft (OUT-02), automated checks for non-PO invoices (OUT-07), posting or export to the ERP (OUT-08), SSO with Keycloak (OUT-10), mailbox intake (OUT-11), multi-tenancy (OUT-12), GR-based verification (OUT-13). Still out: OUT-03, -04, -05, -06, -14, -15; OUT-01 and OUT-09 see R9 | Scope | [DEC-048](../decision-log.md#dec-048) `[CR]`; scope.md 0.7: SCP-IN-15 … SCP-IN-21, those SCP-OUT items withdrawn with a link | logged |
| R4 | Users can see and search all invoices, also after processing (today Completed and Rejected invoices disappear from the Web App) | Functional | [DEC-048](../decision-log.md#dec-048); SCP-IN-22 | logged |
| R5 | Order: SSO, mailbox intake, multi-tenancy first; AWS and OCR / AI later because the Product Owner has neither yet | Project | [DEC-050](../decision-log.md#dec-050) | logged |
| R6 | A demo of the new features at the end of Phase 2, like the PoC; no interim release | Project | [DEC-051](../decision-log.md#dec-051); scope.md BO3; Phase 2 demo scenarios in the test strategy (later) | logged |
| R7 | About 3 companies, each 1,000 invoices per day; about 30 users in total | NFR | nfr.md 0.4 Workload Profile; NFR-SCAL-001 unchanged (the numbers fit its target); targets per Q8 | logged |
| R8 | Users work in Singapore time (SGT, UTC+8) | NFR | nfr.md 0.4 Workload Profile "Operating hours", "User locations" | logged |
| R9 | Update after the meeting: OCR / AI extraction (OUT-01) and AWS deployment (OUT-09) move after the Phase 2 demo; the design must make it easy to add them later | Scope / NFR | [DEC-048](../decision-log.md#dec-048), [DEC-050](../decision-log.md#dec-050); scope.md SCP-OUT-01, -09; NFR-MAINT-001 | proposed (NFR-MAINT-001) |

### 7.1 Conflicts with existing items
| Existing item | Conflict | Proposal |
|---|---|---|
| [ADR-0008](../../02-architecture/adr/0008-use-session-cookies-for-authentication.md), [NFR-SEC-001](../nfr.md#nfr-sec-001), [SCP-IN-12](../scope.md#31-functional-capabilities) | Simple user accounts in the SAPS Database vs Single Sign-On with Keycloak | New ADR (sign-in with Keycloak, OIDC); supersedes ADR-0008 where needed; NFR-SEC-001 new version |
| [ADR-0007](../../02-architecture/adr/0007-prepare-data-model-for-tenants.md), SCP-OUT-12 | The PoC only prepared the data model for tenants | New ADR on the tenancy model (isolation, tenant of a user, settings per company) |
| [DEC-026](../decision-log.md#dec-026) | AWS is the target, but no AWS account is available yet | Direction unchanged; AWS moves after the Phase 2 demo ([DEC-050](../decision-log.md#dec-050)); where the Phase 2 demo runs is open (Q2) |
| [DEC-003](../decision-log.md#dec-003), SCP-IN-10 | "PoC runs locally" | Stays true until AWS is available; to be confirmed for Phase 2 (Q2) |
| [DEC-041](../decision-log.md#dec-041), [DEC-039](../decision-log.md#dec-039) | Four-eyes rule and "return for correction" stay out (OUT-14, OUT-15) | None; confirmed out of scope (R3) |

### 7.2 ADR needs
- Sign-in with Keycloak (OIDC), roles from Keycloak, impact on sessions and the Origin check (ADR-0008).
- Tenancy model: one database with `tenant_id` (ADR-0007) vs a schema or a database per company; how a user belongs to a company.
- Mailbox intake: mail provider and protocol (Microsoft Graph, Gmail API, IMAP), one mailbox per company or one shared.
- Later in the phase: ERP integration via MuleSoft. After the Phase 2 demo: OCR / AI extraction service and AWS deployment (the Phase 2 design keeps both easy to add, NFR-MAINT-001).

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Apply the confirmed decisions to the decision log, scope (new version) and NFRs | Solution Architect (our company) | 2027-03-01 | done (DEC-047 … DEC-051, scope 0.7, nfr 0.4) |
| A2 | Answer the open questions Q1–Q12 | Product Owner (Customer) | next meeting | open |
| A3 | Create the Linear issues for Phase 2 (the team lists them) | Solution Architect (our company) | after A1 | open |

## 9. Open Questions
| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| Q1 | Demo date of Phase 2? Go-live date and budget (MTG-20261114 Q26)? | Product Owner (Customer) | next meeting | open |
| Q2 | Without AWS, where does the Phase 2 demo run: locally with Docker Compose like the PoC, or another environment? | Product Owner (Customer) | next meeting | open |
| Q3 | Keycloak: does your company already run one, or do we run it? One realm for all companies or one per company? Where are the users and roles managed? | Product Owner (Customer) | next meeting | open |
| Q4 | Mailbox intake: which mail system (Microsoft 365, Google Workspace, other)? One mailbox per company? Only PDF / image attachments? What happens to mails without an invoice? | Product Owner (Customer) | next meeting | open |
| Q5 | Multi-tenancy: may a user work for more than one company? Must each company have its own matching settings, vendors and ERP data? How strictly must the data be separated? | Product Owner (Customer) | next meeting | open |
| Q6 | Invoice list and search: who sees which invoices (all of the own company?), which filters (status, vendor, invoice number, date, amount, PO), export needed? | Product Owner (Customer) | next meeting | open |
| Q7 | Priority of the other in-scope items: ERP integration via MuleSoft (OUT-02, OUT-08), checks for non-PO invoices (OUT-07), GR-based verification (OUT-13)? Is MuleSoft / SAP access available in this phase? | Product Owner (Customer) | next meeting | open |
| Q8 | Are there performance or availability targets for the demo (for example: an invoice processed within N minutes)? | Product Owner (Customer) | next meeting | open |
| Q9 | Peak periods (for example month end) and how much higher than average? (MTG-20261205 Q1) | Product Owner (Customer) | next meeting | open |
| Q10 | Retention of invoices, files and the audit trail (MTG-20261205 Q3)? | Product Owner (Customer) | next meeting | open |
| Q11 | Must the 1,000 invoices per day per company be shown in the demo (load test), or is it design information as in the PoC? | Product Owner (Customer) | next meeting | open |
| Q12 | Language of the user interface: still English only for the 3 companies? | Product Owner (Customer) | next meeting | open |

## 10. Next Meeting
- To be agreed; topic: answers to Q1–Q12.

## 11. Customer Confirmation
| Field | Value |
|---|---|
| Summary sent on | not sent; the Product Owner reviews the minutes directly |
| Confirmed on | pending |
| Reference | this document |
| Corrections received | none |
