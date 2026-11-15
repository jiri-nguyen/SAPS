---
id: ADR-0004
title: "ADR-0004: Process invoices in a background worker with a PostgreSQL job queue"
status: proposed         # proposed | accepted | rejected | deprecated | superseded
date: 2026-11-28         # date of the latest status change
owner: "Solution Architect (our company)"
deciders: ["Solution Architect (our company)"]
consulted: ["Tech Lead (TBD)"]
last_updated: 2026-11-28
supersedes: ""
superseded_by: ""
related: [NFR-SCAL-001, CON-01, CON-02, CON-03, DEC-010, ADR-0001, ADR-0003, SAPS-33]
---

# ADR-0004: Process invoices in a background worker with a PostgreSQL job queue

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
- Runs locally with Docker Compose; no managed cloud services — [CON-01](../arc42/02-constraints.md), [ADR-0003](0003-use-postgresql-and-docker-compose.md)
- 3-month PoC; few moving parts — [CON-02](../arc42/02-constraints.md)
- Work must not be lost when a container restarts

## Considered Options
1. Synchronous processing inside the upload request (SAPS API)
2. FastAPI background tasks in the SAPS API process
3. Separate worker container with a job queue table in PostgreSQL
4. Separate worker container with a message broker (e.g. Redis or RabbitMQ)

## Decision Outcome
**Chosen option:** "Separate worker container with a job queue table in PostgreSQL", because it decouples slow
processing from user requests and scales by adding workers (NFR-SCAL-001), keeps jobs durable across restarts, and
needs no infrastructure beyond the PostgreSQL already chosen in ADR-0003 (CON-01, CON-02).

How it works:
- The SAPS API stores the uploaded file and the invoice (status Uploaded), adds a job, and returns `202 Accepted`.
- A new container, **SAPS Worker** (same Python codebase as the SAPS API), takes jobs from the job table with
  `SELECT … FOR UPDATE SKIP LOCKED`, so several workers can run in parallel without taking the same job.
- Job types: process a new invoice; re-match an invoice after a manual update (DEC-010).
- Failed jobs are retried a limited number of times; then the invoice goes to status Exception.
- The SAPS Worker writes in-app notifications; the SAPS Web App reads invoice status and notifications from the SAPS API.
- Jobs are taken through a **Job Queue Port**, so a cloud queue (e.g. Amazon SQS, Azure Service Bus) can replace
  the table later without changing processing logic (same pattern as [ADR-0001](0001-isolate-extraction-and-erp-behind-ports.md)).

### Consequences
- **Good:** Upload requests stay fast even when extraction and SAP calls become slow.
- **Good:** Throughput grows by running more SAPS Worker instances.
- **Good:** Jobs survive container restarts; retries are possible.
- **Bad:** Users see results asynchronously; the SAPS Web App must refresh status (polling or push, decided in the feature spec).
- **Bad:** Polling the job table adds database load; acceptable at PoC volume, revisit with the workload profile (MTG-20261114 Q5, Q6).
- **Neutral:** One more container in Docker Compose, the C4 L2 diagram and the glossary.
- **Neutral:** Job handlers must be idempotent (a job may run twice after a crash).

### Confirmation
- Docker Compose starts SAPS Web App, SAPS API, SAPS Worker and SAPS Database.
- An integration test runs two workers against one queue and checks that each job runs exactly once.
- On acceptance, [§6.2 Runtime View](../arc42/06-runtime-view.md) is updated to the asynchronous flow.
- Revisit when the workload profile is known, or before moving to a cloud environment.

## Pros and Cons of the Options

### Synchronous processing in the upload request
- Good, because it is the simplest to build and to debug.
- Bad, because slow OCR/AI or SAP calls would block the user and hit HTTP timeouts.
- Bad, because work is lost if the request fails half-way.

### FastAPI background tasks
- Good, because the response returns at once with almost no extra code.
- Bad, because tasks live in memory and are lost when the SAPS API restarts.
- Bad, because processing cannot scale separately from the API.

### Worker with a PostgreSQL job table
- Good, because jobs are durable and transactional with the invoice data.
- Good, because no new infrastructure is needed.
- Bad, because a database queue has lower throughput than a dedicated broker.

### Worker with a message broker
- Good, because brokers handle high throughput, routing and retries.
- Bad, because it adds a container and a technology to learn and run in a 3-month local PoC.
- Bad, because job state and invoice state live in two systems, which complicates consistency.

## More Information
- Linear: [SAPS-33](https://linear.app/jiringuyen/issue/SAPS-33)
- Customer agreement: not required (internal design decision).
