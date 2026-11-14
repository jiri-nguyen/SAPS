---
id: PSR-YYYYMMDD
title: "PSR-YYYYMMDD — Performance Test Report: {{scope}}"
version: "0.1"           # 1.0 = first version shared with the customer
status: draft            # draft | in-review | approved | deprecated
owner: "{{QA Lead}}"
reviewers: ["{{Solution Architect}}", "{{Tech Lead}}"]
last_updated: YYYY-MM-DD
related: []              # e.g. [NFR-PERF-001, NFR-SCAL-001, ADR-0005]
---
<!--
TEMPLATE: Performance Test Report (PSR) (customer-facing)
Copy to: docs/05-testing/performance/YYYY-MM-DD-psr-<scope>.md   (one file per test campaign; date = campaign end)
Rules:
- Report facts measured in this campaign. Never estimate or round in the customer's favor.
- Every NFR-PERF / NFR-SCAL in the campaign's scope gets a row in §1.2 with PASS / FAIL.
- Targets are copied as a snapshot from nfr.md and the nfr.md version is stated (the only allowed copy of NFR values).
- Percentiles are computed over the steady-state window only (exclude ramp-up / ramp-down) — state the window.
- Charts go to an assets/ folder next to this file: assets/psr-YYYYMMDD-<description>.png
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# PSR-YYYYMMDD — Performance Test Report: {{scope}}

## 1. Executive Summary

### 1.1 Overall Result
**{{PASS / PASS WITH ISSUES / FAIL}}** — {{one sentence: what was tested and the main conclusion}}

Key findings:
- {{finding 1}}
- {{finding 2}}

### 1.2 NFR Results
<!-- Target = snapshot from nfr.md at the version below. Result: PASS | FAIL | NOT TESTED (with reason). -->
NFR targets as of [nfr.md](../../01-requirements/nfr.md) version {{X.Y}}.

| NFR | Target | Measured | Run | Result |
|---|---|---|---|---|
| {{[NFR-PERF-001](../../01-requirements/nfr.md#nfr-perf-001)}} | {{p95 ≤ 500 ms at 200 req/s}} | {{p95 = 430 ms at 205 req/s}} | {{R2}} | {{PASS}} |

## 2. Scope & Objectives
- **Objective:** {{e.g. verify go-live readiness for month-end peak}}
- **System under test:** release {{vX.Y.Z}}, build {{commit / image tags}}
- **In scope:** {{transactions / APIs / jobs}}
- **Out of scope:** {{what was not tested and why}}

## 3. Test Environment
<!-- Compare with prod so readers can judge how far results transfer. Impact: none | results conservative | results optimistic. -->
| Component | Test environment | Production (arc42 §7) | Impact of difference |
|---|---|---|---|
| {{container / data store}} | {{size, count}} | {{size, count}} | {{impact}} |

| Item | Value |
|---|---|
| Environment | {{stg}} |
| Data volume loaded | {{n records / GB — vs. Workload Profile}} |
| Load tool & version | {{k6 / JMeter / Azure Load Testing …}} |
| Load generator location | {{region / network path}} |
| Monitoring used | {{CloudWatch / Azure Monitor / APM}} |

## 4. Workload Model
<!-- Derived from the NFR Workload Profile. Mix % of total load; rates at 100 % load. -->
| Scenario | Business transaction | Mix % | Target rate | Think time | Test data |
|---|---|---:|---|---|---|
| {{S1}} | {{e.g. search invoices}} | {{60}} | {{n req/s}} | {{n s}} | {{data set}} |

## 5. Test Runs
| Run | Type | Date | Duration (steady state) | Load | Result |
|---|---|---|---|---|---|
| R1 | {{baseline / load / stress / soak / spike}} | YYYY-MM-DD | {{60 min (10:15–11:15 ICT)}} | {{n VUs / n req/s}} | {{PASS / FAIL / aborted — reason}} |

## 6. Results

### 6.1 Response Times & Throughput
<!-- One table per run that matters (usually the peak load run). Times in ms. -->
**Run {{R2}}**

| Transaction | Requests | Error % | p50 | p95 | p99 | Max | Throughput (req/s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| {{transaction}} | {{n}} | {{0.00}} | {{n}} | {{n}} | {{n}} | {{n}} | {{n}} |

![Response time over time – {{R2}}](assets/psr-YYYYMMDD-{{r2-response-time}}.png)

### 6.2 Resource Utilization
| Component | CPU avg / peak | Memory avg / peak | Other key metric | Scaling events |
|---|---|---|---|---|
| {{container / DB}} | {{n % / n %}} | {{n % / n %}} | {{DB connections, queue depth, IOPS}} | {{e.g. 2 → 5 tasks at 10:32}} |

### 6.3 Errors
<!-- optional — error types observed, counts, cause. -->
| Error | Count | Run | Cause |
|---|---:|---|---|
| {{HTTP 503 / timeout}} | {{n}} | {{R3}} | {{cause}} |

## 7. Findings & Bottlenecks
<!-- Severity: Critical | High | Medium | Low (same definitions as the test strategy). -->
| # | Finding | Severity | Root cause | Recommendation | Owner | Ticket |
|---|---|---|---|---|---|---|
| F1 | {{finding}} | {{severity}} | {{root cause / suspected}} | {{recommendation}} | {{name}} | {{[KEY-NN](url)}} |

## 8. Capacity Assessment
<!-- What the system can handle and how much headroom there is above the expected peak. -->
| Item | Value |
|---|---|
| Max sustainable throughput (errors < {{1}} %, p95 within target) | {{n req/s}} |
| Breaking point (stress run) | {{n req/s — failure mode}} |
| Headroom vs. expected peak | {{n× / n %}} |
| Scaling behavior | {{e.g. linear up to 6 tasks; DB CPU limits beyond}} |

## 9. Deviations & Limitations
- {{e.g. stg DB is one size smaller than prod; results are conservative}}
- {{e.g. third-party ERP was mocked with fixed 200 ms latency}}

## 10. Recommendations & Next Steps
1. {{recommendation, with owner and target date}}

## 11. Appendix
- Scripts: {{repo / path @ commit}}
- Raw results: {{link}}
- Dashboards: {{link}}
- Test strategy: [Test Strategy](../test-strategy.md)

## 12. Approval
| Name | Role | Organization | Date | Reference |
|---|---|---|---|---|
| {{name}} | {{role}} | {{organization}} | YYYY-MM-DD | {{email / signed document link}} |

## 13. Change History
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | YYYY-MM-DD | {{name}} | Initial report |
