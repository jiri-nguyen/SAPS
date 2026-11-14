---
title: "§3 Context and Scope"
status: draft            # draft | in-review | approved | deprecated
owner: "{{Solution Architect}}"
reviewers: ["{{Tech Lead}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: arc42 §3 Context and Scope
Copy to: docs/02-architecture/arc42/03-context-and-scope.md
Purpose: the system as a black box — who uses it and which external systems it talks to.
Diagram: C4 Level 1 System Context (drawio). Every person/system on the diagram appears in the tables below,
with exactly the same name as in the glossary (§12).
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# §3 Context and Scope

## 3.1 Business Context
![C4 L1 – System Context](../diagrams/c4/c4-l1-system-context.drawio.svg)

<!-- Type: Person | External system. Owner: who runs the external system (customer IT, vendor …).
     Example row:
| ERP | External system | Approved invoices, vendor master updates | Vendor master, PO data | Customer IT |
-->
| Partner | Type | Receives from our system | Sends to our system | Owner |
|---|---|---|---|---|
| {{name}} | {{Person / External system}} | {{business data}} | {{business data}} | {{owner}} |

## 3.2 Technical Context
<!-- One row per technical interface. Direction from our system's point of view: In | Out | Both.
     Auth: OAuth2 client credentials, API key, mTLS, SFTP key …  Volume: e.g. "≈1,000 calls/day, peak 50/min".
     Spec: link to api/*.yaml for our APIs, or the vendor's documentation. -->
| Interface | Partner | Direction | Protocol / format | Auth | Frequency / volume | Spec |
|---|---|---|---|---|---|---|
| {{interface name}} | {{partner}} | {{In / Out / Both}} | {{HTTPS REST JSON / SFTP CSV / AMQP …}} | {{auth}} | {{volume}} | {{[spec](../api/service.openapi.yaml) / vendor link}} |

## 3.3 Out of Context
<!-- optional — systems or responsibilities deliberately NOT handled by this system (link SCP-OUT-NN). -->
- {{item}} — see [SCP-OUT-NN](../../01-requirements/scope.md)
