---
title: "§11 Risks and Technical Debt"
status: draft            # draft | in-review | approved | deprecated
owner: "{{Solution Architect}}"
reviewers: ["{{Tech Lead}}", "{{PM}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: arc42 §11 Risks and Technical Debt
Copy to: docs/02-architecture/arc42/11-risks-and-technical-debt.md
Purpose: living register of technical/architecture risks and known technical debt. Review at each milestone.
IDs: RSK-NN and TD-NN, permanent, never reused. Closed items stay with status closed.
Probability / Impact: Low | Medium | High.  Score: L/M/H matrix (H×H = Critical).
Keep the summary rows in sync with the item blocks.
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# §11 Risks and Technical Debt

## 11.1 Risks

| ID | Title | Probability | Impact | Owner | Status |
|---|---|---|---|---|---|
| [RSK-01](#rsk-01) | {{title}} | {{L/M/H}} | {{L/M/H}} | {{name}} | {{open}} |

<!-- Example:
### RSK-03
**ERP vendor API rate limit unknown**

| Field | Value |
|---|---|
| Description | The ERP API rate limit is undocumented; bulk vendor sync may be throttled at go-live. |
| Probability | Medium |
| Impact | High |
| Mitigation | Request limits from vendor (Q4 in MTG-20261114); design sync as queued, resumable batches. |
| Contingency | Run initial sync over a weekend window. |
| Owner | Tech Lead |
| Status | open |
| Source | [MTG-20261114](../../01-requirements/meetings/2026-11-14-integration-workshop.md) |
-->

### RSK-01
**{{Risk title}}**

| Field | Value |
|---|---|
| Description | {{what may happen and why}} |
| Probability | {{Low / Medium / High}} |
| Impact | {{Low / Medium / High}} — {{on what: schedule, cost, quality goal}} |
| Mitigation | {{actions to reduce probability or impact}} |
| Contingency | {{what to do if it happens}} |
| Owner | {{name}} |
| Status | {{open / mitigated / occurred / closed}} |
| Source | {{MTG / DEC / ADR link}} |

## 11.2 Technical Debt

| ID | Title | Impact | Remediation effort | Status |
|---|---|---|---|---|
| [TD-01](#td-01) | {{title}} | {{L/M/H}} | {{S/M/L}} | {{open}} |

### TD-01
**{{Debt title}}**

| Field | Value |
|---|---|
| Description | {{shortcut taken or deficiency}} |
| Cause | {{deadline, missing info, legacy constraint …}} |
| Impact | {{what it costs us if not fixed}} |
| Remediation | {{how to fix}} |
| Effort | {{S / M / L}} |
| Backlog | {{[KEY-NN](url) / TBD}} |
| Status | {{open / scheduled / resolved}} |
