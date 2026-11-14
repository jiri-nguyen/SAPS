---
title: Decision Log
status: draft            # draft | in-review | approved
owner: "{{Solution Architect}}"
reviewers: ["{{PM}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: Decision Log
Copy to: docs/01-requirements/decision-log.md   (one file per project)
What goes here: business, scope, project and process decisions, plus customer agreement on technical choices.
What goes to an ADR instead: the rationale of an architecturally significant decision
  (structure, technology, NFR trade-off). When the customer agrees an ADR, add a DEC entry that links the ADR.
Scope changes: prefix the title with [CR] and link the affected SCP-* items.
IDs: DEC-NNN, sequential, never renumbered or reused. Withdrawn decisions stay with status "withdrawn".
Status: proposed (not yet confirmed by the decision maker) | confirmed | superseded | withdrawn
Category: Business | Scope | Technical | Project | Process
Keep the Index row and the entry in sync (Index = one line per entry, no details).
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# Decision Log

## 1. Index
| ID | Date | Title | Category | Status |
|---|---|---|---|---|
| [DEC-001](#dec-001) | YYYY-MM-DD | {{short title}} | {{category}} | {{status}} |

## 2. Decisions

<!-- Copy this block for each new decision. Newest at the bottom.

Example:
### DEC-004
**[CR] Add vendor self-service portal to phase 1**

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Category | Scope |
| Status | confirmed |
| Decided by | Jane Doe (Customer, Finance Director) |
| Source | [MTG-20261121](meetings/2026-11-21-scope-review.md) D2 |
| Impacts | [SCP-IN-12](scope.md), [APA-45](https://example.atlassian.net/browse/APA-45) |
| Supersedes / Superseded by | — |
-->

### DEC-001
**{{Decision title}}**

| Field | Value |
|---|---|
| Date | YYYY-MM-DD |
| Category | {{Business / Scope / Technical / Project / Process}} |
| Status | {{proposed / confirmed / superseded / withdrawn}} |
| Decided by | {{name (organization, role)}} |
| Source | [MTG-YYYYMMDD](meetings/{{YYYY-MM-DD-topic}}.md) {{D#}} / {{email: subject, date}} |
| Impacts | {{links to SCP-* / NFR-* / ADR-NNNN / Jira keys, or "none"}} |
| Supersedes / Superseded by | {{DEC-NNN / —}} |

**Context:** {{what situation or question required a decision}}

**Decision:** {{what was decided, one or two sentences}}

**Rationale:** {{why; options considered if relevant}}

**Consequences & follow-ups:** {{effects on scope, cost, timeline, design; follow-up actions with owners}}
