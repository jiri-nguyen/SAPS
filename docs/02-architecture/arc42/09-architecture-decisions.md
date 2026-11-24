---
title: "§9 Architecture Decisions"
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Tech Lead (TBD)"]
last_updated: 2027-03-01
related: [ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006, ADR-0007, ADR-0008, ADR-0009, ADR-0010]
---

# §9 Architecture Decisions

| ADR | Title | Status | Date | Supersedes / Superseded by |
|---|---|---|---|---|
| [ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md) | Isolate invoice extraction and ERP data behind ports | accepted | 2026-11-21 | — |
| [ADR-0002](../adr/0002-use-python-fastapi-and-react.md) | Use Python/FastAPI and React for the PoC | accepted | 2026-11-21 | — |
| [ADR-0003](../adr/0003-use-postgresql-and-docker-compose.md) | Use PostgreSQL and Docker Compose for the PoC | accepted | 2026-11-21 | — |
| [ADR-0004](../adr/0004-process-invoices-in-background-worker.md) | Process invoices in a background worker with Dramatiq and Redis | accepted | 2026-12-01 | — |
| [ADR-0005](../adr/0005-use-sqlalchemy-and-alembic.md) | Use SQLAlchemy 2.0 (async) and Alembic for data access | accepted | 2026-11-28 | — |
| [ADR-0006](../adr/0006-store-invoice-files-in-seaweedfs.md) | Store invoice files in SeaweedFS through the S3 API | accepted | 2026-12-01 | — |
| [ADR-0007](../adr/0007-prepare-data-model-for-tenants.md) | Prepare the PoC data model for tenants; defer the multi-tenancy model | accepted | 2026-12-05 | — |
| [ADR-0008](../adr/0008-use-session-cookies-for-authentication.md) | Use server-side sessions in HttpOnly cookies for PoC authentication | accepted | 2026-12-05 | — |
| [ADR-0009](../adr/0009-isolate-tenant-data-in-a-shared-database.md) | Isolate tenant data in one shared database with tenant_id and row-level security | proposed | 2027-03-01 | — |
| [ADR-0010](../adr/0010-use-one-keycloak-realm-with-company-groups.md) | Use one Keycloak realm with a group per company; broker Microsoft Entra ID later | proposed | 2027-03-01 | — |
