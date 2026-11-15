---
id: ADR-0005
title: "ADR-0005: Use SQLAlchemy 2.0 (async) and Alembic for data access"
status: accepted         # proposed | accepted | rejected | deprecated | superseded
date: 2026-11-28         # date of the latest status change
owner: "Solution Architect (our company)"
deciders: ["Solution Architect (our company)"]
consulted: ["Tech Lead (TBD)"]
last_updated: 2026-11-28
supersedes: ""
superseded_by: ""
related: [ADR-0002, ADR-0003, ADR-0004, NFR-SCAL-001, CON-02]
---

# ADR-0005: Use SQLAlchemy 2.0 (async) and Alembic for data access

## Context and Problem Statement
The SAPS API (Python/FastAPI, [ADR-0002](0002-use-python-fastapi-and-react.md)) and the SAPS Worker
([ADR-0004](0004-process-invoices-in-background-worker.md)) read and write the SAPS Database (PostgreSQL,
[ADR-0003](0003-use-postgresql-and-docker-compose.md)). The [data model](../data-model.md) has about ten tables,
line-level matching queries, and row locking. The schema will change often during the PoC.

**Question:** How does Python code access PostgreSQL, and how is the schema migrated?

## Decision Drivers
- Readable, typed data access for matching and workflow logic
- Row locking and transactions for state changes (e.g. `SELECT … FOR UPDATE`)
- Frequent schema changes in a 3-month PoC — [CON-02](../arc42/02-constraints.md)
- I/O-bound work after the PoC (OCR/AI, SAP via MuleSoft); FastAPI is async — [NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)

## Considered Options
1. SQLAlchemy 2.0 ORM (async) + Alembic
2. SQLModel (SQLAlchemy + Pydantic) + Alembic
3. Plain SQL with asyncpg + hand-written migration scripts

## Decision Outcome
**Chosen option:** "SQLAlchemy 2.0 ORM (async) + Alembic", because it gives typed models, full control over complex
queries and locking, and the most widely used migration tool for Python, while fitting FastAPI's async model.

- Driver: **psycopg 3**, which supports both async and sync connections. Code that cannot run async
  (for example a worker library without async support) can use sync sessions on the same models.
- Migrations: Alembic, forward-only, in the SAPS API codebase (`migrations/`), as described in
  [data-model.md §7](../data-model.md#7-schema-migration-approach).
- Pydantic models (API schemas) stay separate from ORM models.

### Consequences
- **Good:** One mature toolkit for models, queries, locking and migrations.
- **Good:** Async sessions suit FastAPI and the I/O-bound calls that come after the PoC.
- **Bad:** Async SQLAlchemy needs care (no lazy loading in async code; explicit eager loading) and makes tests a little more complex.
- **Neutral:** API schemas and ORM models are written separately (some duplication, clearer boundaries).

### Confirmation
- Code review rule: no lazy loading in async code paths; relationships are loaded explicitly.
- CI runs `alembic upgrade head` against a fresh PostgreSQL in the integration tests.

## Pros and Cons of the Options

### SQLAlchemy 2.0 ORM (async) + Alembic
- Good, because it is the most widely used Python ORM, with typed 2.0-style models.
- Good, because row locking (`with_for_update`) and complex joins are first-class.
- Bad, because async usage has pitfalls (lazy loading).

### SQLModel + Alembic
- Good, because one class serves as ORM model and API schema, which is concise with FastAPI.
- Bad, because complex queries fall back to SQLAlchemy anyway, and mixing API schemas with tables couples layers.

### Plain SQL with asyncpg
- Good, because it is the fastest option and gives full SQL control.
- Bad, because mapping, migrations and query building are hand-written, which costs time in a 3-month PoC.

## More Information
- Customer agreement: not required (internal design decision; within the stack agreed in [DEC-019](../../01-requirements/decision-log.md#dec-019)).
