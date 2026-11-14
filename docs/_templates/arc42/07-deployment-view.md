---
title: "§7 Deployment View"
status: draft            # draft | in-review | approved | deprecated
owner: "{{Solution Architect}}"
reviewers: ["{{Tech Lead}}", "{{DevOps}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: arc42 §7 Deployment View
Copy to: docs/02-architecture/arc42/07-deployment-view.md
Purpose: where and how containers run on AWS / Azure, per environment.
Diagrams: one drawio infra diagram per environment: diagrams/infra/infra-<aws|azure>-<env>.drawio.svg.
Sizing here must match cost-estimate.md; costs themselves live only in cost-estimate.md.
How to deploy (pipelines, steps) lives in docs/06-release/deployment-guide.md.
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# §7 Deployment View

## 7.1 Infrastructure Overview
| Environment | Cloud | Account / subscription | Region(s) | Purpose |
|---|---|---|---|---|
| dev | {{AWS / Azure}} | {{account ID alias / subscription name}} | {{region}} | {{development, integration}} |
| stg | {{cloud}} | {{account}} | {{region}} | {{UAT, performance tests}} |
| prod | {{cloud}} | {{account}} | {{region}} | {{production}} |

## 7.2 Production
![Infrastructure – prod](../diagrams/infra/infra-{{aws|azure}}-prod.drawio.svg)

<!-- Map every container from §5.1 to the cloud service that runs it.
     HA: e.g. "2 tasks across 2 AZs", "zone-redundant", "single instance".
     Example row:
| Invoice API | ECS Fargate service | 2 tasks × 1 vCPU / 2 GB | Target tracking on CPU 60 %, 2–6 tasks | Multi-AZ (2 AZs) |
-->
| Container | Cloud service | Size / tier | Scaling | High availability |
|---|---|---|---|---|
| {{container}} | {{service}} | {{size}} | {{scaling rule}} | {{HA setup}} |

## 7.3 Environment Differences
<!-- Only what differs between environments. -->
| Aspect | dev | stg | prod |
|---|---|---|---|
| Sizing | {{…}} | {{…}} | {{…}} |
| High availability | {{single AZ}} | {{…}} | {{multi-AZ}} |
| Data | {{synthetic}} | {{masked copy / synthetic}} | {{real}} |
| Access | {{…}} | {{…}} | {{…}} |
| Schedule | {{auto-stop outside business hours}} | {{…}} | {{24×7}} |

## 7.4 Network & Connectivity
<!-- VPC/VNet CIDRs, subnets, ingress (ALB / App Gateway / Front Door, WAF), egress (NAT),
     private endpoints, connectivity to customer on-prem (VPN / Direct Connect / ExpressRoute), DNS. -->
| Item | prod | Non-prod |
|---|---|---|
| VPC / VNet CIDR | {{x.x.x.x/16}} | {{…}} |
| Ingress | {{…}} | {{…}} |
| Egress | {{…}} | {{…}} |
| Private connectivity | {{…}} | {{…}} |
| DNS | {{zone / records}} | {{…}} |

## 7.5 Backup & Disaster Recovery
<!-- How AVAIL NFRs (RPO / RTO) are met: backup frequency, retention, cross-region copy, restore procedure link. -->
| Data store | Backup method | Frequency / retention | Cross-region | Meets |
|---|---|---|---|---|
| {{store}} | {{automated snapshots / PITR}} | {{daily, 35 days}} | {{yes / no}} | {{[NFR-AVAIL-NNN](../../01-requirements/nfr.md#nfr-avail-nnn)}} |

## 7.6 Related
- Cost: [Cloud Cost Estimate](../cost-estimate.md)
- Deployment: [Deployment Guide](../../06-release/deployment-guide.md)
- Infrastructure as Code: {{repo / path}}
