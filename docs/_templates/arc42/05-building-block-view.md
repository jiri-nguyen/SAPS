---
title: "§5 Building Block View"
status: draft            # draft | in-review | approved | deprecated
owner: "{{Solution Architect}}"
reviewers: ["{{Tech Lead}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: arc42 §5 Building Block View
Copy to: docs/02-architecture/arc42/05-building-block-view.md
Purpose: static decomposition of the system.
- 5.1 = C4 Level 2 (containers): every deployable/runnable unit and every data store.
- 5.2 = C4 Level 3 (components): only for containers complex enough to need it.
Names MUST match the C4 diagrams and the glossary (§12).
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# §5 Building Block View

## 5.1 Level 1 – Containers
![C4 L2 – Containers](../diagrams/c4/c4-l2-containers.drawio.svg)

<!-- Type: Web app | API | Worker | Function | Database | Queue/Topic | Object storage | …
     Repository: code repo link. API: link to the OpenAPI/AsyncAPI file it exposes.
     Example row:
| Invoice API | API | .NET 8 on ECS Fargate | Receives, validates and stores invoices | invoice-service repo | [invoice.openapi.yaml](../api/invoice.openapi.yaml) |
-->
| Container | Type | Technology | Responsibility | Repository | API |
|---|---|---|---|---|---|
| {{name}} | {{type}} | {{technology}} | {{one-line responsibility}} | {{repo link}} | {{spec link / —}} |

## 5.2 Level 2 – Components
<!-- optional — copy one subsection per container that needs component-level detail. -->

### 5.2.1 {{Container name}}
![C4 L3 – {{Container name}} components](../diagrams/c4/c4-l3-{{container}}-components.drawio.svg)

| Component | Responsibility | Depends on |
|---|---|---|
| {{component}} | {{responsibility}} | {{components / containers}} |
