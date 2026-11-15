---
id: MTG-20261128
title: "MTG-20261128 — PoC flow review and open questions"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2026-11-28
related: [MTG-20261121, ADR-0001, ADR-0002, ADR-0003, DEC-011, DEC-012, DEC-013, DEC-014, DEC-015, DEC-016, DEC-017, DEC-018, DEC-019, DEC-020, DEC-021]
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

### 5.5 Written answers after the meeting
The Product Owner answered Q1–Q5 in writing on 2026-11-28:
- The Product Owner is also the sign-off owner for the PoC acceptance.
- The three rejection points are confirmed.
- The Accounting Manager changes the tolerance and threshold settings.
- Notification recipients depend on the notification type; the flow in §6.2 is correct.
  Normal exceptions go to Accounting Members; invoices above 300 USD go to the Accounting Manager.
- All in-scope items are priority Must for the PoC.

## 6. Decisions
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | The Product Owner is the customer's single representative and decision maker | Product Owner (Customer) | [DEC-011](../decision-log.md#dec-011) |
| D2 | Uploading a file from the dummy sample set loads its predefined data; any other file raises EX1 | Product Owner (Customer) | [DEC-012](../decision-log.md#dec-012) |
| D3 | Approval comes before the final review; the 300 USD approval rule applies to all invoice types | Product Owner (Customer) | [DEC-013](../decision-log.md#dec-013) |
| D4 | Rejected is a final state | Product Owner (Customer) | [DEC-014](../decision-log.md#dec-014) |
| D5 | Price tolerance and approval threshold are configurable; defaults 0.5 USD and 300 USD | Product Owner (Customer) | [DEC-015](../decision-log.md#dec-015) |
| D6 | Exceptions go to a shared queue; any Accounting Member picks them up | Product Owner (Customer) | [DEC-016](../decision-log.md#dec-016) |
| D7 | PoC demo on 2027-02-22; no interim demo | Product Owner (Customer) | [DEC-017](../decision-log.md#dec-017) |
| D8 | Exception types EX1–EX9 are confirmed for the PoC | Product Owner (Customer) | [DEC-018](../decision-log.md#dec-018) |
| D9 | The customer agrees the PoC technology stack in ADR-0002 and ADR-0003 | Product Owner (Customer) | [DEC-019](../decision-log.md#dec-019) |
| D10 | PoC success = all flows run successfully in the demo | Product Owner (Customer) | [DEC-020](../decision-log.md#dec-020) |
| D11 | Notification recipients by type: exceptions and final reviews → Accounting Members; approvals above 300 USD → Accounting Manager (written answer Q4) | Product Owner (Customer) | [DEC-021](../decision-log.md#dec-021) |

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | The Product Owner is the only customer attendee, now and in future meetings, and the decision maker | Constraint | DEC-011; arc42 §1.3 stakeholders; glossary | logged |
| R2 | The end-to-end flow in arc42 §6.2 is approved | Functional | Remove "(proposal)" marks in §6.2 and §6.2.1 | logged |
| R3 | Uploading a file from the dummy sample set loads its predefined extraction data; a file not in the set raises an exception (EX1) | Functional | DEC-012; change SCP-IN-02 | logged |
| R4 | Approval (when required) comes before the final review | Functional | DEC-013; change SCP-IN-06 | logged |
| R5 | The 300 USD approval rule applies to all invoice types, including non-PO | Functional | DEC-013; change SCP-IN-06 | logged |
| R6 | Rejected is a final state | Functional | DEC-014; SCP-IN-14 (new) | logged |
| R7 | Price tolerance and approval threshold are adjustable; defaults 0.5 USD and 300 USD | Functional | DEC-015; SCP-IN-13 (new) | logged |
| R8 | Exceptions go to a shared queue; any available Accounting Member picks one up | Functional | DEC-016; change SCP-IN-04 | logged |
| R9 | PoC demo on 2027-02-22; no interim demo | Scope | DEC-017; change SCP-IN-11; change CON-02 | logged |
| R10 | Exception types EX1–EX9 are confirmed for the PoC | Functional | DEC-018; change SCP-IN-04 | logged |
| R11 | No performance target for the PoC, but the design must perform well and be able to scale in the future | NFR | arc42 §1.2 quality goal; NFR-SCAL-001 (target TBD); ADR need | logged |
| R12 | The customer agrees the PoC technology stack (ADR-0002, ADR-0003) | Constraint | DEC-019 | logged |
| R13 | No business objectives yet; PoC success = all flows run successfully | Scope | DEC-020; change BO2 success measure | logged |
| R14 | The Product Owner is the sign-off owner for the PoC acceptance (Q1) | Scope | DEC-011; scope.md §8, §10 | logged |
| R15 | Rejection points: Accounting Manager at approval; Accounting Member during exception handling and at final review (Q2) | Functional | DEC-014; SCP-IN-14 | logged |
| R16 | Only the Accounting Manager changes the tolerance and threshold settings (Q3) | Functional | DEC-015; SCP-IN-13 | logged |
| R17 | Notifications: exceptions and final reviews → Accounting Members; approvals above 300 USD → Accounting Manager (Q4) | Functional | DEC-021; change SCP-IN-08 | logged |
| R18 | All in-scope items are priority Must for the PoC (Q5) | Scope | scope.md AS2 → confirmed | logged |

### 7.1 Conflicts with existing items
| # | Existing item | Conflict | Proposed resolution |
|---|---|---|---|
| K1 | [DEC-003](../decision-log.md#dec-003), [CON-02](../../02-architecture/arc42/02-constraints.md): PoC lasts 3 months from 2026-11-21 (ends 2027-02-21) | Demo date 2027-02-22 is one day later | CON-02 and SCP-IN-11 state the demo date 2027-02-22; DEC-017 refines DEC-003 |
| K2 | [scope.md BO2](../scope.md#2-business-objectives): "demo for different cases, including exception cases" | Now "all flows run successfully" | DEC-020; BO2 success measure: every flow in the demo scenario catalog runs successfully |
| K3 | Earlier documents name the customer attendee "Customer representative" | Same person, now called Product Owner | Keep past records unchanged; new and updated documents use "Product Owner (Customer)" |
| K4 | [ADR-0002](../../02-architecture/adr/0002-use-python-fastapi-and-react.md), [ADR-0003](../../02-architecture/adr/0003-use-postgresql-and-docker-compose.md): "Customer agreement: TBD" | Accepted ADRs are immutable, so the text cannot be updated | Record the agreement in DEC-019, which links both ADRs |
| K5 | [§6.2 Runtime View](../../02-architecture/arc42/06-runtime-view.md) runtime note: processing runs inside the API request | Future scalability (R11) may need asynchronous processing | processing model ADR ([SAPS-33](https://linear.app/jiringuyen/issue/SAPS-33)); PoC keeps synchronous processing unless the ADR decides otherwise |
| K6 | Q4 answer says "exception > 300 USD" | In the agreed flow an invoice above 300 USD is an approval, not an exception | Recorded as approval notification to the Accounting Manager, as in §6.2; the Product Owner confirmed the flow is correct |

### 7.2 ADR needs
| # | Need | Driver |
|---|---|---|
| [SAPS-33](https://linear.app/jiringuyen/issue/SAPS-33) | Processing model for upload, extraction and matching: synchronous in the request, or a background worker / job queue, so the design can scale later | R11 |

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Draft the data model (entities, ERD, invoice lifecycle) in `data-model.md` ([SAPS-31](https://linear.app/jiringuyen/issue/SAPS-31)) | Solution Architect (our company) | 2026-12-05 | open |
| A2 | Draft the test strategy with a demo scenario catalog: happy paths per invoice type and one scenario per exception type EX1–EX9 ([SAPS-32](https://linear.app/jiringuyen/issue/SAPS-32)) | Solution Architect (our company) | 2026-12-05 | open |
| A3 | List the Linear epics and milestone (SA); create them in Linear manually (Product Owner / SA); add issue keys to scope.md | Solution Architect (our company) | 2026-12-05 | done: epics [SAPS-17](https://linear.app/jiringuyen/issue/SAPS-17) to [SAPS-30](https://linear.app/jiringuyen/issue/SAPS-30), tasks [SAPS-31](https://linear.app/jiringuyen/issue/SAPS-31) to [SAPS-33](https://linear.app/jiringuyen/issue/SAPS-33); keys added to scope.md v0.3 |
| A4 | Draft the processing model ADR ([SAPS-33](https://linear.app/jiringuyen/issue/SAPS-33)) | Solution Architect (our company) | 2026-12-05 | open |

## 9. Open Questions
| # | Question | Asked to | Due | Answer / status |
|---|---|---|---|---|
| Q1 | Is the Product Owner also the sign-off owner for the PoC acceptance (MTG-20261114 Q26)? | Product Owner (Customer) | 2026-12-05 | answered 2026-11-28 (written) → R14 |
| Q2 | Confirm the rejection points: Accounting Manager at approval; Accounting Member during exception handling (e.g. a real duplicate); Accounting Member at final review | Product Owner (Customer) | 2026-12-05 | answered 2026-11-28 (written) → R15 |
| Q3 | Which role may change the tolerance and threshold settings? Proposal: Accounting Manager | Product Owner (Customer) | 2026-12-05 | answered 2026-11-28 (written) → R16 |
| Q4 | Who receives in-app notifications? Proposal: every Accounting Member for exceptions and final reviews; every Accounting Manager for approvals | Product Owner (Customer) | 2026-12-05 | answered 2026-11-28 (written) → R17 |
| Q5 | Are all in-scope items priority Must for the PoC (scope.md AS2)? | Product Owner (Customer) | 2026-12-05 | answered 2026-11-28 (written) → R18 |

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
