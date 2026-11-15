---
id: MTG-20261128
title: "MTG-20261128 — PoC flow review and open questions"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2026-11-28
related: [MTG-20261121, ADR-0001, ADR-0002, ADR-0003]
---

# MTG-20261128 — PoC flow review and open questions

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2026-11-28 |
| Time | TBD |
| Type | design review |
| Channel | TBD |
| Facilitator | Solution Architect (our company) |
| Note taker | Solution Architect (our company) |
| Recording / slides | [§6 Runtime View](../../02-architecture/arc42/06-runtime-view.md) |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20261121](2026-11-21-requirements-workshop.md) #A1 | Attendee list and key contacts | Closed: the Product Owner is the only customer attendee, now and in future meetings → R1 |
| [MTG-20261121](2026-11-21-requirements-workshop.md) #A2 | End-to-end PoC flow | Done; reviewed and approved in this meeting → R2 |
| [MTG-20261121](2026-11-21-requirements-workshop.md) #A3 | Send meeting summary | Done 2026-11-21 |
| [MTG-20261121](2026-11-21-requirements-workshop.md) #A4 | ADR drafts | Done: ADR-0001, ADR-0002, ADR-0003 accepted |
| [MTG-20261121](2026-11-21-requirements-workshop.md) #Q1 | Upload with dummy extraction | Answered → R3 |
| [MTG-20261121](2026-11-21-requirements-workshop.md) #Q2 | Order of approval and final review | Answered → R4 |
| [MTG-20261121](2026-11-21-requirements-workshop.md) #Q3 | Rejected invoices | Answered → R6; rejection points still to confirm (Q2 below) |
| [MTG-20261121](2026-11-21-requirements-workshop.md) #Q4 | Approval rule for non-PO invoices | Answered → R5 |
| [MTG-20261121](2026-11-21-requirements-workshop.md) #Q5 | Configurable tolerance and threshold | Answered → R7 |
| [MTG-20261121](2026-11-21-requirements-workshop.md) #Q6 | Exception assignment | Answered → R8 |
| [MTG-20261121](2026-11-21-requirements-workshop.md) #Q7 | PoC end date and demo date | Answered → R9 |
| [MTG-20261121](2026-11-21-requirements-workshop.md) #Q8 | Exception list EX1–EX9 | Answered → R10 |
| [nfr.md](../nfr.md#5-open-questions) #Q1 | Response-time target for the PoC demo | Answered → R11 |
| [MTG-20261114](2026-11-14-kickoff.md) #Q1 | Organization and legal entities | Still open; not needed for the PoC |
| [MTG-20261114](2026-11-14-kickoff.md) #Q3 | Business objectives and success measures | Partly answered: none yet; PoC success → R13 |
| [MTG-20261114](2026-11-14-kickoff.md) #Q5, #Q6 | Invoice volume, peak periods | Still open; needed after the PoC |
| [MTG-20261114](2026-11-14-kickoff.md) #Q9 | Other intake channels, e-invoice XML | Still open; not needed for the PoC |
| [MTG-20261114](2026-11-14-kickoff.md) #Q23 | Exception assignment | Answered → R8 |
| [MTG-20261114](2026-11-14-kickoff.md) #Q26 | Go-live, phases, budget, UAT, sign-off | Partly answered: demo date → R9. Sign-off owner → Q1 below |
| [MTG-20261114](2026-11-14-kickoff.md) #Q27, #Q30, #Q31 | Cloud, retention, operating hours | Still open; needed after the PoC |
| [MTG-20261114](2026-11-14-kickoff.md) #Q7, #Q8, #Q10–#Q12, #Q28 | Extraction details | Deferred (dummy extraction in the PoC) |

## 4. Agenda
1. Follow-up from MTG-20261121
2. Review of the end-to-end PoC flow
3. Open questions Q1–Q8 of MTG-20261121
4. Other questions: performance, tech stack agreement, business objectives

## 5. Discussion
### 5.1 Follow-up
- The Product Owner is the only customer attendee, now and in future meetings.

### 5.2 End-to-end PoC flow
- The SA presented the flow in [§6.2](../../02-architecture/arc42/06-runtime-view.md): upload → dummy extraction →
  duplicate check, type derivation, matching → exception loop → approval above 300 USD → final review → completed.
- The Product Owner approved the flow.

### 5.3 Open questions
- A file that is not in the dummy sample set raises an exception.
- Approval comes before the final review.
- Rejected is a final state.
- The 300 USD approval rule also applies to non-PO invoices.
- Price tolerance and approval threshold are adjustable; 0.5 USD and 300 USD are the defaults.
- Exceptions go to a shared queue; any available Accounting Member picks them up.
- The demo is on 2027-02-22. No interim demo.
- Exception types EX1–EX9 are confirmed for now.

### 5.4 Other questions
- No performance target for the PoC. The design must still perform well and be able to scale in the future.
- The Product Owner agrees the PoC technology stack (ADR-0002, ADR-0003).
- No business objectives yet. At this point, the PoC is successful when all flows run successfully.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | The Product Owner is the customer's single representative and decision maker | Product Owner (Customer) | pending |
| D2 | Uploading a file from the dummy sample set loads its predefined data; any other file raises EX1 | Product Owner (Customer) | pending |
| D3 | Approval comes before the final review; the 300 USD approval rule applies to all invoice types | Product Owner (Customer) | pending |
| D4 | Rejected is a final state | Product Owner (Customer) | pending |
| D5 | Price tolerance and approval threshold are configurable; defaults 0.5 USD and 300 USD | Product Owner (Customer) | pending |
| D6 | Exceptions go to a shared queue; any Accounting Member picks them up | Product Owner (Customer) | pending |
| D7 | PoC demo on 2027-02-22; no interim demo | Product Owner (Customer) | pending |
| D8 | Exception types EX1–EX9 are confirmed for the PoC | Product Owner (Customer) | pending |
| D9 | The customer agrees the PoC technology stack in ADR-0002 and ADR-0003 | Product Owner (Customer) | pending |
| D10 | PoC success = all flows run successfully in the demo | Product Owner (Customer) | pending |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | The Product Owner is the only customer attendee, now and in future meetings, and the decision maker | Constraint | DEC-011; arc42 §1.3 stakeholders; glossary | proposed |
| R2 | The end-to-end flow in arc42 §6.2 is approved | Functional | Remove "(proposal)" marks in §6.2 and §6.2.1 | proposed |
| R3 | Uploading a file from the dummy sample set loads its predefined extraction data; a file not in the set raises an exception (EX1) | Functional | DEC-012; change SCP-IN-02 | proposed |
| R4 | Approval (when required) comes before the final review | Functional | DEC-013; change SCP-IN-06 | proposed |
| R5 | The 300 USD approval rule applies to all invoice types, including non-PO | Functional | DEC-013; change SCP-IN-06 | proposed |
| R6 | Rejected is a final state | Functional | DEC-014; SCP-IN-14 (new) | proposed |
| R7 | Price tolerance and approval threshold are adjustable; defaults 0.5 USD and 300 USD | Functional | DEC-015; SCP-IN-13 (new) | proposed |
| R8 | Exceptions go to a shared queue; any available Accounting Member picks one up | Functional | DEC-016; change SCP-IN-04 | proposed |
| R9 | PoC demo on 2027-02-22; no interim demo | Scope | DEC-017; change SCP-IN-11; change CON-02 | proposed |
| R10 | Exception types EX1–EX9 are confirmed for the PoC | Functional | DEC-018; change SCP-IN-04 | proposed |
| R11 | No performance target for the PoC, but the design must perform well and be able to scale in the future | NFR | arc42 §1.2 quality goal; NFR-SCAL-001 (target TBD); ADR need | proposed |
| R12 | The customer agrees the PoC technology stack (ADR-0002, ADR-0003) | Constraint | DEC-019 | proposed |
| R13 | No business objectives yet; PoC success = all flows run successfully | Scope | DEC-020; change BO2 success measure | proposed |

### 7.1 Conflicts with existing items
| # | Existing item | Conflict | Proposed resolution |
|---|---|---|---|
| K1 | [DEC-003](../decision-log.md#dec-003), [CON-02](../../02-architecture/arc42/02-constraints.md): PoC lasts 3 months from 2026-11-21 (ends 2027-02-21) | Demo date 2027-02-22 is one day later | CON-02 and SCP-IN-11 state the demo date 2027-02-22; DEC-017 refines DEC-003 |
| K2 | [scope.md BO2](../scope.md#2-business-objectives): "demo for different cases, including exception cases" | Now "all flows run successfully" | DEC-020; BO2 success measure: every flow in the demo scenario catalog runs successfully |
| K3 | Earlier documents name the customer attendee "Customer representative" | Same person, now called Product Owner | Keep past records unchanged; new and updated documents use "Product Owner (Customer)" |
| K4 | [ADR-0002](../../02-architecture/adr/0002-use-python-fastapi-and-react.md), [ADR-0003](../../02-architecture/adr/0003-use-postgresql-and-docker-compose.md): "Customer agreement: TBD" | Accepted ADRs are immutable, so the text cannot be updated | Record the agreement in DEC-019, which links both ADRs |
| K5 | [§6.2 Runtime View](../../02-architecture/arc42/06-runtime-view.md) runtime note: processing runs inside the API request | Future scalability (R11) may need asynchronous processing | ADR need ADR-N1 below; PoC keeps synchronous processing unless the ADR decides otherwise |

### 7.2 ADR needs
| # | Need | Driver |
|---|---|---|
| ADR-N1 | Processing model for upload, extraction and matching: synchronous in the request, or a background worker / job queue, so the design can scale later | R11 |

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Draft the data model (entities, ERD, invoice lifecycle) in `data-model.md` | Solution Architect (our company) | 2026-12-05 | open |
| A2 | Draft the test strategy with a demo scenario catalog: happy paths per invoice type and one scenario per exception type EX1–EX9 | Solution Architect (our company) | 2026-12-05 | open |
| A3 | Create Linear epics for the in-scope items and add the Linear base URL to the Project Context | Solution Architect (our company) | 2026-12-05 | open |
| A4 | Draft ADR-N1 (processing model) | Solution Architect (our company) | 2026-12-05 | open |

## 9. Open Questions
| # | Question | Asked to | Due | Answer / status |
|---|---|---|---|---|
| Q1 | Is the Product Owner also the sign-off owner for the PoC acceptance (MTG-20261114 Q26)? | Product Owner (Customer) | 2026-12-05 | open |
| Q2 | Confirm the rejection points: Accounting Manager at approval; Accounting Member during exception handling (e.g. a real duplicate); Accounting Member at final review | Product Owner (Customer) | 2026-12-05 | open |
| Q3 | Which role may change the tolerance and threshold settings? Proposal: Accounting Manager | Product Owner (Customer) | 2026-12-05 | open |
| Q4 | Who receives in-app notifications? Proposal: every Accounting Member for exceptions and final reviews; every Accounting Manager for approvals | Product Owner (Customer) | 2026-12-05 | open |
| Q5 | Are all in-scope items priority Must for the PoC (scope.md AS2)? | Product Owner (Customer) | 2026-12-05 | open |

## 10. Next Meeting
- Date: 2026-12-05, time TBD
- Planned topics: data model review (A1), demo scenario catalog (A2), processing model ADR (A4), open questions Q1–Q5.

## 11. Customer Confirmation
| Field | Value |
|---|---|
| Summary sent on | not sent; the Product Owner reviews the minutes directly |
| Confirmed on | pending |
| Reference | this document |
| Corrections received | none |
