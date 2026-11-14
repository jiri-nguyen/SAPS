---
title: Cloud Cost Estimate
version: "0.1"           # 1.0 = first customer-approved version
status: draft            # draft | in-review | approved | deprecated
owner: "{{Solution Architect}}"
reviewers: ["{{Tech Lead}}", "{{PM}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: Cloud Cost Estimate (customer-facing)
Copy to: docs/02-architecture/cost-estimate.md   (one file per project)
Rules:
- Sizing MUST match arc42 §7 Deployment View; workload numbers come from the NFR Workload Profile.
- Every estimate states region, pricing date, currency (USD), pricing model and the calculator share link.
- Never invent prices: take them from the AWS Pricing Calculator / Azure Pricing Calculator.
- Round monthly figures to whole USD. Totals = sum of rows (re-check after every change).
- One "### COST-<ENV>" block per environment → anchors #cost-prod, #cost-stg, #cost-dev.
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# Cloud Cost Estimate

## 1. Summary
| Environment | Monthly (USD) | Annual (USD) | Pricing model | Details |
|---|---:|---:|---|---|
| prod | {{0}} | {{0}} | {{on-demand / 1-yr savings plan / reserved}} | [COST-PROD](#cost-prod) |
| stg | {{0}} | {{0}} | {{pricing model}} | [COST-STG](#cost-stg) |
| dev | {{0}} | {{0}} | {{pricing model}} | [COST-DEV](#cost-dev) |
| **Total** | **{{0}}** | **{{0}}** | | |

## 2. Basis of Estimate
| Item | Value |
|---|---|
| Cloud provider | {{AWS / Azure}} |
| Region(s) | {{e.g. ap-southeast-1 (Singapore) / Southeast Asia}} |
| Pricing date | YYYY-MM-DD |
| Currency | USD, excluding VAT |
| Pricing model | {{on-demand unless stated per row}} |
| Calculator links | prod: {{share URL}} · stg: {{share URL}} · dev: {{share URL}} |
| Workload basis | [NFR Workload Profile](../01-requirements/nfr.md#2-workload-profile) |
| Sizing basis | [arc42 §7 Deployment View](arc42/07-deployment-view.md) |

## 3. Assumptions
<!-- Everything the numbers depend on: data volumes, request counts, storage growth, log volume,
     data transfer out, operating hours of non-prod, number of environments. -->
| # | Assumption | Source |
|---|---|---|
| CA1 | {{assumption}} | {{NFR / MTG / DEC link, or "estimate"}} |

## 4. Cost Breakdown
<!-- Group rows by container or by category (Compute, Database, Storage, Networking, Security, Observability).
     Example row:
| Compute | Invoice API | ECS Fargate | 2 tasks × 1 vCPU / 2 GB, 730 h | 72 | |
-->

### COST-PROD
| Category | Container / purpose | Service | Configuration & usage | Monthly (USD) | Notes |
|---|---|---|---|---:|---|
| {{Compute}} | {{container}} | {{service}} | {{size × quantity × hours / requests / GB}} | {{0}} | {{note}} |
| **Subtotal** | | | | **{{0}}** | |

### COST-STG
| Category | Container / purpose | Service | Configuration & usage | Monthly (USD) | Notes |
|---|---|---|---|---:|---|
| {{category}} | {{container}} | {{service}} | {{configuration}} | {{0}} | {{note}} |
| **Subtotal** | | | | **{{0}}** | |

### COST-DEV
| Category | Container / purpose | Service | Configuration & usage | Monthly (USD) | Notes |
|---|---|---|---|---:|---|
| {{category}} | {{container}} | {{service}} | {{configuration}} | {{0}} | {{note}} |
| **Subtotal** | | | | **{{0}}** | |

## 5. Not Included
<!-- Make exclusions explicit so the customer is not surprised. Delete lines that are included above. -->
- Cloud support plan ({{AWS Business / Azure Standard}} support)
- Third-party licenses and SaaS subscriptions ({{list}})
- Data transfer above {{n GB/month}}
- Taxes, currency conversion, marketplace fees
- Operations and support labor

## 6. Cost Scaling
<!-- optional — how cost changes with volume, e.g. "+ ~USD 40/month per additional 10,000 invoices/month". -->
| Driver | Unit | Cost per unit (USD/month) | Notes |
|---|---|---:|---|
| {{e.g. invoices processed}} | {{per 10,000/month}} | {{0}} | {{which services scale}} |

## 7. Optimization Options
<!-- Savings the customer can choose, with trade-offs. Saving = estimated USD/month vs. this estimate. -->
| Option | Est. saving (USD/month) | Trade-off |
|---|---:|---|
| {{e.g. 1-year Compute Savings Plan for prod}} | {{0}} | {{1-year commitment}} |
| {{e.g. stop dev/stg outside business hours}} | {{0}} | {{not available at night / weekends}} |

## 8. Open Questions
| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| Q1 | {{question}} | {{name}} | YYYY-MM-DD | {{open}} |

## 9. Approval
| Name | Role | Organization | Date | Reference |
|---|---|---|---|---|
| {{name}} | {{role}} | {{organization}} | YYYY-MM-DD | {{email / signed document link}} |

## 10. Change History
| Version | Date | Author | Change | Decision |
|---|---|---|---|---|
| 0.1 | YYYY-MM-DD | {{name}} | Initial estimate | — |
