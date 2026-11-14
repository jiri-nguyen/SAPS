---
title: Monitoring & Alerting Specification
status: draft            # draft | in-review | approved | deprecated
owner: "{{Solution Architect / DevOps}}"
reviewers: ["{{Tech Lead}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: Monitoring & Alerting Specification
Copy to: docs/07-operations/monitoring-alerting.md   (one file per project)
Purpose: what is measured, the SLOs, and every alert with its condition, severity, routing and runbook.
Rules:
- SLO-NN derive from NFRs (link them); targets may be stricter than the NFR, never looser.
- Every ALR-NNN links exactly one runbook procedure RB-NNN. No runbook entry → no alert.
- Alert on symptoms users feel (SLO burn, errors, latency) before causes (CPU); avoid alerts nobody acts on.
- Alert definitions live in IaC — this document states intent; link the IaC path.
- Logging rules (format, fields, PII masking) live in arc42 §8.4 — link, don't repeat.
IDs: SLO-NN, ALR-NNN — permanent, never reused. Item headings are the ID only.
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# Monitoring & Alerting Specification

## 1. Overview
| Item | Value |
|---|---|
| Metrics & logs | {{Amazon CloudWatch / Azure Monitor + Log Analytics / Grafana / Datadog}} |
| Tracing | {{AWS X-Ray / Application Insights / OpenTelemetry → …}} |
| Alert routing | {{SNS → email / Teams / Slack / PagerDuty / Opsgenie}} |
| Synthetic monitoring | {{CloudWatch Synthetics / Application Insights availability tests}} |
| Alert definitions (IaC) | {{repo / path}} |
| Support model | {{who receives alerts in and out of business hours: our team / customer IT}} |
| Logging conventions | [arc42 §8.4](../02-architecture/arc42/08-crosscutting-concepts.md#84-logging-monitoring--tracing) |

## 2. Service Level Objectives

| ID | SLO | Target | Window | NFR |
|---|---|---|---|---|
| [SLO-01](#slo-01) | {{title}} | {{99.9 %}} | {{28-day rolling}} | {{[NFR-AVAIL-001](../01-requirements/nfr.md#nfr-avail-001)}} |

<!-- Example:
### SLO-01
**Invoice API availability**

| Field | Value |
|---|---|
| SLI | Ratio of requests to /v1/* with status < 500, measured at the load balancer |
| Target | 99.9 % |
| Window | 28-day rolling |
| Error budget | 0.1 % ≈ 40 min of full outage per 28 days |
| Source NFR | NFR-AVAIL-001 |
| Data source | ALB metrics HTTPCode_Target_5XX_Count / RequestCount |
| Alerts | ALR-001 (fast burn), ALR-002 (slow burn) |
-->

### SLO-01
**{{SLO title}}**

| Field | Value |
|---|---|
| SLI | {{good events / valid events, and where measured}} |
| Target | {{n %}} |
| Window | {{28-day rolling / calendar month}} |
| Error budget | {{100 % − target, expressed in time or requests}} |
| Source NFR | {{[NFR-CAT-NNN](../01-requirements/nfr.md#nfr-cat-nnn)}} |
| Data source | {{metric / query}} |
| Alerts | {{[ALR-NNN](#alr-nnn)}} |

## 3. Dashboards
| Dashboard | Audience | Content | Link |
|---|---|---|---|
| {{Service overview}} | {{on-call engineer}} | {{golden signals per container, SLO status}} | {{link}} |
| {{Business}} | {{customer operations}} | {{e.g. invoices processed / stuck / failed}} | {{link}} |

## 4. Key Metrics
<!-- Golden signals per container (latency, traffic, errors, saturation) + business metrics.
     Type: counter | gauge | histogram. Name custom metrics consistently: <domain>.<entity>.<measure>. -->
| Metric | Container | Type | Unit | Source | Purpose |
|---|---|---|---|---|---|
| {{metric}} | {{container}} | {{type}} | {{ms / count / %}} | {{built-in / custom}} | {{purpose}} |

## 5. Logs
| Log source | Destination | Retention | Notes |
|---|---|---|---|
| {{application logs}} | {{CloudWatch Logs group / Log Analytics workspace}} | {{n days}} | {{PII masked per arc42 §8.4}} |
| {{audit logs}} | {{destination}} | {{per NFR-SEC / NFR-COMP}} | {{immutable storage?}} |

## 6. Alert Severity & Routing
<!-- Align severity names with the incident process in runbook.md §5. -->
| Severity | Definition | Notify | Response time | Hours |
|---|---|---|---|---|
| SEV1 | {{service down or data loss for many users}} | {{on-call phone + Teams channel}} | {{15 min}} | {{24×7 / business hours}} |
| SEV2 | {{major function degraded, SLO fast burn}} | {{on-call + channel}} | {{30 min}} | {{hours}} |
| SEV3 | {{minor degradation, SLO slow burn}} | {{channel / ticket}} | {{next business day}} | {{business hours}} |
| SEV4 | {{informational, capacity trend}} | {{ticket}} | {{planned}} | {{business hours}} |

## 7. Alerts
<!-- Alert name in the monitoring tool: <env>-<container>-<symptom>, e.g. prod-invoice-api-high-5xx. -->

| ID | Alert | Severity | Environment | Runbook |
|---|---|---|---|---|
| [ALR-001](#alr-001) | {{title}} | {{SEV2}} | {{prod}} | {{[RB-001](runbook.md#rb-001)}} |

### ALR-001
**{{Alert title}}**

| Field | Value |
|---|---|
| Name in tool | {{prod-container-symptom}} |
| Description | {{what it means for users}} |
| Condition | {{metric / query, threshold, evaluation window, datapoints, e.g. 5xx ratio > 2 % for 5 of 5 one-minute periods}} |
| Severity | {{SEV1–SEV4}} |
| Environments | {{prod / stg}} |
| Notify | {{routing per §6}} |
| SLO | {{[SLO-NN](#slo-nn) / —}} |
| Runbook | {{[RB-NNN](runbook.md#rb-nnn)}} |
| Definition (IaC) | {{path}} |

## 8. Health Checks & Synthetic Monitoring
| Check | Target | Frequency | From | Alert |
|---|---|---|---|---|
| {{liveness / readiness / synthetic journey}} | {{URL / endpoint}} | {{1 min}} | {{regions}} | {{ALR-NNN}} |

## 9. Open Questions
| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| Q1 | {{question}} | {{name}} | YYYY-MM-DD | {{open}} |
