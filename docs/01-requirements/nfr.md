---
title: Non-Functional Requirements
version: "0.1"           # 1.0 = first customer-approved version
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Tech Lead (TBD)", "Customer representative (Customer)"]
last_updated: 2026-11-21
related: [MTG-20261121, DEC-003]
---

# Non-Functional Requirements

## 1. Introduction
- This version covers the Proof of Concept (PoC) phase ([DEC-003](decision-log.md#dec-003)).
- Requirement statements use RFC 2119 keywords: **MUST**, **SHOULD**, **MAY**.
- **Priority:** Must (release blocker) · Should (important, can be deferred with agreement) · Could (nice to have).
- **Status:** proposed (not yet agreed) · agreed (confirmed by the customer) · withdrawn.
- **Verification:** Load test (reported in a PSR) · Monitoring (tracked as an SLO) · Security test · Review / inspection · Demo.
- Targets refer to the [Workload Profile](#2-workload-profile) unless a requirement states other conditions.

## 2. Workload Profile
The PoC uses dummy data and runs locally ([DEC-003](decision-log.md#dec-003), [DEC-004](decision-log.md#dec-004)).
Production workload values are not known yet.

| Parameter | Value | Source |
|---|---|---|
| Total named users | TBD | MTG-20261114 Q4 (counts not given) |
| Peak concurrent users | TBD | — |
| Peak request rate | TBD | — |
| Business transactions per day | TBD | MTG-20261114 Q5 |
| Peak periods | TBD | MTG-20261114 Q6 |
| Data volume at go-live | TBD | — |
| Annual data growth | TBD | — |
| Operating hours | TBD | MTG-20261114 Q31 |
| User locations | TBD | MTG-20261114 Q1 |

## 3. Summary
| ID | Title | Priority | Status |
|---|---|---|---|
| [NFR-SEC-001](#nfr-sec-001) | Sign-in with simple user accounts | Must | agreed |
| [NFR-USAB-001](#nfr-usab-001) | English user interface | Must | agreed |

## 4. Requirements

### 4.1 Performance (PERF)
None agreed for the PoC.

### 4.2 Scalability (SCAL)
None agreed for the PoC.

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
None agreed for the PoC.

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
| MTG-20261114 Q5 | Invoices per month, per invoice type | Customer representative (Customer) | after PoC | open |
| MTG-20261114 Q6 | Peak periods | Customer representative (Customer) | after PoC | open |
| MTG-20261114 Q28 | Data residency; cloud AI/OCR services | Customer representative (Customer) | after PoC | deferred |
| MTG-20261114 Q30 | Retention of invoice files and audit trail | Customer representative (Customer) | after PoC | open |
| MTG-20261114 Q31 | Operating hours and availability | Customer representative (Customer) | after PoC | open |
| Q1 | Does the PoC demo need any response-time target (e.g. from upload to matching result)? | Customer representative (Customer) | 2026-11-28 | open |

## 6. Approval
| Name | Role | Organization | Date | Reference |
|---|---|---|---|---|
| TBD | Sign-off owner (MTG-20261114 Q26) | Customer | — | pending |

## 7. Change History
| Version | Date | Author | Change | Decision |
|---|---|---|---|---|
| 0.1 | 2026-11-21 | Solution Architect (our company) | Initial draft for the PoC: NFR-SEC-001, NFR-USAB-001 | [DEC-003](decision-log.md#dec-003) |
