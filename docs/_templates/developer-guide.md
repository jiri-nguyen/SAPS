---
title: Developer Guide
status: draft            # draft | in-review | approved | deprecated
owner: "{{Tech Lead}}"
reviewers: ["{{Solution Architect}}", "{{developer}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: Developer Guide
Copy to: docs/04-development/developer-guide.md   (one file per project)
Audience: a developer joining the project. Goal: running the system locally and opening a first pull request
on day one, without asking the team.
Rules:
- Link instead of repeating: tech stack → arc42 §4, repositories → deployment guide §3,
  quality gates → test strategy §5, error handling / logging / security rules → arc42 §8.
- Commands must be copy-paste ready and tested on a clean machine. State the OS assumptions.
- Use {{placeholders}} for values; NEVER write secrets, tokens or passwords here.
- Per-repo details (exact scripts) may live in each repo's README; this guide links them and holds the project-wide rules.
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# Developer Guide

## 1. Overview
{{one paragraph: what the system does and how the code is organized (mono-repo / one repo per container)}}

- Tech stack and key decisions: [arc42 §4 Solution Strategy](../02-architecture/arc42/04-solution-strategy.md)
- Containers and responsibilities: [arc42 §5 Building Blocks](../02-architecture/arc42/05-building-block-view.md)
- Repositories and artifacts: [Deployment Guide §3](../06-release/deployment-guide.md#3-repositories--artifacts)
- Domain terms: [Glossary](../02-architecture/arc42/12-glossary.md)

## 2. Getting Started

### 2.1 Prerequisites
<!-- Pin versions. Prefer a version manager file in the repo (.nvmrc, .tool-versions, global.json, .python-version). -->
| Tool | Version | Install | Notes |
|---|---|---|---|
| {{Git}} | {{≥ 2.40}} | {{link}} | |
| {{Docker Desktop / Podman}} | {{version}} | {{link}} | {{for local dependencies}} |
| {{runtime: .NET SDK / Node.js / Java / Python}} | {{version}} | {{link}} | {{version file in repo}} |
| {{AWS CLI / Azure CLI}} | {{version}} | {{link}} | {{SSO profile setup in §2.2}} |
| {{IDE + recommended extensions}} | — | — | {{extensions list / .vscode/extensions.json}} |

### 2.2 Access
<!-- What a new developer must request, from whom. -->
| Access | Request from | How |
|---|---|---|
| {{Source repositories}} | {{Tech Lead}} | {{GitHub / Azure Repos team}} |
| {{Work tracker (Jira / Azure Boards)}} | {{PM}} | {{…}} |
| {{Cloud dev account / subscription}} | {{DevOps}} | {{SSO role; CLI profile name: …}} |
| {{Dev secrets}} | {{DevOps}} | {{Secrets Manager / Key Vault path — never shared in chat}} |
| {{Team channels}} | {{PM}} | {{…}} |

### 2.3 Set Up and Run Locally
<!-- Exact commands from clone to a running system. Use local emulators where possible
     (LocalStack, Azurite, Cosmos DB emulator, docker compose for DB / queue). -->
```bash
# 1. Clone
git clone {{repository URL}}
cd {{repo}}

# 2. Local dependencies (database, queue, emulators)
{{docker compose up -d}}

# 3. Configuration
cp .env.example .env    # fill values as described in §6

# 4. Install, migrate, seed
{{install command}}
{{migration command}}
{{seed command}}

# 5. Run
{{run command}}
```

### 2.4 Verify the Setup
- Open `http://localhost:{{port}}` and log in with the seeded test user {{user name}}.
- Run the unit tests with `{{command}}` — all tests pass.

## 3. Project Structure
<!-- One tree per repository (or one for the mono-repo). Show only the folders a newcomer needs to know. -->
```
{{repo}}/
├── src/                 # {{application code}}
├── tests/               # {{unit and integration tests}}
├── infra/               # {{IaC}}
├── docs/                # {{this documentation kit}}
└── {{…}}
```

| Folder | Purpose | Rules |
|---|---|---|
| {{folder}} | {{purpose}} | {{e.g. no references from domain to infrastructure}} |

## 4. Development Workflow

### 4.1 Branching
<!-- Pick one model and describe it: trunk-based (short-lived branches off main) / GitHub flow / GitFlow. -->
- Model: {{trunk-based with short-lived feature branches}}
- Main branch: `main` — always deployable to dev
- Branch names: `{{feature|fix|chore}}/<JIRA-KEY>-<short-description>` — e.g. `feature/APA-123-invoice-approval`
- Release tags: `vX.Y.Z` (see [Deployment Guide §2](../06-release/deployment-guide.md#2-environments--promotion))

### 4.2 Commits
<!-- e.g. Conventional Commits with the Jira key. -->
- Format: `{{type(scope): summary [JIRA-KEY]}}` — e.g. `feat(invoice): add approval endpoint [APA-123]`
- Types: {{feat, fix, refactor, test, docs, chore, ci}}

### 4.3 Pull Requests
- Size: {{aim for < 400 changed lines; split larger work}}
- Description: {{PR template path}} — link the Jira key and the feature spec
- Reviewers: {{at least 1 developer; SA for changes to APIs, data model, infra or security}}
- Required checks: see [Test Strategy §5 Quality Gates](../05-testing/test-strategy.md#5-quality-gates)
- Merge: {{squash merge; delete branch after merge}}

### 4.4 Code Review Checklist
- [ ] Meets the Jira acceptance criteria and the feature spec
- [ ] Tests added or updated at the right level
- [ ] Follows the cross-cutting rules (§5) — errors, logging, security
- [ ] No secrets, no PII in logs
- [ ] API spec, data model and docs updated (see §8)
- [ ] Migrations are backward compatible

### 4.5 Definition of Ready / Definition of Done
| Definition of Ready (before a story enters a sprint) | Definition of Done (before a story is closed) |
|---|---|
| {{Acceptance criteria agreed with the customer / PO}} | {{Code merged to main, all quality gates green}} |
| {{Dependencies and open questions resolved}} | {{Deployed to dev / stg and verified}} |
| {{Feature spec written if required}} | {{Tests written; acceptance criteria verified by QA}} |
| {{Estimated by the team}} | {{Docs updated (§8); release notes entry prepared}} |

## 5. Coding Conventions

### 5.1 Style & Tooling
<!-- Formatter and linter config is the rule; don't describe style in prose. -->
| Language / area | Formatter | Linter | Config |
|---|---|---|---|
| {{C# / TypeScript / Python / Terraform}} | {{dotnet format / Prettier / Black / terraform fmt}} | {{analyzers / ESLint / Ruff / tflint}} | {{path}} |

### 5.2 Naming
<!-- Only project-specific rules beyond the language's standard. Domain names must match the glossary. -->
- {{e.g. classes and API resources use glossary terms; no abbreviations except those in glossary §12.3}}

### 5.3 Cross-cutting Rules
Follow [arc42 §8 Cross-cutting Concepts](../02-architecture/arc42/08-crosscutting-concepts.md):
- Errors and resilience — §8.3
- Logging, metrics, tracing — §8.4
- Security (authN / authZ, secrets) — §8.2
- Configuration — §8.5

### 5.4 APIs & Events
- Contract first: change `docs/02-architecture/api/*.yaml` before or with the implementation.
- {{API conventions: versioning, error format, pagination — as in the OpenAPI spec header comments}}

### 5.5 Database Changes
- See [Data Model §7 Schema Migration Approach](../02-architecture/data-model.md#7-schema-migration-approach).
- {{e.g. one migration per PR, named YYYYMMDDHHMM_description; never edit a merged migration}}

### 5.6 Dependencies
- {{Rules for adding a library: license allow-list, maintenance status, security scan, who approves}}
- {{Update cadence: e.g. Dependabot / Renovate weekly}}

## 6. Configuration & Secrets (Local)
<!-- How local configuration works. Values come from .env.example and the dev secret store. -->
| Setting | Purpose | Local value source |
|---|---|---|
| {{SETTING_NAME}} | {{purpose}} | {{.env.example default / dev secret store path}} |

- Never commit `.env` or any secret; {{pre-commit secret scanning: gitleaks / detect-secrets}}.

## 7. Testing Locally
<!-- How to run each test level locally. Strategy and gates: test-strategy.md. -->
| Level | Command | Notes |
|---|---|---|
| Unit | {{command}} | |
| Integration | {{command}} | {{needs docker compose dependencies}} |
| Contract | {{command}} | |
| End-to-end | {{command}} | {{against local or dev}} |

- Test naming: {{e.g. MethodName_State_ExpectedResult}}
- Test data: {{builders / fixtures location}}

## 8. Documentation Duties
<!-- When developers must update the documentation kit (rules in CLAUDE.md). -->
| When you… | Update |
|---|---|
| Build a non-trivial feature | Feature spec in `docs/03-features/` (template `_templates/feature-spec.md`) |
| Change an API or event | `docs/02-architecture/api/*.yaml` |
| Change the schema | `docs/02-architecture/data-model.md` |
| Introduce a new domain term or component | arc42 §12 Glossary |
| Make an architecturally significant decision | New ADR in `docs/02-architecture/adr/` |
| Add a failure mode that needs an alert | `ALR-*` in monitoring-alerting.md + `RB-*` in runbook.md |

## 9. Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| {{e.g. port 5432 already in use}} | {{local PostgreSQL running}} | {{stop it or change the port in .env}} |

## 10. Command Cheat Sheet
| Task | Command |
|---|---|
| {{Run all tests}} | {{command}} |
| {{Create a migration}} | {{command}} |
| {{Lint and format}} | {{command}} |
| {{Regenerate API client from OpenAPI}} | {{command}} |

## 11. Onboarding Checklist
- [ ] Access granted (§2.2)
- [ ] Local setup running and verified (§2.3–2.4)
- [ ] Read: scope, arc42 §1–§5, glossary, this guide
- [ ] Walkthrough of the architecture with the SA / Tech Lead
- [ ] First small ticket merged: {{starter ticket / label}}
