---
title: Non-Functional Requirements
version: "0.4"           # 1.0 = first customer-approved version
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Tech Lead (TBD)", "Product Owner (Customer)"]
last_updated: 2027-03-01
related: [MTG-20261121, MTG-20261128, MTG-20261205, MTG-20270301, DEC-003, DEC-026, DEC-048, DEC-050, NFR-MAINT-001]
---

# Non-Functional Requirements

## 1. Introduction
- This version covers the Proof of Concept (PoC) phase ([DEC-003](decision-log.md#dec-003)) and the Workload Profile of Phase 2 ([DEC-048](decision-log.md#dec-048)); quality targets for Phase 2 are open ([MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) Q8).
- Requirement statements use RFC 2119 keywords: **MUST**, **SHOULD**, **MAY**.
- **Priority:** Must (release blocker) · Should (important, can be deferred with agreement) · Could (nice to have).
- **Status:** proposed (not yet agreed) · agreed (confirmed by the customer) · withdrawn.
- **Verification:** Load test (reported in a PSR) · Monitoring (tracked as an SLO) · Security test · Review / inspection · Demo.
- Targets refer to the [Workload Profile](#2-workload-profile) unless a requirement states other conditions.

## 2. Workload Profile
The PoC uses dummy data and runs locally ([DEC-003](decision-log.md#dec-003), [DEC-004](decision-log.md#dec-004)).
Volumes below are design information, not PoC acceptance criteria ([MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) R6).

| Parameter | Value | Source |
|---|---|---|
| Total named users | Phase 2: about 30 (Accounting Members and Accounting Managers of about 3 companies) | [MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) R7 |
| Peak concurrent users | TBD | — |
| Peak request rate | TBD | — |
| Business transactions per day | PoC: ≤ 1,000 invoices/day (one company). Phase 2 demo: about 3 companies × 1,000 invoices/day ([MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) R7). Later: 1,000–2,000 invoices/day per company, many companies | [MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) R6 |
| Peak periods | TBD | [MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) Q1 |
| Data volume at go-live | TBD | — |
| Annual data growth | TBD | — |
| Operating hours | Business hours, Singapore time (SGT, UTC+8) | [MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) R9; [MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) R8 |
| User locations | Singapore time zone; locations TBD | MTG-20261114 Q1; [MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) R8 |

## 3. Summary
| ID | Title | Priority | Status |
|---|---|---|---|
| [NFR-SCAL-001](#nfr-scal-001) | Scalable design beyond the PoC | Must | agreed |
| [NFR-MAINT-001](#nfr-maint-001) | Ready for real extraction and AWS | Must | agreed |
| [NFR-SEC-001](#nfr-sec-001) | Sign-in with simple user accounts | Must | agreed |
| [NFR-USAB-001](#nfr-usab-001) | English user interface | Must | agreed |

## 4. Requirements

### 4.1 Performance (PERF)
No performance target for the PoC ([MTG-20261128](meetings/2026-11-28-poc-flow-review.md) R11). See NFR-SCAL-001.

### 4.2 Scalability (SCAL)

#### NFR-SCAL-001
**Scalable design beyond the PoC**

| Field | Value |
|---|---|
| Requirement | The PoC architecture MUST allow higher invoice volumes and more users after the PoC without a redesign of the matching and workflow logic. |
| Metric & target | The design supports the Workload Profile: ≤ 1,000 invoices/day for one company in the PoC, and many companies × 1,000–2,000 invoices/day after the PoC by adding instances, without redesign. No load test in the PoC. |
| Conditions | Design and code of the PoC |
| Priority | Must |
| Verification | Review (architecture review of ADRs and code structure) |
| Source | [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) R11 |
| Status | agreed |
| Related | [ADR-0001](../02-architecture/adr/0001-isolate-extraction-and-erp-behind-ports.md), [ADR-0004](../02-architecture/adr/0004-process-invoices-in-background-worker.md), [ADR-0007](../02-architecture/adr/0007-prepare-data-model-for-tenants.md) |

### 4.3 Availability & Disaster Recovery (AVAIL)
None agreed for the PoC.

### 4.4 Security (SEC)

#### NFR-SEC-001
**Sign-in with simple user accounts**

| Field | Value |
|---|---|
| Requirement | Users MUST sign in with a simple user account managed by the application. Single Sign-On is not required in the PoC. |
| Metric & target | Every function except sign-in requires a signed-in user |
| Conditions | PoC, local environment |
| Priority | Must |
| Verification | Demo |
| Source | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R22 |
| Status | agreed |
| Related | [SCP-IN-12](scope.md), [SCP-OUT-10](scope.md) |

### 4.5 Compliance & Data Protection (COMP)
None agreed for the PoC. Data residency and retention are open (MTG-20261114 Q28, Q30).

### 4.6 Observability (OBS)
None agreed for the PoC.

### 4.7 Maintainability & Operability (MAINT)

#### NFR-MAINT-001
**Ready for real extraction and AWS**

| Field | Value |
|---|---|
| Requirement | The Phase 2 design MUST let a real OCR / AI extraction service and the deployment on AWS be added after the Phase 2 demo without changing the matching and workflow logic. |
| Metric & target | Extraction stays behind the Extraction Port ([ADR-0001](../02-architecture/adr/0001-isolate-extraction-and-erp-behind-ports.md)); file storage, message queue, database, identity provider and mail are reached only through adapters and environment settings; no local-only assumptions in the code |
| Conditions | Every ADR and feature spec of Phase 2 |
| Priority | Must |
| Verification | Review (architecture review of each Phase 2 ADR and feature spec) |
| Source | [MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) R9; [DEC-050](decision-log.md#dec-050) |
| Status | agreed |
| Related | [NFR-SCAL-001](#nfr-scal-001), [DEC-026](decision-log.md#dec-026) |

### 4.8 Usability & Accessibility (USAB)

#### NFR-USAB-001
**English user interface**

| Field | Value |
|---|---|
| Requirement | The user interface MUST be in English. |
| Metric & target | 100 % of UI texts in English |
| Conditions | All screens |
| Priority | Must |
| Verification | Demo |
| Source | [MTG-20261121](meetings/2026-11-21-requirements-workshop.md) R23 |
| Status | agreed |
| Related | — |

### 4.9 Interoperability (INTOP)
None agreed for the PoC. Later ERP integration is a constraint: [CON-03](../02-architecture/arc42/02-constraints.md).

## 5. Open Questions
| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| MTG-20261114 Q5 | Invoices per month, per invoice type | Customer representative (Customer) | — | answered: see Workload Profile ([MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) R6) |
| MTG-20261114 Q6 | Peak periods | Customer representative (Customer) | after PoC | open |
| MTG-20261114 Q28 | Data residency; cloud AI/OCR services | Customer representative (Customer) | after PoC | deferred |
| MTG-20261114 Q30 | Retention of invoice files and audit trail | Customer representative (Customer) | after PoC | open |
| MTG-20261114 Q31 | Operating hours and availability | Customer representative (Customer) | after PoC | partly answered: business hours, assumption ([MTG-20261205](meetings/2026-12-05-poc-architecture-review.md) R9); availability open |
| Q1 | Does the PoC demo need any response-time target (e.g. from upload to matching result)? | Customer representative (Customer) | 2026-11-28 | answered → [MTG-20261128](meetings/2026-11-28-poc-flow-review.md) R11 |

## 6. Approval
| Name | Role | Organization | Date | Reference |
|---|---|---|---|---|
| TBD | Product Owner (sign-off owner) | Customer | — | pending |

## 7. Change History
| Version | Date | Author | Change | Decision |
|---|---|---|---|---|
| 0.1 | 2026-11-21 | Solution Architect (our company) | Initial draft for the PoC: NFR-SEC-001, NFR-USAB-001 | [DEC-003](decision-log.md#dec-003) |
| 0.2 | 2026-11-28 | Solution Architect (our company) | NFR-SCAL-001 added | — ([MTG-20261128](meetings/2026-11-28-poc-flow-review.md) R11) |
| 0.3 | 2026-12-05 | Solution Architect (our company) | Workload Profile filled; NFR-SCAL-001 target set | [DEC-026](decision-log.md#dec-026) |
| 0.4 | 2027-03-01 | Solution Architect (our company) | Workload Profile for Phase 2: users, invoices per day, Singapore time; NFR-MAINT-001 added | [DEC-048](decision-log.md#dec-048) ([MTG-20270301](meetings/2027-03-01-phase-2-kickoff.md) R7, R8) |
