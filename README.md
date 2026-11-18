---
title: Smart-AP-Suite
status: draft
owner: "Solution Architect / Tech Lead (our company)"
reviewers: []
last_updated: 2026-12-15
related: [DEC-028, SAPS-26]
---

# Smart-AP-Suite

Proof of Concept of an Accounts Payable automation system: invoice upload, (dummy) extraction, 2-way / 3-way matching,
exception handling, approval and final review. Code and documentation live in this repository.

- Start here: [Developer Guide](docs/04-development/developer-guide.md) — run the local stack with `docker compose up -d --build --wait`.
- Scope and decisions: [Scope](docs/01-requirements/scope.md), [Decision Log](docs/01-requirements/decision-log.md).
- Architecture: [arc42](docs/02-architecture/arc42/), [ADRs](docs/02-architecture/arc42/09-architecture-decisions.md),
  [API contract](docs/02-architecture/api/saps-api.openapi.yaml).
- Documentation standard used in this repository: [CLAUDE.md](CLAUDE.md).

All data in this repository is synthetic. License: [MIT](LICENSE).
