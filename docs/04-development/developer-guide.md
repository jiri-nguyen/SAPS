---
title: Developer Guide
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect / Tech Lead (our company)"
reviewers: []
last_updated: 2027-03-01
related: [DEC-028, DEC-029, DEC-030, ADR-0001, ADR-0008, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006, ADR-0007, ADR-0011, SAPS-26, SAPS-44]
---

# Developer Guide

> **Status of this guide:** the repository skeleton ([SAPS-26](https://linear.app/jiringuyen/issue/SAPS-26)) exists;
> the commands in §2 and §7 are verified on macOS. Steps that need later features are marked with their Linear issue.

## 1. Overview
Smart-AP-Suite automates the Accounts Payable flow: upload, (dummy) extraction, matching, exception handling, approval
and final review. The PoC runs locally with Docker Compose: SAPS Web App (React), SAPS API (FastAPI), SAPS Worker
(Dramatiq), SAPS Message Broker (Redis), SAPS File Storage (SeaweedFS) and SAPS Database (PostgreSQL).
Code and this documentation live in **one public GitHub repository**, [jiri-nguyen/SAPS](https://github.com/jiri-nguyen/SAPS) ([DEC-028](../01-requirements/decision-log.md#dec-028)).
SAPS API and SAPS Worker share one Python package. Code is written by Claude Code and reviewed by the Solution Architect / Tech Lead ([DEC-029](../01-requirements/decision-log.md#dec-029)).

- Containers and responsibilities: [arc42 §5 Building Block View](../02-architecture/arc42/05-building-block-view.md)
- Key decisions: [arc42 §9 Architecture Decisions](../02-architecture/arc42/09-architecture-decisions.md) (arc42 §4 Solution Strategy is not written yet)
- Runtime flows: [arc42 §6 Runtime View](../02-architecture/arc42/06-runtime-view.md)
- Data model: [data-model.md](../02-architecture/data-model.md)
- Domain terms and element names: [Glossary](../02-architecture/arc42/12-glossary.md)
- Scope and demo scenarios: [Scope](../01-requirements/scope.md), [Test Strategy §11](../05-testing/test-strategy.md#11-poc-demo-acceptance)

## 2. Getting Started

### 2.1 Prerequisites
OS: macOS (Apple silicon or Intel) or Linux; Windows via WSL 2.

| Tool | Version | Install | Notes |
|---|---|---|---|
| Git | ≥ 2.40 | https://git-scm.com | GitHub account with access to the repository |
| Docker engine with Compose v2 | Docker 27+ / Compose 2.30+ | Docker Desktop or OrbStack (macOS) | Runs all 6 containers |
| Python | 3.14 | via `uv` | Pinned in `backend/.python-version` |
| uv | ≥ 0.9 | https://docs.astral.sh/uv/ | Python packages and virtual env |
| Node.js | 24 LTS | via a version manager (fnm / nvm) | Pinned in `frontend/.nvmrc` |
| npm | bundled with Node.js | — | |
| TypeScript | 5.9 (pinned) | via npm | TypeScript 7 is not yet supported by `openapi-typescript`; revisit with Dependabot |
| IDE | VS Code or PyCharm | — | Recommended extensions in `.vscode/extensions.json` |

Library versions are locked in `backend/uv.lock` and `frontend/package-lock.json`. Versions verified in the spike:
dramatiq 2.2.1, SQLAlchemy 2.1.8, psycopg 3.3.9, APScheduler 3.11.3, Redis 7.2, SeaweedFS 4.53, PostgreSQL 17
([spikes/saps-34](../../spikes/saps-34/README.md); the spike ran on Python 3.13). On Python 3.14.2 the same libraries plus
FastAPI 0.163.1, Pydantic 2.14.3, Alembic 1.20.1 and testcontainers 4.15.0 install and import without errors (checked 2026-12-05).

### 2.2 Access
| Access | Request from | How |
|---|---|---|
| Source repository [jiri-nguyen/SAPS](https://github.com/jiri-nguyen/SAPS) (public) | Solution Architect / Tech Lead | GitHub collaborator invitation (write access only for the team) |
| Linear project [Smart-AP-Suite](https://linear.app/jiringuyen/project/smart-ap-suite-766faab061af/overview) | Solution Architect | Invitation to workspace `jiringuyen`, team `SAPS` |
| Cloud accounts | — | Not needed in the PoC (local only, [CON-01](../02-architecture/arc42/02-constraints.md)) |
| Secrets | — | None in the PoC; all local values are test values in `.env.example` |

### 2.3 Set Up and Run Locally
```bash
# 1. Clone
git clone https://github.com/jiri-nguyen/SAPS.git
cd SAPS

# 2. Configuration (local test values only)
cp .env.example .env
#    Then set in .env (`docker compose` refuses to start without them):
#    - SEED_USER_PASSWORD: a value of your choice, the password of the demo users in Keycloak;
#    - SESSION_ENCRYPTION_KEY: `openssl rand -base64 32 | tr '+/' '-_'` (encrypts the stored Keycloak tokens, SAPS-44).

# 3. Build and start all containers (Keycloak included, SAPS-43); the SAPS API runs Alembic migrations, then the seed, on start.
#    --wait returns when every container is healthy; Keycloak needs about a minute on the first start.
docker compose up -d --build --wait

# 4. Optional: install the git hooks (gitleaks, ruff, eslint/prettier)
uvx pre-commit install
```

For development with hot reload, run only the dependencies in Docker and the apps locally:
```bash
docker compose up -d db redis seaweedfs keycloak
cd backend && uv sync && uv run alembic upgrade head && uv run python -m saps.seed   # demo companies and users
uv run fastapi dev src/saps/api/main.py                      # SAPS API on :8000 (OIDC_* defaults: Keycloak on :8080;
                                                             #   set OIDC_CLIENT_SECRET to KEYCLOAK_CLIENT_SECRET)
uv run dramatiq saps.worker.actors --processes 1 --threads 4   # SAPS Worker (second terminal)
cd ../frontend && npm ci && npm run dev                        # SAPS Web App on :5173, proxies /v1 and /health
```

### 2.4 Verify the Setup
- Demo companies ([SAPS-42](../03-features/SAPS-42-companies-and-demo-data.md)): the seed creates Demo Vietnam,
  Demo Singapore and Demo Malaysia from `backend/fixtures/companies.json`, each with `member1@`, `member2@` and `manager1@`
  its domain (`vn.example.com`, `sg.example.com`, `my.example.com`); their password is the `SEED_USER_PASSWORD` in Keycloak. The header shows the
  company name. A PoC database keeps its data as Demo Vietnam (`member1` … are renamed; `manager2` stays). Every company uses
  the demo ERP catalogue on its own: DS-01 can be completed in each company, and an invoice of one company is never seen in
  another.
- Open `http://localhost:5173` — the sign-in page shows "Smart-AP-Suite", the button "Sign in with your company account" and
  "SAPS API: ok".
- Single Sign-On ([SAPS-44](../03-features/SAPS-44-single-sign-on.md)): click the button; Keycloak shows its sign-in page. Sign in as
  `member1@vn.example.com` (Demo Vietnam) with the `SEED_USER_PASSWORD` from `.env`: the header shows "Accounting Member 1 (Accounting Member)"
  and the menu shows Upload invoices, Exception queue and Review queue. Sign out (this ends the Keycloak session too), then sign in as
  `manager1@vn.example.com`: the menu shows Approval queue and Matching settings. In the Keycloak admin console, remove a user from its
  company group: the next sign-in shows "Your account is not assigned to exactly one company"; an open session ends within 5 minutes
  (the next token refresh). **Users → Sessions → Sign out** ends the SAPS session at once (back-channel logout).
- `curl http://localhost:8000/ready` returns `{"status":"ready","database":true}`.
- SAPS API → SAPS Message Broker → SAPS Worker:
  `docker compose exec api python -c "from saps.worker.actors import ping; ping.send('check')"`, then
  `docker compose logs worker` shows `ping_received` with `correlation_id` `check`.
- `cd backend && uv run pytest` and `cd frontend && npm test` — all tests pass.
- Upload, extraction and matching ([SAPS-17](https://linear.app/jiringuyen/issue/SAPS-17), [SAPS-18](https://linear.app/jiringuyen/issue/SAPS-18), [SAPS-19](https://linear.app/jiringuyen/issue/SAPS-19)):
  as `member1@vn.example.com`, open **Upload invoices** and drop `backend/fixtures/ds-01/invoices/ds-01-trade-po.pdf`; the row shows the
  progress, then Pending review. Then upload `ds-15/invoices/ds-15-duplicate-scan.png` (same vendor and invoice number):
  Exception with EX9 and EX7 ([SAPS-23](https://linear.app/jiringuyen/issue/SAPS-23)).
  `ds-12-price-outside-tolerance.pdf` ends in Exception (EX6); any file outside the sample set,
  e.g. `ds-07/unregistered/ds-07-unknown-invoice.pdf`, ends in Exception (EX1). `docker compose logs worker` shows
  `extraction_completed` and `matching_completed`.
- Exception handling ([SAPS-20](https://linear.app/jiringuyen/issue/SAPS-20)): as `member1@vn.example.com`, upload `ds-12-price-outside-tolerance.pdf`
  and `ds-08-non-po.pdf`, open **Exception queue**, **Claim** DS-12, **Correct data** (unit price `20.00`), **Save**: the page
  shows "Re-matching in progress", then Pending review. Claim DS-08 and **Accept as is**: Pending approval. As `manager1@vn.example.com`, the
  Exception queue is read-only; open a claimed invoice and **Release claim**.
- Approval ([SAPS-22](https://linear.app/jiringuyen/issue/SAPS-22)): as `manager1@vn.example.com`, open **Approval queue** (DS-08 after it was accepted, or
  `ds-03-above-threshold.pdf` uploaded by `member1@vn.example.com`), open the invoice (the accepted EX2 shows who accepted it and when) and
  **Approve** (Pending review, members are notified) or **Reject** with a comment (Rejected, no notification). A member sees that the
  invoice waits for a manager and has no decision buttons.
- Final review ([SAPS-21](https://linear.app/jiringuyen/issue/SAPS-21)): as `member2@vn.example.com`, open **Review queue**, open DS-01 and **Confirm**
  (Completed: ready for posting), or DS-17 and **Reject** with a reason. The whole demo chain: `member1@vn.example.com` uploads DS-03 →
  `manager1@vn.example.com` approves → `member2@vn.example.com` confirms (the review screen shows the approval).
- Matching settings ([SAPS-28](https://linear.app/jiringuyen/issue/SAPS-28), DS-18): as `member1@vn.example.com`, the menu has no **Matching settings**.
  As `manager1@vn.example.com`, open **Matching settings**: it shows 0.50 and 300.00 and who changed them last (`system` at first). Enter a price
  tolerance of `1.00` and **Save settings**: "Saved. The new values apply to the next matching runs." Then, as `member1@vn.example.com`, upload
  `ds-18/invoices/ds-18-settings-tolerance.pdf` (50.80 against the PO price 50.00): Pending review instead of Exception (EX6).
  Invoices processed earlier keep the tolerance they were processed with. A negative value or a tolerance with more than 4
  decimals (threshold: 2) is refused. Set 0.50 again afterwards; uploading DS-18 twice raises EX9.
- Notifications ([SAPS-24](https://linear.app/jiringuyen/issue/SAPS-24)): as `member1@vn.example.com`, upload `ds-12-price-outside-tolerance.pdf`
  and `ds-03-above-threshold.pdf`. Within 15 s the bell in the top bar shows 1 unread (the exception of DS-12). Open the bell: the
  panel lists the notification (unread ones are highlighted); click it to open the invoice and mark it read, or **Mark all as read**.
  As `manager1@vn.example.com`, the bell shows the approval request of DS-03; clicking it opens the approval screen. Members are told about
  exceptions and final reviews, managers about approvals; rejecting and completing an invoice notify nobody.
- Keycloak ([SAPS-43](https://linear.app/jiringuyen/issue/SAPS-43)): open `http://localhost:8080/realms/saps/account` and sign in as
  `member1@sg.example.com` with the `SEED_USER_PASSWORD`. The admin console is `http://localhost:8080/admin` (user and password
  `KEYCLOAK_ADMIN_USERNAME` / `KEYCLOAK_ADMIN_PASSWORD` of `.env`, master realm); realm `saps` has the groups `/companies/vn`,
  `/companies/sg`, `/companies/my`, the roles Accounting Member and Accounting Manager and the 9 demo users of
  `fixtures/companies.json`. Passwords, roles and company groups are changed here, not in the SAPS Database.
- Sweeper ([SAPS-37](https://linear.app/jiringuyen/issue/SAPS-37)): `docker compose stop worker`, upload `ds-17-rejected-at-review.pdf` as
  `member1@vn.example.com` (it stays Uploaded), `docker compose exec redis redis-cli FLUSHALL` (the message is lost), `docker compose start worker`.
  After `SWEEPER_STUCK_AFTER_SECONDS` (60 s by default) the next tick sends it again: the invoice reaches Pending review, its
  history shows `RESEND` by `system`, and `docker compose logs worker` shows `sweeper_resent`.

## 3. Project Structure
```
SAPS/
├── backend/                      # Python package "saps" — SAPS API and SAPS Worker
│   ├── src/saps/
│   │   ├── domain/               # entities, invoice lifecycle, matching rules (no framework imports)
│   │   ├── application/          # use cases: upload, resolve exception, approve, review, settings
│   │   ├── ports/                # Extraction, ERP Data, Job Queue, File Storage ports (typing.Protocol)
│   │   ├── adapters/             # dummy extraction, dummy ERP, Dramatiq queue, S3 storage, SQLAlchemy repositories
│   │   ├── api/                  # FastAPI routers and Pydantic schemas
│   │   ├── worker/               # Dramatiq actors, sweeper (APScheduler)
│   │   └── config.py             # settings from environment (§6)
│   ├── migrations/               # Alembic
│   ├── fixtures/                 # dummy sample set and dummy ERP data, one folder per demo scenario
│   └── tests/{unit,integration,architecture}/
├── frontend/                     # React + TypeScript (Vite) — SAPS Web App
│   ├── src/
│   └── e2e/                      # Playwright tests DS-01 … DS-20
├── docs/                         # this documentation kit
├── spikes/                       # throwaway spike code
├── compose.yaml                  # 6 containers (local PoC)
├── deploy/seaweedfs/s3.json      # local test identity of SAPS File Storage
├── .github/                      # CI workflow (ci.yml) and Dependabot
└── .env.example
```

| Folder | Purpose | Rules |
|---|---|---|
| `domain/` | Business rules: type derivation, matching, tolerance, lifecycle | No imports from `adapters/`, `api/`, `worker/`, FastAPI, SQLAlchemy or Dramatiq ([ADR-0001](../02-architecture/adr/0001-isolate-extraction-and-erp-behind-ports.md)); enforced by `tests/architecture` |
| `application/` | Use cases that combine domain and ports | Depends on `domain/` and `ports/` only |
| `ports/` | Interfaces to the outside world | No implementation code |
| `adapters/` | Implementations of ports | Selected by configuration at startup |
| `api/` | HTTP layer | Thin: validate, call a use case, map the result |
| `worker/` | Background jobs | Actors are idempotent: lock the invoice row, check status first ([ADR-0004](../02-architecture/adr/0004-process-invoices-in-background-worker.md) S2) |
| `fixtures/` | Dummy data for the demo | One folder per demo scenario; files identified by SHA-256 |

## 4. Development Workflow

### 4.1 Branching
- Model: trunk-based development with short-lived branches.
- Main branch: `main` — always runs with `docker compose up`.
- Branch names: `feature|fix|chore/SAPS-<n>-<short-description>`, e.g. `feature/SAPS-19-line-matching`
  (the Linear key links the branch to the issue).
- Tags: `vX.Y.Z` for the demo build (release notes in `docs/06-release/release-notes/`).

### 4.2 Commits
- Format: Conventional Commits with the Linear key: `type(scope): summary [SAPS-<n>]`,
  e.g. `feat(matching): add price tolerance check [SAPS-19]`.
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`.

### 4.3 Pull Requests
- Size: aim for < 400 changed lines; split larger work.
- Description: link the Linear issue and, if any, the feature spec in `docs/03-features/`.
- Author: Claude Code (the only developer, [DEC-029](../01-requirements/decision-log.md#dec-029)). Reviewer: the Solution Architect / Tech Lead reviews and merges every PR.
- Required checks run in GitHub Actions: [Test Strategy §5 Quality Gates](../05-testing/test-strategy.md#5-quality-gates) (coverage ≥ 90 % on changed code).
- Merge: squash merge; delete the branch after merge.

### 4.4 Code Review Checklist
- [ ] Meets the acceptance criteria of the Linear issue and the feature spec
- [ ] Tests added at the right level; affected demo scenario E2E tests still pass
- [ ] Domain code has no framework or adapter imports
- [ ] Async code does not use lazy loading; relationships are loaded explicitly ([ADR-0005](../02-architecture/adr/0005-use-sqlalchemy-and-alembic.md))
- [ ] Queries are scoped by the signed-in user's `tenant_id` ([ADR-0007](../02-architecture/adr/0007-prepare-data-model-for-tenants.md))
- [ ] Worker actors are idempotent and short in cleanup (≤ 1 s after cancellation, ADR-0004 spike findings)
- [ ] No secrets, no personal data in logs
- [ ] API spec, data model and docs updated (§8)
- [ ] Migrations are forward-only

### 4.5 Public Repository Rules
The repository is public ([DEC-028](../01-requirements/decision-log.md#dec-028)); everything committed is visible to anyone.
- Never commit secrets, real credentials, real invoices, real customer or vendor data, or personal data.
- GitHub secret scanning and push protection are on; gitleaks runs as a pre-commit hook.
- Branch protection on `main`: pull request required, all checks green, no force push.
- Documentation in `docs/` is public too; meeting minutes and decisions must not contain confidential customer information.

### 4.6 Working with Claude Code
- Each task is one Linear issue; Claude Code works on one branch and opens one PR per issue.
- Claude Code follows CLAUDE.md and this guide, runs the tests of §7 before opening a PR, and states in the PR which
  demo scenarios were run.
- Non-trivial features start with a feature spec in `docs/03-features/` that the Solution Architect approves before coding.

### 4.7 Definition of Ready / Definition of Done
| Definition of Ready (before work starts) | Definition of Done (before the issue is closed) |
|---|---|
| Acceptance criteria written in the Linear issue | Merged to `main`; all quality gates green |
| Feature spec written for non-trivial features (CLAUDE.md §10 C) | Runs in the full Docker Compose stack |
| Open questions resolved with the Product Owner (meeting on demand, [DEC-027](../01-requirements/decision-log.md#dec-027)) | Affected demo scenarios pass (E2E) |
| Fixtures for the affected demo scenarios defined | Docs updated (§8) |

## 5. Coding Conventions

### 5.1 Style & Tooling

| Language / area | Formatter | Linter / type check | Config |
|---|---|---|---|
| Python | Ruff format | Ruff, mypy (strict for `domain/` and `application/`), import-linter | `backend/pyproject.toml` |
| TypeScript / React | Prettier | ESLint, `tsc --noEmit` | `frontend/package.json`, `frontend/eslint.config.js` |
| All | — | pre-commit hooks incl. gitleaks (secret scan) | `.pre-commit-config.yaml` |

### 5.2 Naming
- Classes, tables, API resources and UI labels use glossary terms ([§12](../02-architecture/arc42/12-glossary.md)):
  `Invoice`, `InvoiceLine`, `InvoiceException`, `Approval`, `MatchingSettings`, … No abbreviations except those in glossary §12.3.
- Exception codes are `EX1` … `EX10` ([DEC-033](../01-requirements/decision-log.md#dec-033)); statuses are the enum values in the data model.

### 5.3 Cross-cutting Rules
arc42 §8 Cross-cutting Concepts is not written yet. Until then:
- Errors: API errors use `application/problem+json` (RFC 9457).
- Logging: structured JSON logs to stdout; include `invoice_id` and `tenant_id`; never log passwords or file contents.
- Security: sign-in through Keycloak only, no passwords in the SAPS Database ([NFR-SEC-001](../01-requirements/nfr.md#nfr-sec-001),
  [SAPS-44](../03-features/SAPS-44-single-sign-on.md)); the SAPS API is the OpenID Connect client and keeps a server-side session in the
  HttpOnly cookie `saps_session` with the Keycloak tokens encrypted; `Origin` check on state-changing requests
  ([ADR-0011](../02-architecture/adr/0011-sign-in-through-keycloak-with-a-server-side-session.md)). Never log tokens.
- Configuration: environment variables only (§6).

### 5.4 APIs & Events
- Contract first: change [saps-api.openapi.yaml](../02-architecture/api/saps-api.openapi.yaml) before or with the implementation;
  run `redocly lint` and `openapi-spec-validator` on it. Feature specs reference its `operationId`s.
- The SAPS Web App uses a TypeScript client generated from that file.
- Messages to the SAPS Worker carry only the `invoice_id` (`process_invoice`, `rematch_invoice`).

### 5.5 Database Changes
- See [Data Model §7](../02-architecture/data-model.md#7-schema-migration-approach) and [ADR-0005](../02-architecture/adr/0005-use-sqlalchemy-and-alembic.md).
- One migration per PR, created with `uv run alembic revision --autogenerate -m "<description>"` and reviewed by hand;
  never edit a merged migration.
- Every new tenant-owned table gets a non-null `tenant_id` ([ADR-0007](../02-architecture/adr/0007-prepare-data-model-for-tenants.md)).

### 5.6 Dependencies
- New libraries need: an OSI-approved license (no AGPL / SSPL in shipped code), active maintenance, a clean
  `pip-audit` / `npm audit` result, and Solution Architect approval for anything that affects architecture.
- Updates: weekly Dependabot PRs (GitHub).

## 6. Configuration & Secrets (Local)
All settings are environment variables, read in `backend/src/saps/config.py`. `.env.example` holds local test values.

| Setting | Purpose | Local value source |
|---|---|---|
| `DATABASE_URL` | SAPS Database connection as the table owner: migrations and seed only (psycopg async) | `.env.example` |
| `APP_DATABASE_URL` | Connection of the SAPS API and worker jobs as `saps_app` (row-level security applies, [SAPS-41](../03-features/SAPS-41-tenant-isolation.md)) | `.env.example` |
| `SYSTEM_DATABASE_URL` | Connection of the sweeper as `saps_system` (bypasses row-level security) | `.env.example` |
| `APP_DB_PASSWORD`, `SYSTEM_DB_PASSWORD` | Passwords the migration sets for `saps_app` and `saps_system`; must match the two URLs above | `.env.example` |
| `REDIS_URL` | SAPS Message Broker | `.env.example` |
| `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | SAPS File Storage (S3 API) | `.env.example` (local test credentials) |
| `DRAMATIQ_HEARTBEAT_TIMEOUT_MS` | Broker heartbeat timeout — default 30000 | `.env.example` |
| `DRAMATIQ_MAINTENANCE_CHANCE` | Broker maintenance frequency out of 1,000,000 — default 100000 = 10 % ([ADR-0004](../02-architecture/adr/0004-process-invoices-in-background-worker.md) S7) | `.env.example` |
| `ACTOR_TIME_LIMIT_MS` | Time limit per job — default 60000 | `.env.example` |
| `SWEEPER_INTERVAL_SECONDS`, `SWEEPER_STUCK_AFTER_SECONDS` | Sweeper tick and stuck age — defaults 10 and 60 | `.env.example` |
| `SWEEPER_MAX_RESENDS` | Re-sends of `process_invoice` per Uploaded invoice before `RESEND_LIMIT` — default 3 | `.env.example` |
| `PROCESS_INVOICE_MAX_RETRIES`, `PROCESS_INVOICE_MIN_BACKOFF_MS`, `PROCESS_INVOICE_MAX_BACKOFF_MS` | Retries and back-off of `process_invoice` before EX1 — defaults 5, 15000 and 300000 | `.env.example` |
| `VITE_NOTIFICATION_POLL_SECONDS` | SAPS Web App polling interval for notifications — default 15 ([SAPS-24](../03-features/SAPS-24-in-app-notifications.md)) | `frontend/.env.example` |
| `MAX_UPLOAD_SIZE_MB` | Maximum invoice file size — default 10 ([SAPS-17](../03-features/SAPS-17-invoice-upload.md)) | `.env.example` |
| `EXTRACTION_ADAPTER`, `ERP_ADAPTER` | Port adapters — `dummy` in the PoC | `.env.example` |
| `FIXTURES_DIR` | Dummy sample set and ERP data | `.env.example` |
| `WEB_APP_ORIGIN` | Allowed `Origin` for state-changing requests (CSRF check) — `http://localhost:5173` locally | `.env.example` |
| `SESSION_IDLE_TIMEOUT_MINUTES`, `SESSION_ABSOLUTE_TIMEOUT_HOURS` | Session timeouts — defaults 30 and 8 ([ADR-0008](../02-architecture/adr/0008-use-session-cookies-for-authentication.md)) | `.env.example` |
| `SESSION_COOKIE_SECURE` | `Secure` flag on the session cookie — `false` only for local HTTP | `.env.example` |
| `KEYCLOAK_PUBLIC_URL` | URL at which the browser reaches Keycloak; the issuer of the tokens — default `http://localhost:8080` | `.env.example` |
| `KEYCLOAK_DB_PASSWORD` | Password of the role `keycloak` (database `keycloak`, created by the `db-init` service) | `.env.example` |
| `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD` | Bootstrap administrator of Keycloak (master realm) | `.env.example` |
| `KEYCLOAK_CLIENT_SECRET` | Secret of the client `saps-web` (replaces the placeholder of the realm file at import); the SAPS API gets it as `OIDC_CLIENT_SECRET` in `compose.yaml` | `.env.example` |
| `SESSION_ENCRYPTION_KEY` | Fernet key that encrypts the stored Keycloak tokens and the sign-in cookie; required by the SAPS API ([SAPS-44](../03-features/SAPS-44-single-sign-on.md)). Changing it ends all sessions | set locally; CI generates a random value |
| `OIDC_DISCOVERY_URL`, `OIDC_ISSUER` | Discovery document as the SAPS API reaches Keycloak, and the issuer in the tokens (the public URL) — set in `compose.yaml` from `KEYCLOAK_PUBLIC_URL` | `compose.yaml` |
| `OIDC_CLIENT_ID`, `OIDC_GROUPS_CLAIM`, `OIDC_ROLES_CLAIM` | Client and claim names — defaults `saps-web`, `groups`, `roles` ([ADR-0010](../02-architecture/adr/0010-use-one-keycloak-realm-with-company-groups.md)) | defaults |
| `SEED_USER_PASSWORD` | Password of the demo users in Keycloak; empty → the demo seed is skipped (log `seed_skipped`) | set locally; CI generates a random value |

- Never commit `.env`; gitleaks runs as a pre-commit hook.

## 7. Testing Locally
Strategy, levels and gates: [Test Strategy](../05-testing/test-strategy.md).

| Level | Command | Notes |
|---|---|---|
| Unit (backend) | `cd backend && uv run pytest tests/unit` | No containers needed |
| Architecture rules | `cd backend && uv run lint-imports` | Domain must not import adapters |
| Integration | `cd backend && uv run pytest tests/integration` | Starts PostgreSQL with Testcontainers (Redis and SeaweedFS when features need them); skipped without Docker |
| Coverage | `cd backend && uv run pytest --cov=saps --cov-report=term-missing` | Gate: ≥ 90 % on changed code |
| Unit (frontend) | `cd frontend && npm test` | Vitest |
| End-to-end | `docker compose up -d --build --wait && cd frontend && npx playwright test` | Demo scenarios DS-01 … DS-20; Playwright is added with the first feature UI |

- Test names: `test_<behavior>_when_<condition>` (Python), `it('<behavior> when <condition>')` (TypeScript).
- Test data: fixtures in `backend/fixtures/<scenario>/`; builders in `backend/tests/builders.py`.

## 8. Documentation Duties
| When you… | Update |
|---|---|
| Build a non-trivial feature | Feature spec in `docs/03-features/` (template `docs/_templates/feature-spec.md`) |
| Change an API | [saps-api.openapi.yaml](../02-architecture/api/saps-api.openapi.yaml) |
| Change the schema | [data-model.md](../02-architecture/data-model.md) |
| Introduce a new domain term or component | [Glossary](../02-architecture/arc42/12-glossary.md) |
| Make an architecturally significant decision | New ADR in `docs/02-architecture/adr/` |
| Change a demo flow | [Test Strategy §11](../05-testing/test-strategy.md#11-poc-demo-acceptance) and the E2E test |

## 9. Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| Port 5432, 6379, 8333 or 8000 already in use | Another local service | Stop it, or change the host port in `compose.yaml` |
| Invoice stays in Uploaded or Matching | SAPS Worker not running, or message lost | `docker compose logs worker`; the sweeper re-sends after `SWEEPER_STUCK_AFTER_SECONDS` (`RESEND` in the invoice history, log `sweeper_resent`); `sweeper_failed` means the tick failed (database or broker down) and the next tick tries again; `RESEND_LIMIT` in the history and `sweeper_gave_up` in the log mean the sweeper stopped after `SWEEPER_MAX_RESENDS` re-sends and the invoice needs an operator; EX1 with "Processing failed after the last retry" means `process_invoice` failed on every retry ([SAPS-38](https://linear.app/jiringuyen/issue/SAPS-38)) |
| A query as `saps_app` returns no rows | No company set on the transaction (row-level security, fail closed) | Run `SELECT set_config('app.tenant_id', '<tenant id>', true);` first in the same transaction, or query as the owner (`DATABASE_URL`) for diagnosis |
| `docker compose` says `Set SEED_USER_PASSWORD in .env` | The demo password is required because Keycloak imports the demo users with it | Set `SEED_USER_PASSWORD` in `.env` |
| Keycloak shows old users or groups after you edited `companies.json` | The realm file is imported only once (existing realms are kept) | Run `make keycloak-realm` in `backend/`, commit the file, and recreate the volume (`docker compose down -v`) or change the realm in the admin console |
| `MissingGreenlet` / lazy-load error | Lazy loading in async SQLAlchemy code | Load relationships explicitly (`selectinload`) |
| Presigned URL returns 403 | Wrong S3 credentials or clock skew | Check `S3_*` settings; restart the stack |
| `docker compose up --wait` takes about 40 s | SAPS File Storage becomes healthy only when SeaweedFS can store files (`/dir/assign`); the SAPS API waits for it | Expected; without the wait the first upload would hang 7–20 s |
| Upload answers 413 / 415 / 400 | File above `MAX_UPLOAD_SIZE_MB`, not PDF / JPEG / PNG by content, or empty | Use a supported file; the type is checked by content, not by name |
| Keycloak says "Invalid username or password" | Wrong password, or the user is locked out for a while after repeated failures (brute-force protection) | Use the `SEED_USER_PASSWORD` that was set when the realm was first imported; unlock the user in the admin console |
| Sign-in page shows "Your account is not assigned to exactly one company" | No company group, two company groups, or the company was not seeded (log `sign_in_refused`, reason `no_company`; `sign_in_conflict` when the e-mail belongs to another account) | Fix the group in Keycloak; check that the seed ran (`seed_skipped` means `SEED_USER_PASSWORD` was empty) |
| Sign-in page shows "Your sign-in took too long…" right after signing in | The tokens are refused: issuer mismatch (`KEYCLOAK_PUBLIC_URL` differs from the URL in the browser), wrong client secret, or clocks differ (log `token_request_refused`) | Open the SAPS Web App at `WEB_APP_ORIGIN` and Keycloak at `KEYCLOAK_PUBLIC_URL`; keep `KEYCLOAK_CLIENT_SECRET` as at the realm import |
| Every request answers 503 "Sign-in service not reachable" | Keycloak is down when a session needs a token refresh (every 5 minutes) | `docker compose ps keycloak`; the sessions are kept and work again when Keycloak is back |
| `docker compose` says `Set SESSION_ENCRYPTION_KEY in .env` | The key is required (SAPS-44) | Generate one: `openssl rand -base64 32 \| tr '+/' '-_'` |
| State-changing request returns 403 "The request origin is not allowed." | `Origin` header missing or different from `WEB_APP_ORIGIN` | Call the SAPS API through the SAPS Web App origin (`http://localhost:5173`); with curl add `-H "Origin: http://localhost:5173"` |

## 10. Command Cheat Sheet
| Task | Command |
|---|---|
| Start / stop the stack | `docker compose up -d --build --wait` / `docker compose down` |
| Reset all demo data | `docker compose down -v && docker compose up -d --build --wait` |
| Run all backend tests | `cd backend && uv run pytest` |
| Create a migration | `cd backend && uv run alembic revision --autogenerate -m "<description>"` |
| Lint and format | `cd backend && uv run ruff format && uv run ruff check --fix && uv run mypy src` / `cd frontend && npm run lint` |
| Regenerate API client | `cd frontend && npm run gen:api` |
| Regenerate the dummy sample set after editing a fixture JSON | `cd backend && make fixtures` (commit JSON, files, manifest and schema) |

## 11. Onboarding Checklist
- [ ] Access granted (§2.2)
- [ ] Local stack running and verified (§2.3–2.4)
- [ ] Read: scope, arc42 §1, §3, §5, §6, data model, glossary, this guide
- [ ] Walkthrough of the architecture with the Solution Architect
- [ ] First small issue merged (Linear label `good-first-issue`)

## 12. Open Questions
| # | Question | Asked to | Due | Status |
|---|---|---|---|---|
| Q1 | Where is the code hosted, and in which repository? | Solution Architect | — | answered: public GitHub repository [jiri-nguyen/SAPS](https://github.com/jiri-nguyen/SAPS), same repository as the docs ([DEC-028](../01-requirements/decision-log.md#dec-028)) |
| Q2 | Who is the Tech Lead, and who are the developers? | Solution Architect | — | answered: the Solution Architect is also Tech Lead; Claude Code is the only developer ([DEC-029](../01-requirements/decision-log.md#dec-029)) |
| Q3 | Confirm the items: project structure (§3), Node.js 24 + npm, tooling (§5.1), API error format, broker and sweeper defaults (§6), dependency license rule (§5.6) | Solution Architect / Tech Lead | — | answered: all confirmed; Python 3.14 |
| Q4 | Which license applies to the public repository? | Solution Architect / Product Owner | — | answered: MIT ([DEC-030](../01-requirements/decision-log.md#dec-030)) |
