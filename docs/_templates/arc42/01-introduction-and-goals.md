---
title: "§1 Introduction and Goals"
status: draft            # draft | in-review | approved | deprecated
owner: "{{Solution Architect}}"
reviewers: ["{{Tech Lead}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: arc42 §1 Introduction and Goals
Copy to: docs/02-architecture/arc42/01-introduction-and-goals.md
Purpose: what the system is for, the top quality goals, and who cares about the architecture.
Do NOT restate scope items or NFR targets — link scope.md and nfr.md.
IDs: UC-NN for use cases (permanent, never reused).
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# §1 Introduction and Goals

## 1.1 Requirements Overview
<!-- 3–5 sentences: what the system does and for whom. Scope boundary lives in scope.md. -->
{{short description of the system and its purpose}}

Scope: see [Scope Statement](../../01-requirements/scope.md).

### Use Cases
<!-- One drawio use case diagram per domain. Actors MUST match C4 Persons and the glossary. -->
![Use cases – {{domain}}](../diagrams/usecase/uc-{{domain}}.drawio.svg)

<!-- Use case names: verb + object ("Approve invoice"). Scope item = the SCP-IN-NN it belongs to. -->
| ID | Use case | Primary actor | Scope item | Backlog |
|---|---|---|---|---|
| UC-01 | {{Verb object}} | {{actor}} | {{SCP-IN-NN}} | {{[KEY-NN](url) / TBD}} |

## 1.2 Quality Goals
<!-- The 3–5 most important quality goals, highest priority first. Each links to the NFRs that make it measurable.
     Example row:
| 1 | Reliability | Month-end close must not be blocked by invoice processing failures | [NFR-AVAIL-001](../../01-requirements/nfr.md#nfr-avail-001) |
-->
| Priority | Quality goal | Motivation | NFRs |
|---|---|---|---|
| 1 | {{quality characteristic}} | {{why it matters to the business}} | {{[NFR-CAT-NNN](../../01-requirements/nfr.md#nfr-cat-nnn)}} |

## 1.3 Stakeholders
<!-- People who influence or are affected by the architecture (customer and our side). -->
| Role | Name / organization | Expectations from the architecture |
|---|---|---|
| {{e.g. Finance Director (sponsor)}} | {{name (organization)}} | {{expectation}} |
