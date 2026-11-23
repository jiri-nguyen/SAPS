# CLAUDE.md — Project Documentation Standard

This repository follows the company documentation standard for software development projects
(team of 4–5, cloud: AWS and/or Azure). Copy this file and the `docs/` skeleton into every new
project, then fill in **Project Context**.

## 1. Project Context
<!-- Fill in at project kickoff. Claude: read these values; never guess them. -->
| Key | Value |
|---|---|
| Project name | `Smart-AP-Suite` |
| Project code | `SAPS` (Linear team key) |
| Customer | `TBD` |
| Cloud | `AWS` after the Phase 2 demo (Product Owner's company account, DEC-026, DEC-050); the PoC ran locally, Phase 2 environment TBD (MTG-20270301 Q2) |
| Primary region(s) | `TBD` |
| Work tracker | Linear |
| Work tracker base URL | `https://linear.app/jiringuyen/issue/` (project: `https://linear.app/jiringuyen/project/smart-ap-suite-766faab061af/overview`) |
| Environments | `dev`, `stg`, `prod` |
| Time zone | `Asia/Ho_Chi_Minh (ICT, UTC+7)` |
| Solution Architect | `TBD` |

> **Project note:** this project tracks work in **Linear**. Wherever this standard says "Jira key" or
> "Jira / Azure Boards", read **Linear issue key** (`SAPS-NNN`). File naming is unchanged, e.g. `SAPS-123-invoice-upload.md`.
> Code lives in this repository (public, https://github.com/jiri-nguyen/SAPS). Claude Code is the developer: when writing
> code, follow [docs/04-development/developer-guide.md](docs/04-development/developer-guide.md) (DEC-028, DEC-029).

## 2. Language & Writing Style
- All documents are written in **English** (US spelling). The user may chat in Vietnamese; file content is always English.
- Short sentences, active voice, present tense. Prefer tables and lists over long prose.
- RFC 2119 keywords (MUST / SHOULD / MAY) only in NFRs, ADR decisions and specs.
- Dates `YYYY-MM-DD`; times with zone (`14:00 ICT`). Always state units: `ms`, `req/s`, `GB`, `USD/month`.
- Unknown value → write `TBD` and add it to the doc's **Open Questions** section. Never invent numbers, SLAs, volumes or costs.
- Assumption → `> **Assumption:** …` and record who must confirm it.
- No secrets, credentials, real customer PII or production data in any document.

## 3. Repository Layout
```
CLAUDE.md
docs/
├── _templates/                      # reserved – document templates (added later)
├── 01-requirements/
│   ├── meetings/                    # YYYY-MM-DD-<topic>.md
│   ├── decision-log.md
│   ├── scope.md
│   └── nfr.md
├── 02-architecture/
│   ├── arc42/                       # 01-introduction-and-goals.md … 12-glossary.md
│   ├── adr/                         # NNNN-<title>.md
│   ├── diagrams/
│   │   ├── c4/                      # c4-l1-system-context.drawio.svg …
│   │   ├── infra/                   # infra-<cloud>-<env>.drawio.svg
│   │   └── usecase/                 # uc-<domain>.drawio.svg
│   ├── api/                         # <service>.openapi.yaml, <service>.asyncapi.yaml
│   ├── data-model.md
│   └── cost-estimate.md
├── 03-features/                     # <JIRA-KEY>-<title>.md
├── 04-development/
│   └── developer-guide.md
├── 05-testing/
│   ├── test-strategy.md
│   └── performance/                 # YYYY-MM-DD-psr-<scope>.md
├── 06-release/
│   ├── deployment-guide.md
│   └── release-notes/               # vX.Y.Z.md
└── 07-operations/
    ├── monitoring-alerting.md
    ├── runbook.md
    └── rca/                         # YYYY-MM-DD-<BUG-KEY>-<title>.md
spikes/                              # throwaway spike code: <issue-key>/ with README.md; results go to the ADR
```
Non-diagram images (screenshots, calculator exports) go in an `assets/` folder next to the document
that uses them, named `<doc-slug>-<description>.png`.

## 4. Document Catalog
| # | Document | Path | Item IDs | Owner | Create / update when |
|---|---|---|---|---|---|
| 1 | Meeting Minutes | `01-requirements/meetings/YYYY-MM-DD-<topic>.md` | `MTG-YYYYMMDD[-n]` | SA / PM | After every customer meeting |
| 2 | Decision Log | `01-requirements/decision-log.md` | `DEC-NNN` | SA | A decision is made or confirmed (meeting, email) |
| 3 | Scope Statement | `01-requirements/scope.md` | `SCP-IN-NN`, `SCP-OUT-NN` | PM / BA | Baseline; each approved scope change. Links to backlog epics |
| 4 | NFR Specification | `01-requirements/nfr.md` | `NFR-<CAT>-NNN` | SA | New/changed quality requirement |
| 5 | Architecture Document (arc42) | `02-architecture/arc42/NN-<section>.md` | `§1`…`§12`; `UC-NN`, `CON-NN`, `QS-NN`, `RSK-NN`, `TD-NN` | SA | Continuously; reviewed at each milestone |
| 6 | Architecture Decision Records | `02-architecture/adr/NNNN-<title>.md` | `ADR-NNNN` | SA / Tech Lead | Architecturally significant decision |
| 7 | API Specification | `02-architecture/api/<service>.openapi.yaml` (`.asyncapi.yaml` for events) | `operationId` | Tech Lead | Before implementing an endpoint (contract-first) |
| 8 | Data Model | `02-architecture/data-model.md` | entity names | Tech Lead | Schema change |
| 9 | Cloud Cost Estimate | `02-architecture/cost-estimate.md` | `COST-<env>` | SA | Proposal, infra change, before go-live |
| 10 | Feature Tech Spec | `03-features/<JIRA-KEY>-<title>.md` | Jira key | Assigned dev; SA reviews | Before implementing a non-trivial feature |
| 11 | Developer Guide | `04-development/developer-guide.md` | — | Tech Lead | Setup / conventions / branching change |
| 12 | Test Strategy | `05-testing/test-strategy.md` | — | QA | Project start; test approach change |
| 13 | Performance Test Report (PSR) | `05-testing/performance/YYYY-MM-DD-psr-<scope>.md` | `PSR-YYYYMMDD` | QA + SA | After each performance test campaign |
| 14 | Deployment Guide | `06-release/deployment-guide.md` | — | DevOps / Tech Lead | Pipeline or infra change |
| 15 | Release Notes | `06-release/release-notes/vX.Y.Z.md` | SemVer `vX.Y.Z` | Tech Lead | Every release to stg/prod |
| 16 | Monitoring & Alerting Spec | `07-operations/monitoring-alerting.md` | `SLO-NN`, `ALR-NNN` | SA / DevOps | New service, SLO or alert |
| 17 | Runbook | `07-operations/runbook.md` | `RB-NNN` | DevOps | New alert, incident learning |
| 18 | Root Cause Analysis (RCA) | `07-operations/rca/YYYY-MM-DD-<BUG-KEY>-<title>.md` | `RCA-YYYYMMDD[-n]` | Investigating dev / Tech Lead; SA reviews | A bug or incident meets the RCA criteria below |

**RCA criteria.** Bugs are tracked in Jira / Azure Boards. Write an RCA only when at least one of these is true:
- the bug is a prod incident at SEV1/SEV2, causes data loss or corruption, or is a security issue;
- the root cause is still unclear after a first look, or the bug spans several containers;
- there is more than one viable fix and someone has to choose;
- the customer asks for a formal report.

Otherwise, the root cause and the fix go in the ticket and the PR.

### Templates
Templates live in `docs/_templates/`. Copy the template to the target path, then fill it in.

| Template | Target |
|---|---|
| `meeting-minutes.md` | `01-requirements/meetings/YYYY-MM-DD-<topic>.md` |
| `decision-log.md` | `01-requirements/decision-log.md` |
| `scope.md` | `01-requirements/scope.md` |
| `nfr.md` | `01-requirements/nfr.md` |
| `arc42/NN-<section>.md` (12 files) | `02-architecture/arc42/NN-<section>.md` (same names) |
| `adr.md` | `02-architecture/adr/NNNN-<title>.md` |
| `service.openapi.yaml` | `02-architecture/api/<service>.openapi.yaml` |
| `service.asyncapi.yaml` | `02-architecture/api/<service>.asyncapi.yaml` |
| `data-model.md` | `02-architecture/data-model.md` |
| `cost-estimate.md` | `02-architecture/cost-estimate.md` |
| `feature-spec.md` | `03-features/<JIRA-KEY>-<title>.md` |
| `developer-guide.md` | `04-development/developer-guide.md` |
| `test-strategy.md` | `05-testing/test-strategy.md` |
| `psr.md` | `05-testing/performance/YYYY-MM-DD-psr-<scope>.md` |
| `deployment-guide.md` | `06-release/deployment-guide.md` |
| `release-notes.md` | `06-release/release-notes/vX.Y.Z.md` |
| `monitoring-alerting.md` | `07-operations/monitoring-alerting.md` |
| `runbook.md` | `07-operations/runbook.md` |
| `rca.md` | `07-operations/rca/YYYY-MM-DD-<BUG-KEY>-<title>.md` |

Every document in the catalog has a template.
There are no drawio templates. Use the drawio C4 / AWS / Azure shape libraries and follow §8.

Template markup:
- `{{placeholder}}` marks a value to fill in (not `<…>`, which Markdown can swallow as an HTML tag).
  In YAML front matter, keep placeholder values quoted.
- `<!-- … -->` holds guidance, elicitation checklists and commented-out examples. It is invisible when rendered.
- `<!-- optional -->` marks a section that may be deleted when it does not apply.

### arc42 section files and what they host
| File | Hosts |
|---|---|
| `01-introduction-and-goals.md` | Goals, stakeholders, **use case diagrams**; links to `scope.md` |
| `02-constraints.md` | Technical / organizational / regulatory constraints |
| `03-context-and-scope.md` | **C4 L1 System Context** |
| `04-solution-strategy.md` | Key approaches; links to ADRs |
| `05-building-block-view.md` | **C4 L2 Containers**, **C4 L3 Components** |
| `06-runtime-view.md` | Cross-feature key scenarios (Mermaid sequence); feature-level flows live in `03-features/` |
| `07-deployment-view.md` | **Infra diagrams** per env; env differences; links to `cost-estimate.md` |
| `08-crosscutting-concepts.md` | Security, authN/authZ, logging, error handling, i18n |
| `09-architecture-decisions.md` | **Index table of ADRs only** (no decision content) |
| `10-quality-requirements.md` | Quality tree + scenarios referencing `NFR-*` IDs (no restated values) |
| `11-risks-and-technical-debt.md` | Risk & tech-debt list (`RSK-NN`, `TD-NN`) |
| `12-glossary.md` | **Single source of truth for domain terms and element names** |

## 5. File Naming
- Lowercase **kebab-case**, ASCII only, no spaces: `payment-service.openapi.yaml`.
- Dated documents start with `YYYY-MM-DD-`: `2026-11-14-kickoff.md`.
- Sequenced documents use zero-padded numbers: `0007-use-amazon-sqs.md`, `05-building-block-view.md`.
- Feature specs start with the Jira key in upper case: `APA-123-invoice-approval.md`.
- Title part ≤ 6 words, describes content, no versions in names (git holds history) — except release notes `v1.4.0.md`.
- Diagram files: `<type>-<scope>[-<env>].drawio.svg`
  - C4: `c4-l1-system-context`, `c4-l2-containers`, `c4-l3-<container>-components`
  - Infra: `infra-<aws|azure>-<env>`, optional `infra-<cloud>-network-<env>`
  - Use case: `uc-<domain>`

## 6. Document IDs
- IDs are **permanent**: never renumber, never reuse. Removed items keep their ID with status `withdrawn`.
- Next ID = highest existing + 1 (check the file, not memory).
- arc42 item IDs: `UC-NN` use case (§1), `CON-NN` constraint (§2), `QS-NN` quality scenario (§10),
  `RSK-NN` risk and `TD-NN` technical debt (§11).
- Feature specs use local IDs: `BR-NN` business rule, `EC-NN` edge case, `TS-NN` test scenario. They are unique only
  within one spec, so a reference from another document must name the spec too (`APA-123 BR-02`).
- NFR categories: `PERF` performance, `SCAL` scalability, `AVAIL` availability/DR, `SEC` security, `COMP` compliance,
  `OBS` observability, `MAINT` maintainability, `USAB` usability, `INTOP` interoperability.
- In register-style docs (decision log, NFR, runbook, monitoring, risks) each item heading is the **ID only**,
  so anchors are stable; the title goes on the next line:
  ```markdown
  ### NFR-PERF-001
  **API response time** — p95 ≤ 300 ms at 200 req/s …
  ```

## 7. Front Matter
Every Markdown document starts with YAML front matter:
```yaml
---
title: Non-Functional Requirements
status: draft            # draft | in-review | approved | deprecated
owner: <name>
reviewers: [<name>]
last_updated: YYYY-MM-DD
related: [DEC-004, ADR-0002]
---
```
- ADRs use `status: proposed | accepted | rejected | deprecated | superseded` and `superseded_by: ADR-NNNN` when relevant.
- Customer-facing documents (`scope.md`, `nfr.md`, `cost-estimate.md`, PSR, release notes, RCA) add `version: X.Y`
  (`1.0` = first customer-approved) and a short **Change History** table at the end. Other docs rely on git history.

## 8. Diagram Conventions
### drawio (C4, infra, use case)
- Save as **Editable SVG** (`.drawio.svg`) so the file opens in drawio and renders in Markdown. One diagram per file (no multi-page).
- Every diagram has a **title block** (title, C4 level or environment, last updated) and a **legend**.
- **C4**: drawio C4 shape library and standard colors (Person `#08427B`, Software System `#1168BD`,
  Container `#438DD5`, Component `#85BBF0`, External `#999999`). Each element: name, `[type: technology]`,
  one-line responsibility. Each relationship: verb phrase + protocol, e.g. `Publishes events [AMQP/TLS]`.
- **Infra**: latest official AWS / Azure icon sets from drawio libraries. Show account/subscription, region,
  VPC/VNet, AZ, public/private subnets, security boundaries; label connections with protocol/port.
  One environment per diagram; do not mix AWS and Azure unless the architecture is hybrid.
- **Use case**: UML notation; actors match C4 Persons; use case names are verb + object ("Approve invoice").

### Mermaid (sequence, ERD, state, flowchart)
- Written inline in Markdown inside ```` ```mermaid ```` blocks.
- `sequenceDiagram` uses `autonumber`; participants use C4 container names; show error paths with `alt`/`opt`;
  ≤ 12 participants (split otherwise).
- ERD (`erDiagram`) lives only in `data-model.md`; entity lifecycles use `stateDiagram-v2`.

### Naming consistency
Element names MUST be identical across C4 diagrams, Mermaid participants, API specs, data model and
`12-glossary.md`. The glossary is the source of truth.

### Embedding
`![C4 L2 – Containers](../diagrams/c4/c4-l2-containers.drawio.svg)` — always with alt text.

## 9. Linking & Traceability
- Inside the repo use **relative links** only. Link text starts with the ID:
  `[NFR-PERF-001](../../01-requirements/nfr.md#nfr-perf-001)`, `[ADR-0003](../adr/0003-use-amazon-sqs.md)`.
- Jira/Azure Boards items: full URL from Project Context, text = key: `[APA-123](<base-url>APA-123)`.
- **Single source of truth** — each fact lives in one place; everything else links to it:

  | Fact | Lives in |
  |---|---|
  | Scope in/out | `scope.md` |
  | Quality targets (numbers) | `nfr.md` |
  | Decision rationale | ADR (architectural) or decision log (business/project) |
  | Domain terms, element names | `arc42/12-glossary.md` |
  | API contract | `api/*.yaml` |
  | Schema | `data-model.md` |
  | SLO targets | `monitoring-alerting.md` (derived from and linking to `NFR-*`) |
  | How each NFR is verified | `test-strategy.md` §8 (one row per NFR) |

  Exception: a PSR copies the NFR targets it tested as a snapshot and states which `nfr.md` version they came from.

- **Mandatory links** per document type:

  | Document | Must link to |
  |---|---|
  | `DEC-*` | Source `MTG-*` (or email reference) |
  | `NFR-*`, `SCP-*` | Source `MTG-*` / `DEC-*` |
  | ADR | Driving `DEC-*` / `NFR-*`; superseded/superseding ADR |
  | Feature spec | Jira key, related ADRs, API `operationId`s, affected NFRs |
  | Cost estimate | Infra diagrams, availability NFRs that drive sizing |
  | PSR | Each `NFR-PERF/SCAL-*` tested, with pass/fail; test strategy |
  | `ALR-*` | Its `SLO-*` and `RB-*` |
  | `RB-*` | Alerts that trigger it |
  | RCA | Bug/incident ticket, triggering `ALR-*`, ADR or feature spec for the fix, ticket per preventive action |
  | Release notes | Jira keys, feature specs, new/changed ADRs, API changes |

- Traceability chain: `MTG → DEC → SCP/NFR/ADR → arc42 → Feature spec (Jira) → Test strategy/PSR → Release notes`,
  and `NFR → SLO → ALR ↔ RB`.

## 10. Workflows for Claude
**A. Process meeting input** (notes, transcript, email)
1. Create `meetings/YYYY-MM-DD-<topic>.md` from `_templates/meeting-minutes.md`. Fill **Follow-up from Previous Meetings**
   with every action item and open question that is still open in earlier meeting files.
2. List every new or changed piece of requirement information in **Requirements Captured** with a proposed target.
   Then **propose** (do not apply until the SA confirms) new `DEC-*`, `SCP-*` and `NFR-*` items and any ADR needs.
   Once they are applied, set the row status to `logged` and link the new ID.
3. Flag conflicts with existing decisions/NFRs/scope explicitly.
4. Draft a short English confirmation email summarizing decisions and open questions for the customer.

**B. New ADR**: next number; `status: proposed`; context → options (≥ 2) → decision → consequences;
add a row to `arc42/09-architecture-decisions.md`.

**C. Feature tech spec**: start from `_templates/feature-spec.md` and the Jira key; reuse glossary/C4 names; Mermaid sequence for the main and
error flows; list API and data model changes; link NFRs and ADRs.

**D. Consistency check** (when asked to "review docs"): report broken relative links, referenced-but-undefined IDs,
names not in the glossary, NFRs without test coverage, alerts without runbook entries, ADRs missing from the §9 index.

**E. Release notes**: start from `_templates/release-notes.md`; build from Jira keys and changes the user provides, sorted into the template's sections.
Never omit Breaking Changes or Known Issues; write "None." when empty.

## 11. Rules
- Start every new document from its template in `docs/_templates/` when one exists. Never edit a template while filling in a document.
- Before a document moves to `in-review`, remove all guidance comments and every `{{placeholder}}`. Optional sections that do not apply may be deleted.
- Never invent requirements, numbers or customer statements; use `TBD` + open question.
- Never renumber or reuse IDs.
- Accepted ADRs are immutable — only `status`/`superseded_by` may change; write a new ADR to change a decision.
- Approved customer-facing documents change only via a new `version` + Change History entry; scope changes
  are recorded as a `DEC-*` tagged `[CR]`.
- Do not duplicate content across documents — link to the source of truth.
- Claude MAY create a **new** `.drawio.svg` diagram: write the drawio XML, export it with the drawio CLI
  (`draw.io -x -f svg -e -b 10 -o <name>.drawio.svg <name>.drawio`), render a PNG and check it before handing over.
  The SA reviews every new diagram.
- Claude MUST NOT edit an **existing** `.drawio.svg` file (the SA may have changed it by hand). When a diagram
  must change, give the SA a checklist of elements/relationships to add/change/remove, or a Mermaid draft to redraw from.
- Cost estimates always state region, pricing date, currency (USD), pricing model (on-demand / reserved / savings plan),
  assumptions, and the AWS/Azure Pricing Calculator share link.
- After creating or renaming a document, update every link to it.
