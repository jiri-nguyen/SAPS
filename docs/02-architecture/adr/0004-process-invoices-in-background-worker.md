---
id: ADR-0004
title: "ADR-0004: Process invoices in a background worker with Dramatiq and Redis"
status: proposed         # proposed | accepted | rejected | deprecated | superseded
date: 2026-11-28         # date of the latest status change
owner: "Solution Architect (our company)"
deciders: ["Solution Architect (our company)"]
consulted: ["Tech Lead (TBD)"]
last_updated: 2026-11-28
supersedes: ""
superseded_by: ""
related: [NFR-SCAL-001, CON-01, CON-02, CON-03, DEC-010, ADR-0001, ADR-0003, ADR-0005, SAPS-33]
---

# ADR-0004: Process invoices in a background worker with Dramatiq and Redis

## Context and Problem Statement
After an upload, the system extracts the invoice data, checks for duplicates, derives the invoice type and matches
the lines ([§6.2](../arc42/06-runtime-view.md)). Matching also re-runs after a manual update of a matching field
([DEC-010](../../01-requirements/decision-log.md#dec-010)). In the PoC these steps are fast because extraction and
ERP data are dummy data. After the PoC they call an OCR/AI service and SAP through MuleSoft
([CON-03](../arc42/02-constraints.md)), which can take seconds or longer and can fail temporarily.
The design must scale beyond the PoC without a redesign ([NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)).

**Question:** Where and how does invoice processing (extraction, duplicate check, matching) run?

## Decision Drivers
- Scale beyond the PoC without redesign — [NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)
- Later steps call slow, unreliable external services — [CON-03](../arc42/02-constraints.md), [SCP-OUT-01](../../01-requirements/scope.md)
- Runs locally with Docker Compose — [CON-01](../arc42/02-constraints.md), [ADR-0003](0003-use-postgresql-and-docker-compose.md)
- 3-month PoC; few moving parts — [CON-02](../arc42/02-constraints.md)
- Work must not be lost when a container restarts
- Preference of the Solution Architect (2026-11-28) for Redis as the message broker

## Considered Options
1. Synchronous processing inside the upload request (SAPS API)
2. FastAPI background tasks in the SAPS API process
3. Worker with a job queue in PostgreSQL (own table or the Procrastinate library)
4. Worker with Celery on Redis
5. Worker with Dramatiq on Redis

## Decision Outcome
**Chosen option:** "Worker with Dramatiq on Redis", because a dedicated broker scales by adding workers without
loading the database (NFR-SCAL-001), Dramatiq's defaults are safe for this workload (messages are acknowledged after
the job finishes; retries with back-off are built in), and Redis is available as a managed service on AWS and Azure
for later phases.

### How it works
- New containers: **SAPS Worker** (Dramatiq workers, same Python codebase as the SAPS API) and
  **SAPS Message Broker** (Redis).
- The SAPS API saves the uploaded file (SAPS File Storage, [ADR-0006](0006-store-invoice-files-in-seaweedfs.md)) and the invoice (status Uploaded), **commits**, then sends a message, and
  returns `202 Accepted`.
- Actors: `process_invoice(invoice_id)` and `rematch_invoice(invoice_id)` ([DEC-010](../../01-requirements/decision-log.md#dec-010)).
- Messages are sent through a **Job Queue Port**, so another broker (e.g. Amazon SQS, Azure Service Bus) can replace
  Redis later without changing processing logic (same pattern as [ADR-0001](0001-isolate-extraction-and-erp-behind-ports.md)).
- The SAPS Worker writes results and in-app notifications to the SAPS Database. The SAPS Web App reads status and
  notifications from the SAPS API (polling or push, decided in the feature spec).

### Safeguards
| # | Risk | Safeguard |
|---|---|---|
| S1 | Invoice saved in PostgreSQL but message not sent (crash between commit and send) — two systems, no shared transaction | **Sweeper**: a periodic task in the SAPS Worker re-sends messages for invoices in status Uploaded or Matching longer than a configurable time. Only one worker instance runs it (lock). A transactional outbox is a later option if needed. |
| S2 | A message is processed twice (redelivery after a crash, sweeper re-send) | Actors are **idempotent**: each actor locks the invoice row (`SELECT … FOR UPDATE`) and does nothing if the invoice is no longer in the expected status. |
| S3 | Redis restart loses queued messages | Redis persistence on (`appendonly yes`) in Docker Compose. Redis is never the source of truth; the sweeper (S1) recovers lost messages from PostgreSQL. |
| S4 | A job keeps failing | Dramatiq retries with exponential back-off up to a configured limit. After the last retry, extraction failures set the invoice to Exception (EX1); other technical failures are logged and handled as defined in the feature spec. |
| S5 | Async actors with SQLAlchemy async | Dramatiq supports `async def` actors through the optional `AsyncIO` middleware: one event-loop thread per worker process; concurrency per process stays equal to the number of worker threads (default 8) ([Dramatiq cookbook](https://dramatiq.io/cookbook.html#asyncio-actors)). The SQLAlchemy async engine is created on that event loop. Time limits and cancellation for async actors are not documented and are checked in the spike. Fallback: sync sessions on the same models (psycopg 3, [ADR-0005](0005-use-sqlalchemy-and-alembic.md)). |
| S6 | Dramatiq has no built-in scheduler for the sweeper | Scheduler library inside the SAPS Worker (e.g. APScheduler); chosen in the spike. |

### Consequences
- **Good:** Upload requests stay fast even when extraction and SAP calls become slow.
- **Good:** Throughput grows by running more SAPS Worker instances; PostgreSQL is not used as a queue.
- **Good:** Retries and acknowledgement after completion come built in.
- **Bad:** One more container (Redis) to run and configure.
- **Bad:** PostgreSQL and Redis are written separately; consistency relies on the sweeper and idempotent actors (S1, S2).
- **Bad:** Users see results asynchronously; the SAPS Web App must refresh status.
- **Neutral:** Redis licensing changed from version 7.4 (RSAL / SSPL; Redis 8 adds AGPL as an option). This does not affect
  local use in the PoC. For a cloud phase, choose a managed Redis OSS or Valkey (BSD-licensed, protocol-compatible) service.
- **Neutral:** The `ProcessingJob` table is not needed; status lives in `Invoice.status` and history in `InvoiceEvent`
  ([data model](../data-model.md)).

### Confirmation
- Docker Compose starts SAPS Web App, SAPS API, SAPS Worker, SAPS Message Broker, SAPS File Storage ([ADR-0006](0006-store-invoice-files-in-seaweedfs.md)) and SAPS Database.
- Integration tests (Testcontainers with PostgreSQL and Redis):
  - a worker is stopped during a job → the message is redelivered and the invoice is processed once;
  - an invoice left in status Uploaded without a message → the sweeper processes it.
- Spike (Linear issue under SAPS-30): `AsyncIO` middleware with SQLAlchemy async sessions (engine per event loop, time limits and cancellation); sweeper scheduling and locking.
- On acceptance, [§6.2 Runtime View](../arc42/06-runtime-view.md) is updated to the asynchronous flow.
- Revisit when the workload profile is known (MTG-20261114 Q5, Q6), or before moving to a cloud environment.

## Pros and Cons of the Options

### Synchronous processing in the upload request
- Good, because it is the simplest to build and to debug.
- Bad, because slow OCR/AI or SAP calls would block the user and hit HTTP timeouts.
- Bad, because work is lost if the request fails half-way.

### FastAPI background tasks
- Good, because the response returns at once with almost no extra code.
- Bad, because tasks live in memory and are lost when the SAPS API restarts.
- Bad, because processing cannot scale separately from the API.

### Worker with a job queue in PostgreSQL
- Good, because jobs can be added in the same transaction as the invoice (no dual write).
- Good, because no new infrastructure is needed.
- Bad, because polling or notifications add load to the database, and throughput is lower than a dedicated broker.
- Bad, because the main library option (Procrastinate) has a small maintainer base.

### Worker with Celery on Redis
- Good, because Celery has the largest ecosystem (monitoring with Flower, scheduling with celery beat).
- Bad, because its defaults acknowledge messages early; reliable delivery needs extra configuration.
- Bad, because it is heavier than needed for two job types.

### Worker with Dramatiq on Redis
- Good, because acknowledgement after completion and retries are the defaults.
- Good, because it is small and simple to configure.
- Bad, because there is no built-in scheduler and a smaller ecosystem than Celery.
- Bad, because the dual write between PostgreSQL and Redis needs safeguards (S1, S2).

## More Information
- Linear: [SAPS-33](https://linear.app/jiringuyen/issue/SAPS-33)
- Customer agreement: not required (internal design decision; Redis is an addition to the stack agreed in
  [DEC-019](../../01-requirements/decision-log.md#dec-019) — to be mentioned to the Product Owner at the next meeting).
