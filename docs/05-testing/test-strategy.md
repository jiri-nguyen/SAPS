---
title: Test Strategy
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Tech Lead (TBD)", "Product Owner (Customer)"]
last_updated: 2026-11-28
related: [ADR-0004, ADR-0006, DEC-003, DEC-011, DEC-017, DEC-018, DEC-020, NFR-SCAL-001, NFR-SEC-001, NFR-USAB-001, SAPS-32]
---

# Test Strategy

Scope: Proof of Concept ([DEC-003](../01-requirements/decision-log.md#dec-003)). Linear: [SAPS-32](https://linear.app/jiringuyen/issue/SAPS-32).

## 1. Introduction
- **Goal:** prove that all flows run successfully in the demo on 2027-02-22
  ([DEC-020](../01-requirements/decision-log.md#dec-020), [DEC-017](../01-requirements/decision-log.md#dec-017)).
  The [demo scenario catalog](#11-poc-demo-acceptance) defines "all flows".
- **In scope:** SAPS Web App, SAPS API, SAPS Worker and SAPS Message Broker ([ADR-0004](../02-architecture/adr/0004-process-invoices-in-background-worker.md)), SAPS File Storage ([ADR-0006](../02-architecture/adr/0006-store-invoice-files-in-seaweedfs.md)), SAPS Database; Dummy Extraction Adapter and Dummy ERP Adapter; NFRs in [nfr.md](../01-requirements/nfr.md) v0.2.
- **Out of scope:** real OCR/AI extraction and SAP / MuleSoft integration ([SCP-OUT-01, SCP-OUT-02](../01-requirements/scope.md#4-out-of-scope)); performance and load testing; cloud environments.
- **Test case management:** in code only (pytest, Playwright). Demo scenarios are listed in §11; each has one automated end-to-end test.
- **References:** [Scope](../01-requirements/scope.md) · [NFRs](../01-requirements/nfr.md) · [Data Model](../02-architecture/data-model.md) · [§6 Runtime View](../02-architecture/arc42/06-runtime-view.md)

## 2. Test Levels & Types
| Level / type | Purpose | Scope | Responsible | Tools | Automated | When / environment |
|---|---|---|---|---|---|---|
| Unit | Matching rules, type derivation, tolerance, approval and state transitions | SAPS API / SAPS Worker domain logic; SAPS Web App components | Dev | pytest; Vitest + React Testing Library (proposal) | Yes | CI on every PR |
| Integration | SAPS API and SAPS Worker with real PostgreSQL, Redis and SeaweedFS; redelivery after a worker stop; sweeper recovers invoices without a message; idempotent actors | SAPS API, SAPS Worker | Dev | pytest + Testcontainers (PostgreSQL, Redis, SeaweedFS) (proposal) | Yes | CI on every PR |
| Contract | SAPS API matches its OpenAPI specification | SAPS API | Dev | Schemathesis (proposal) | Yes | CI on every PR, once `saps-api.openapi.yaml` exists |
| End-to-end | Demo scenarios DS-01 … DS-19 (§11) | UC-01 … UC-08 | SA | Playwright (proposal) | Yes | local, clean Docker Compose stack, before each demo rehearsal |
| Regression | Previously passing demo scenarios still pass | E2E suite | SA | Playwright | Yes | local, before merging to main |
| Security | Vulnerable dependencies, insecure code patterns | all code | Dev | pip-audit, npm audit, Bandit (proposal) | Yes | CI on every PR |
| Demo acceptance | Product Owner accepts the PoC | all demo scenarios | Product Owner (SA supports) | live demo | No | demo on 2027-02-22 |

Not applicable in the PoC: performance (no target, [MTG-20261128](../01-requirements/meetings/2026-11-28-poc-flow-review.md) R11), DR / resilience (local only, [CON-01](../02-architecture/arc42/02-constraints.md)).

## 3. Test Environments
| Environment | Used for | Data | Refresh | Access |
|---|---|---|---|---|
| local (developer machine) | unit, integration, development testing | synthetic fixtures | on demand | team |
| demo (local Docker Compose on the demo machine) | end-to-end, regression, demo rehearsal, demo acceptance | dummy sample set + dummy ERP data | recreated before each rehearsal and before the demo | team; Product Owner at the demo |

There are no dev / stg / prod environments in the PoC ([CON-01](../02-architecture/arc42/02-constraints.md), [ADR-0003](../02-architecture/adr/0003-use-postgresql-and-docker-compose.md)).

## 4. Test Data Management
- Source: JSON fixtures in the repository — the dummy sample set (invoice files with predefined extraction data,
  [DEC-012](../01-requirements/decision-log.md#dec-012)) and dummy ERP data (vendors, POs, goods receipts).
  One fixture set per demo scenario, so scenarios do not interfere.
- Masking rules: not needed — all data is synthetic; no real invoices, vendors or people.
- Volume: demo scale; no volume testing.
- Ownership: the Solution Architect owns the fixtures; any change to a fixture is reviewed together with the scenario it serves.

## 5. Quality Gates
| Gate | Criteria | Enforced at |
|---|---|---|
| Pull request | Build green; unit + integration tests pass; coverage ≥ 90 % on changed code; no high findings from dependency scan or Bandit; review approved | PR checks |
| Merge to main | Pull request gate + E2E regression suite passes | PR checks |
| Demo readiness | All demo scenarios DS-01 … DS-19 pass on a freshly created demo stack; no open Critical or High defects | Demo rehearsal checklist |

## 6. Entry & Exit Criteria
| Phase | Entry criteria | Exit criteria |
|---|---|---|
| Demo rehearsal | All epics SAPS-17 … SAPS-29 done; demo stack builds from scratch; fixtures loaded | All demo scenarios pass; no open Critical/High defects |
| Demo acceptance (2027-02-22) | Last rehearsal passed | Product Owner signs off ([DEC-011](../01-requirements/decision-log.md#dec-011)) |

## 7. Defect Management
| Severity | Definition | Example | Target fix |
|---|---|---|---|
| Critical | A demo scenario cannot run, or data is corrupted, no workaround | Upload crashes the SAPS API | before the next rehearsal |
| High | A demo scenario ends in the wrong state | EX6 not raised for a 0.60 USD price difference | before the next rehearsal |
| Medium | Wrong detail, workaround exists | Notification text shows the wrong amount | before the demo, if time allows |
| Low | Cosmetic | Misaligned label | backlog |

- Tracker: Linear project [Smart-AP-Suite](https://linear.app/jiringuyen/project/smart-ap-suite-766faab061af/overview), label `bug`; workflow Backlog → In Progress → In Review → Done.
- Investigation: bugs that meet the RCA criteria in CLAUDE.md get a Root Cause Analysis in `docs/07-operations/rca/`.
- Release rule: no open Critical or High defects at the demo.

## 8. Traceability & NFR Verification
Functional coverage: each demo scenario names the use cases, decisions and exception types it covers (§11).

| NFR | Verification method | Evidence | Phase |
|---|---|---|---|
| [NFR-SCAL-001](../01-requirements/nfr.md#nfr-scal-001) | Review | Architecture review of ADR-0001, ADR-0004 and the code structure (ports, stateless SAPS API, scalable SAPS Worker); review record in Linear | before the demo |
| [NFR-SEC-001](../01-requirements/nfr.md#nfr-sec-001) | Demo | DS-19 (automated E2E test + live demo) | demo |
| [NFR-USAB-001](../01-requirements/nfr.md#nfr-usab-001) | Demo | All screens shown in the demo are in English; checked in the rehearsal checklist | demo |

## 9. Performance Testing Approach
None in the PoC: there is no performance target ([MTG-20261128](../01-requirements/meetings/2026-11-28-poc-flow-review.md) R11).
Scalability is verified by review (NFR-SCAL-001). Load tests and PSRs start after the PoC, when the workload profile is known (MTG-20261114 Q5, Q6).

## 10. Security Testing Approach
- SAST: Bandit (Python), on every PR (proposal).
- Dependency scanning: pip-audit and npm audit, on every PR (proposal).
- DAST, penetration test, infrastructure checks: not in the PoC (local only, synthetic data).

## 11. PoC Demo Acceptance
- Participant: Product Owner (Customer); our team runs the demo.
- Date: 2027-02-22; no interim demo ([DEC-017](../01-requirements/decision-log.md#dec-017)).
- Script: the demo scenario catalog below. Every scenario starts from a fresh fixture set.
- Defect reporting: findings during the demo are logged in Linear by our team.
- Sign-off: Product Owner ([DEC-011](../01-requirements/decision-log.md#dec-011)), recorded in the minutes of the demo meeting.

### Demo scenario catalog
`DS-NN` IDs are local to this document. Thresholds are the defaults: tolerance 0.5 USD, approval threshold 300 USD.
"Member" = Accounting Member, "Manager" = Accounting Manager.

| ID | Scenario | Steps (summary) | Expected end state | Covers |
|---|---|---|---|---|
| DS-01 | Trade PO invoice, 3-way match, below threshold | Member uploads; all lines match PO and goods receipts; Member confirms | Completed | UC-02, UC-06; DEC-005, DEC-006 |
| DS-02 | Non-trade PO invoice, 2-way match, below threshold | Member uploads; all lines match PO; Member confirms | Completed | UC-02, UC-06; DEC-005, DEC-006 |
| DS-03 | Trade PO invoice above threshold | Upload; match; Manager notified and approves; Member notified and confirms | Completed | UC-04, UC-08; DEC-009, DEC-013, DEC-021 |
| DS-04 | Partial delivery | Second invoice for a PO line; quantity = received-not-invoiced after a second goods receipt | Completed | DEC-007 |
| DS-05 | One invoice, two POs | Lines refer to two different trade POs | Completed | DEC-007 |
| DS-06 | Price within tolerance | Unit price differs from the PO by 0.40 USD | Completed | DEC-006 |
| DS-07 | EX1 unknown file | Member uploads a file that is not in the sample set; Member rejects it | Rejected | EX1; DEC-012, DEC-014 |
| DS-08 | EX2 non-PO invoice above threshold | Non-PO invoice of 450 USD; Member reviews and resolves; Manager approves; Member confirms | Completed | EX2; DEC-006, DEC-013 |
| DS-09 | EX3 invalid PO number | PO number starts with `2`; Member corrects it to a valid PO; matching re-runs | Completed | EX3; DEC-005, DEC-010 |
| DS-10 | EX4 PO not found | Valid format, unknown PO; Member rejects | Rejected | EX4; DEC-014 |
| DS-11 | EX5 trade and non-trade POs on one invoice | Lines refer to a `0…` and a `1…` PO; Member rejects | Rejected | EX5; DEC-007 |
| DS-12 | EX6 price outside tolerance | Unit price differs by 0.60 USD; Member corrects the price; matching re-runs | Completed | EX6; DEC-006, DEC-010 |
| DS-13 | EX7 quantity mismatch | Quantity above received-not-invoiced; Member corrects it; matching re-runs | Completed | EX7; DEC-007, DEC-010 |
| DS-14 | EX8 missing goods receipt | Trade PO without goods receipt; Member rejects | Rejected | EX8; DEC-014 |
| DS-15 | EX9 duplicate invoice | Upload an invoice with the same vendor and invoice number as DS-01; Member rejects | Rejected | EX9; DEC-008 |
| DS-16 | Rejection at approval | Invoice above threshold; Manager rejects with a reason | Rejected | UC-05; DEC-014 |
| DS-17 | Rejection at final review | Matched invoice; Member rejects at final review | Rejected | UC-05; DEC-014 |
| DS-18 | Change matching settings | Manager sets tolerance to 1.00 USD; an invoice with a 0.80 USD difference matches; Member cannot open the settings | Completed | UC-07; DEC-015 |
| DS-19 | Sign-in and role access | Signed-out user is redirected to sign-in; Member cannot approve; Manager can | — | UC-01; NFR-SEC-001 |

Every exception type EX1–EX9 ([DEC-018](../01-requirements/decision-log.md#dec-018)) and every invoice type has at least one scenario.
In each scenario the test also checks the notifications: exceptions and final reviews to Accounting Members, approvals to the Accounting Manager ([DEC-021](../01-requirements/decision-log.md#dec-021)).

## 12. Roles & Responsibilities
| Activity | Dev | SA (incl. QA role) | Product Owner |
|---|---|---|---|
| Unit / integration tests | R | C | — |
| Demo scenarios & E2E tests | C | R, A | I |
| Fixtures (sample set, ERP data) | C | R, A | I |
| Security scans | R | A | — |
| NFR-SCAL-001 review | C | R, A | I |
| Demo acceptance | C | C | R |

R = responsible, A = accountable, C = consulted, I = informed. There is no dedicated QA in the team; the Solution Architect performs the QA role (Q2).

## 13. Risks & Assumptions
| # | Risk / assumption | Mitigation |
|---|---|---|
| 1 | Dummy fixtures do not reflect the shape of real SAP data, so matching may need rework later | Keep fixtures close to the logical model in [data-model.md §4.2](../02-architecture/data-model.md#42-external-entities-read-through-ports-not-stored); review against SAP fields when MuleSoft specs arrive |
| 2 | The demo machine differs from developer machines | Run the last rehearsal on the demo machine with a freshly created stack |
| 3 | Asynchronous processing with Dramatiq and Redis ([ADR-0004](../02-architecture/adr/0004-process-invoices-in-background-worker.md)) makes E2E tests timing-dependent | E2E tests wait for status changes instead of using fixed sleeps |
| 4 | Lost or duplicate messages between PostgreSQL and Redis (ADR-0004 S1–S3) | Integration tests for redelivery, idempotency and the sweeper (§2) |

## 14. Open Questions
| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| Q1 | Minimum code coverage on changed code for the PR gate | Solution Architect (our company) | 2026-12-05 | answered: 90 % (§5) |
| Q2 | Who performs the QA role in the team? | Solution Architect (our company) | 2026-12-05 | answered: no dedicated QA; the Solution Architect tests (§12) |
| Q3 | Is the demo scenario catalog DS-01 … DS-19 complete for "all flows" (DEC-020)? | Product Owner (Customer) | 2026-12-05 | answered: complete → [MTG-20261205](../01-requirements/meetings/2026-12-05-poc-architecture-review.md) R4 |
