---
title: "§2 Architecture Constraints"
status: draft            # draft | in-review | approved | deprecated
owner: "{{Solution Architect}}"
reviewers: ["{{Tech Lead}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: arc42 §2 Architecture Constraints
Copy to: docs/02-architecture/arc42/02-constraints.md
Purpose: requirements that limit design freedom and are NOT negotiable by the team
(mandated technology, cloud, budget, deadlines, regulations, company standards).
This file is the single source of truth for constraints; scope.md and ADRs link here.
IDs: CON-NN, sequential across all subsections, never reused. Every constraint has a Source.
Example row:
| CON-01 | Runs on the customer's existing AWS organization (ap-southeast-1) | All services must be AWS; no Azure | [MTG-20261107](../../01-requirements/meetings/2026-11-07-kickoff.md) R2 |
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# §2 Architecture Constraints

## 2.1 Technical Constraints
<!-- Cloud provider/region, mandated languages/frameworks/databases, existing systems to reuse, licensing. -->
| ID | Constraint | Impact on the architecture | Source |
|---|---|---|---|
| CON-01 | {{constraint}} | {{what it rules in / out}} | {{[MTG-YYYYMMDD](../../01-requirements/meetings/YYYY-MM-DD-topic.md) / [DEC-NNN](../../01-requirements/decision-log.md#dec-nnn)}} |

## 2.2 Organizational Constraints
<!-- Team size and skills, timeline and milestones, budget, who operates the system, procurement rules. -->
| ID | Constraint | Impact on the architecture | Source |
|---|---|---|---|
| CON-NN | {{constraint}} | {{impact}} | {{source}} |

## 2.3 Regulatory & Legal Constraints
<!-- Laws and regulations that constrain design (data residency, Decree 13/2023, e-invoice rules …).
     Measurable compliance targets go to nfr.md (COMP); this section states the constraint itself. -->
| ID | Constraint | Impact on the architecture | Source |
|---|---|---|---|
| CON-NN | {{constraint}} | {{impact}} | {{source}} |

## 2.4 Conventions
<!-- Company or customer standards the team must follow: coding standards, API guidelines, naming,
     tagging policy, documentation standard (this kit). -->
| ID | Convention | Reference |
|---|---|---|
| CON-NN | {{convention}} | {{link}} |
