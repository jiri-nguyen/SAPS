---
title: "§9 Architecture Decisions"
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Tech Lead (TBD)"]
last_updated: 2026-11-28
related: [ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005]
---

# §9 Architecture Decisions

| ADR | Title | Status | Date | Supersedes / Superseded by |
|---|---|---|---|---|
| [ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md) | Isolate invoice extraction and ERP data behind ports | accepted | 2026-11-21 | — |
| [ADR-0002](../adr/0002-use-python-fastapi-and-react.md) | Use Python/FastAPI and React for the PoC | accepted | 2026-11-21 | — |
| [ADR-0003](../adr/0003-use-postgresql-and-docker-compose.md) | Use PostgreSQL and Docker Compose for the PoC | accepted | 2026-11-21 | — |
| [ADR-0004](../adr/0004-process-invoices-in-background-worker.md) | Process invoices in a background worker with Dramatiq and Redis | proposed | 2026-11-28 | — |
| [ADR-0005](../adr/0005-use-sqlalchemy-and-alembic.md) | Use SQLAlchemy 2.0 (async) and Alembic for data access | accepted | 2026-11-28 | — |
