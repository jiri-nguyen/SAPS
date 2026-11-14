---
title: Decision Log
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["PM (TBD)"]
last_updated: 2026-11-14
related: [MTG-20261114]
---

# Decision Log

## 1. Index
| ID | Date | Title | Category | Status |
|---|---|---|---|---|
| [DEC-001](#dec-001) | 2026-11-14 | Project name Smart-AP-Suite, project code SAPS | Project | confirmed |
| [DEC-002](#dec-002) | 2026-11-14 | Track work items in Linear | Process | confirmed |

## 2. Decisions

### DEC-001
**Project name Smart-AP-Suite, project code SAPS**

| Field | Value |
|---|---|
| Date | 2026-11-14 |
| Category | Project |
| Status | confirmed |
| Decided by | Customer representative (Customer); Solution Architect (our company) |
| Source | [MTG-20261114](meetings/2026-11-14-kickoff.md) D1 |
| Impacts | Project Context in `CLAUDE.md`; all document IDs and issue keys |
| Supersedes / Superseded by | — |

**Context:** The project needs a name and a short code for documents and issue keys.

**Decision:** The project is named "Smart-AP-Suite". The project code is `SAPS`.

**Rationale:** The customer gave the name at kickoff. `SAP` was rejected as a code because it clashes with the SAP ERP product name.

**Consequences & follow-ups:** Issue keys and feature spec file names use `SAPS-NNN`.

### DEC-002
**Track work items in Linear**

| Field | Value |
|---|---|
| Date | 2026-11-14 |
| Category | Process |
| Status | confirmed |
| Decided by | Solution Architect (our company) |
| Source | [MTG-20261114](meetings/2026-11-14-kickoff.md) D2 |
| Impacts | Project Context in `CLAUDE.md`; backlog epic links in [scope.md](scope.md) |
| Supersedes / Superseded by | — |

**Context:** The documentation standard assumes Jira or Azure Boards as the work tracker.

**Decision:** This project tracks epics, stories and bugs in Linear. Where the standard says "Jira key", read "Linear issue key".

**Rationale:** Linear is the tracker the team uses.

**Consequences & follow-ups:** The Linear workspace base URL is TBD. The Solution Architect adds it to the Project Context once the Linear team `SAPS` exists.
