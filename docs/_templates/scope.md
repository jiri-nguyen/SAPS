---
title: Scope Statement
version: "0.1"           # 1.0 = first customer-approved version
status: draft            # draft | in-review | approved | deprecated
owner: "{{PM / BA}}"
reviewers: ["{{Solution Architect}}", "{{customer contact}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: Scope Statement (customer-facing)
Copy to: docs/01-requirements/scope.md   (one file per project)
Purpose: the agreed boundary of the project. Detailed user stories and acceptance criteria live in the backlog
(Jira / Azure Boards); this document lists capabilities at epic level and links to the backlog.
IDs: SCP-IN-NN (in scope), SCP-OUT-NN (out of scope). Sequential across all subsections, never reused.
Every item has a Source (MTG-* or DEC-*). After version 1.0, any change needs a DEC-* titled "[CR] …",
a new version number and a Change History row.
Quality targets (performance, availability, security …) are NOT restated here — they live in nfr.md.
Constraints are NOT restated here — they live in arc42 §2.
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# Scope Statement

## 1. Background
<!-- 3–6 sentences: the business problem, who suffers from it, and what the customer wants to change. -->
{{background}}

## 2. Business Objectives
| # | Objective | Success measure |
|---|---|---|
| BO1 | {{objective}} | {{measurable outcome, e.g. "invoice processing time from 5 days to 1 day"}} |

## 3. In Scope
<!-- Priority uses MoSCoW: Must | Should | Could | Won't (this release).
     Backlog epic: Jira / Azure Boards link, or "TBD" until created.
     Example row:
| SCP-IN-01 | Invoice capture | Ingest PDF invoices from a shared mailbox and extract header fields | Must | [APA-10](https://example.atlassian.net/browse/APA-10) | [MTG-20261107](meetings/2026-11-07-kickoff.md) |
-->

### 3.1 Functional Capabilities
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-01 | {{capability}} | {{one-line description}} | {{Must / Should / Could}} | {{[KEY-NN](url) / TBD}} | {{[MTG-YYYYMMDD](meetings/YYYY-MM-DD-topic.md) / [DEC-NNN](decision-log.md#dec-nnn)}} |

### 3.2 Integrations
<!-- External systems this project connects to (ERP, IdP, email, payment …). Details go to arc42 §3 later. -->
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-NN | {{system}} integration | {{direction, purpose}} | {{priority}} | {{epic}} | {{source}} |

### 3.3 Data & Migration
<!-- optional — delete if there is no data migration or initial data load. -->
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-NN | {{data set}} | {{source system, volume, one-off or recurring}} | {{priority}} | {{epic}} | {{source}} |

### 3.4 Infrastructure & Environments
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-NN | {{e.g. dev / stg / prod environments on AWS}} | {{who provisions, who owns the cloud account/subscription}} | {{priority}} | {{epic}} | {{source}} |

### 3.5 Deliverables & Services
<!-- Documents, training, UAT support, hypercare period, knowledge transfer, source code handover … -->
| ID | Item | Description | Priority | Backlog epic | Source |
|---|---|---|---|---|---|
| SCP-IN-NN | {{deliverable / service}} | {{description, duration if a service}} | {{priority}} | {{epic / n/a}} | {{source}} |

### 3.6 Non-Functional Scope
Quality requirements are specified in [Non-Functional Requirements](nfr.md).

## 4. Out of Scope
<!-- Be explicit: everything the customer might assume is included but is not. -->
| ID | Item | Reason / note | Source |
|---|---|---|---|
| SCP-OUT-01 | {{item}} | {{reason, or "candidate for phase 2"}} | {{source}} |

## 5. Assumptions
| # | Assumption | To be confirmed by | Status |
|---|---|---|---|
| AS1 | {{assumption the plan or estimate depends on}} | {{name (organization)}} | {{open / confirmed / invalid}} |

## 6. Constraints
Constraints (technical, organizational, regulatory) are listed in
[arc42 §2 Constraints](../02-architecture/arc42/02-constraints.md).

## 7. Dependencies
<!-- Things the project needs from the customer or third parties: access, accounts, test data, API credentials, SMEs. -->
| # | Dependency | Owner | Needed by | Status |
|---|---|---|---|---|
| DP1 | {{dependency}} | {{name (organization)}} | YYYY-MM-DD | {{open / provided / late}} |

## 8. Acceptance Approach
<!-- How the customer accepts the delivered scope: UAT per release, acceptance criteria per backlog item,
     sign-off owner. Link the test strategy once it exists. -->
- Acceptance is based on {{UAT of each release against the acceptance criteria of the backlog items}}.
- Sign-off by: {{name (organization, role)}}.
- Test approach: see [Test Strategy](../05-testing/test-strategy.md).

## 9. Open Questions
| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| Q1 | {{question}} | {{name (organization)}} | YYYY-MM-DD | {{open / answered → link}} |

## 10. Approval
| Name | Role | Organization | Date | Reference |
|---|---|---|---|---|
| {{name}} | {{role}} | {{organization}} | YYYY-MM-DD | {{email / signed document link}} |

## 11. Change History
| Version | Date | Author | Change | Decision |
|---|---|---|---|---|
| 0.1 | YYYY-MM-DD | {{name}} | Initial draft | — |
