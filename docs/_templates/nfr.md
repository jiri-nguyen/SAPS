---
title: Non-Functional Requirements
version: "0.1"           # 1.0 = first customer-approved version
status: draft            # draft | in-review | approved | deprecated
owner: "{{Solution Architect}}"
reviewers: ["{{Tech Lead}}", "{{customer contact}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: Non-Functional Requirements (customer-facing)
Copy to: docs/01-requirements/nfr.md   (one file per project)
This document is the single source of truth for quality targets. arc42 §10, SLOs (monitoring-alerting.md)
and performance reports (PSR) reference NFR IDs; they never restate the numbers.
IDs: NFR-<CAT>-NNN, numbered per category, never renumbered or reused. Withdrawn items stay with status "withdrawn".
Each requirement MUST be measurable and verifiable. Unknown target → TBD + Open Question. Never guess numbers.
Each category below has an elicitation checklist (comment) — use it to prepare requirements workshops.
Delete categories that do not apply only after confirming with the customer (record as DEC-*).
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# Non-Functional Requirements

## 1. Introduction
- Requirement statements use RFC 2119 keywords: **MUST**, **SHOULD**, **MAY**.
- **Priority:** Must (release blocker) · Should (important, can be deferred with agreement) · Could (nice to have).
- **Status:** proposed (not yet agreed) · agreed (confirmed by the customer) · withdrawn.
- **Verification:** Load test (reported in a PSR) · Monitoring (tracked as an SLO) · Security test · Review / inspection · Demo.
- Targets refer to the [Workload Profile](#2-workload-profile) unless a requirement states other conditions.

## 2. Workload Profile
<!-- Baseline numbers that NFR targets depend on. Get them from the customer; mark estimates as such. -->
| Parameter | Value | Source |
|---|---|---|
| Total named users | {{n / TBD}} | {{MTG / DEC link}} |
| Peak concurrent users | {{n / TBD}} | {{source}} |
| Peak request rate | {{n req/s / TBD}} | {{source}} |
| Business transactions per day | {{n per day, per transaction type / TBD}} | {{source}} |
| Peak periods | {{e.g. last 3 business days of the month, 3× average}} | {{source}} |
| Data volume at go-live | {{n GB / records}} | {{source}} |
| Annual data growth | {{n % or GB/year}} | {{source}} |
| Operating hours | {{24×7 / business hours ICT}} | {{source}} |
| User locations | {{countries / regions}} | {{source}} |

## 3. Summary
| ID | Title | Priority | Status |
|---|---|---|---|
| [NFR-PERF-001](#nfr-perf-001) | {{title}} | {{Must}} | {{proposed}} |

## 4. Requirements
<!-- Item block — copy for each requirement, place it under its category:

#### NFR-<CAT>-NNN
**<Title>**

| Field | Value |
|---|---|
| Requirement | The system MUST … |
| Metric & target | … |
| Conditions | … |
| Priority | Must / Should / Could |
| Verification | Load test (PSR) / Monitoring (SLO) / Security test / Review / Demo |
| Source | [MTG-YYYYMMDD](meetings/…) / [DEC-NNN](decision-log.md#dec-nnn) |
| Status | proposed / agreed / withdrawn |
| Related | ADR-NNNN, SLO-NN, PSR-YYYYMMDD |

Example:
#### NFR-PERF-001
**Invoice search response time**

| Field | Value |
|---|---|
| Requirement | The invoice search API MUST return results within the target latency. |
| Metric & target | p95 ≤ 500 ms, p99 ≤ 1,500 ms |
| Conditions | Peak request rate from Workload Profile; 3 years of invoice data; prod-sized environment |
| Priority | Must |
| Verification | Load test (PSR); Monitoring (SLO-01) |
| Source | [MTG-20261114](meetings/2026-11-14-requirements-workshop.md) R4 |
| Status | agreed |
| Related | ADR-0005 |
-->

### 4.1 Performance (PERF)
<!-- Elicitation checklist:
- Response time targets per key operation (p95 / p99), for UI pages and APIs.
- Throughput at peak (req/s, transactions/hour).
- Batch / background job windows (e.g. "nightly import completes by 06:00 ICT").
- File size limits (upload, export) and their processing time.
- Acceptable degradation during peak periods. -->

#### NFR-PERF-001
**{{Title}}**

| Field | Value |
|---|---|
| Requirement | {{The system MUST …}} |
| Metric & target | {{metric, target value with unit}} |
| Conditions | {{load, data volume, environment}} |
| Priority | {{Must / Should / Could}} |
| Verification | {{Load test (PSR) / Monitoring (SLO) / …}} |
| Source | {{[MTG-YYYYMMDD](meetings/YYYY-MM-DD-topic.md) R#}} |
| Status | {{proposed}} |
| Related | {{ADR / SLO / PSR IDs or —}} |

### 4.2 Scalability (SCAL)
<!-- Elicitation checklist:
- Expected growth of users, transactions, data over 1–3 years.
- Peak multiplier vs. average; seasonal peaks.
- Scale-out expectations (auto-scaling, tenant onboarding).
- Hard limits (max tenants, max records per tenant). -->

### 4.3 Availability & Disaster Recovery (AVAIL)
<!-- Elicitation checklist:
- Uptime target (e.g. 99.5 % / 99.9 % monthly) and measurement window; which components it covers.
- Planned maintenance window and notice period.
- RPO (max data loss) and RTO (max downtime) for a disaster.
- Multi-AZ / multi-region / failover expectations; backup frequency and retention.
- Behavior when an external dependency (ERP, IdP, email) is down. -->

### 4.4 Security (SEC)
<!-- Elicitation checklist:
- Authentication: SSO / IdP (Entra ID, Okta, Cognito …), MFA, session timeout.
- Authorization model: roles, segregation of duties, data-level access.
- Encryption in transit (TLS version) and at rest (KMS / Key Vault, customer-managed keys?).
- Audit logging: which events, retention period, tamper resistance.
- Secrets management, network exposure (public / private only / VPN), WAF.
- Vulnerability management: SAST/DAST, dependency scanning, pen test before go-live.
- Customer security policies or questionnaires to comply with. -->

### 4.5 Compliance & Data Protection (COMP)
<!-- Elicitation checklist:
- Data residency (country / region where data must be stored and processed).
- Personal data: PDPA, Vietnam Decree 13/2023/ND-CP, GDPR — data subjects, consent, deletion requests.
- Data retention and deletion periods per data type (e.g. accounting records).
- Industry or internal standards (ISO 27001, SOC 2, PCI DSS …).
- Audit and evidence requirements. -->

### 4.6 Observability (OBS)
<!-- Elicitation checklist:
- Logging: centralized, structured, retention period, PII masking.
- Metrics and dashboards needed by the customer's operations team.
- Distributed tracing.
- Alerting channels and who receives alerts (customer / our team), support hours.
- Business monitoring (e.g. stuck invoices, failed integrations). -->

### 4.7 Maintainability & Operability (MAINT)
<!-- Elicitation checklist:
- Mandated technology stack, languages, frameworks, cloud services.
- Deployment frequency and zero-downtime deployment expectation.
- Infrastructure as Code, environment parity.
- Code quality gates (test coverage, static analysis).
- Who operates the system after handover; required skills; documentation expectations. -->

### 4.8 Usability & Accessibility (USAB)
<!-- Elicitation checklist:
- Supported browsers and versions; mobile / tablet support.
- Languages and locales (vi-VN, en-US), date / number / currency formats, time zones.
- Accessibility standard (e.g. WCAG 2.1 AA).
- Branding / UI guidelines. -->

### 4.9 Interoperability (INTOP)
<!-- Elicitation checklist:
- Integration protocols and formats (REST, SOAP, SFTP files, events, e-invoice XML …).
- API standards: versioning, backward compatibility period, rate limits.
- Import / export formats (CSV, Excel, PDF).
- Third-party SLAs and rate limits that constrain the design. -->

## 5. Open Questions
| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| Q1 | {{question}} | {{name (organization)}} | YYYY-MM-DD | {{open / answered → NFR ID}} |

## 6. Approval
| Name | Role | Organization | Date | Reference |
|---|---|---|---|---|
| {{name}} | {{role}} | {{organization}} | YYYY-MM-DD | {{email / signed document link}} |

## 7. Change History
| Version | Date | Author | Change | Decision |
|---|---|---|---|---|
| 0.1 | YYYY-MM-DD | {{name}} | Initial draft | — |
