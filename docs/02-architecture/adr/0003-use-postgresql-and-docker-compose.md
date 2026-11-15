---
id: ADR-0003
title: "ADR-0003: Use PostgreSQL and Docker Compose for the PoC"
status: proposed         # proposed | accepted | rejected | deprecated | superseded
date: 2026-11-21         # date of the latest status change
owner: "Solution Architect (our company)"
deciders: ["Solution Architect (our company)"]
consulted: ["Tech Lead (TBD)"]
last_updated: 2026-11-21
supersedes: ""
superseded_by: ""
related: [CON-01, CON-02, DEC-003, ADR-0001, ADR-0002]
---

# ADR-0003: Use PostgreSQL and Docker Compose for the PoC

## Context and Problem Statement
[ADR-0002](0002-use-python-fastapi-and-react.md) chose Python/FastAPI for the SAPS API and React for the SAPS Web App,
but left the database and the local runtime open. The PoC runs on a local machine for 3 months
([CON-01](../arc42/02-constraints.md), [CON-02](../arc42/02-constraints.md)) and must replay demo scenarios reliably
([DEC-003](../../01-requirements/decision-log.md#dec-003)). The production hosting for later phases is not known yet
(MTG-20261114 Q27).

**Question:** Which database does the SAPS Database use, and how is the PoC started on a local machine?

## Decision Drivers
- Runs locally — [CON-01](../arc42/02-constraints.md)
- 3-month PoC; fast, repeatable setup for every team member — [CON-02](../arc42/02-constraints.md)
- Workflow state and matching results need transactions (status changes, invoiced quantity per PO line — [DEC-007](../../01-requirements/decision-log.md#dec-007))
- The database should be available as a managed service on AWS and Azure for later phases (cloud TBD)
- Choice of the Solution Architect on 2026-11-21

## Considered Options
1. PostgreSQL, all containers started with Docker Compose
2. SQLite file database, applications started natively
3. PostgreSQL installed natively on each developer machine

## Decision Outcome
**Chosen option:** "PostgreSQL, all containers started with Docker Compose", chosen by the Solution Architect.
PostgreSQL is transactional, runs the same locally and as a managed service on both AWS and Azure, and Docker Compose
starts the SAPS Web App, SAPS API and SAPS Database with one command on any machine.

### Consequences
- **Good:** The same database engine is used in the PoC and in a later cloud environment.
- **Good:** One command starts the full PoC; demo data can be reset by recreating the containers.
- **Bad:** Each machine needs Docker installed, and containers use more memory than native processes.
- **Neutral:** Exact PostgreSQL and Docker Compose versions are fixed in the Developer Guide.
- **Neutral:** Schema changes are managed as migrations in code; the intent is described in `data-model.md` (to be created).

### Confirmation
- The repository contains one Docker Compose file that starts all three containers.
- Revisit before the phase after the PoC, when production hosting (MTG-20261114 Q27) is known.

## Pros and Cons of the Options

### PostgreSQL with Docker Compose
- Good, because PostgreSQL supports transactions, constraints and JSON columns (useful for extracted invoice data).
- Good, because Docker Compose gives every team member and the demo machine the same setup.
- Bad, because Docker is an extra prerequisite.

### SQLite, native start
- Good, because there is nothing to install for the database.
- Bad, because concurrent writes are limited, and its SQL dialect differs from managed cloud databases.
- Bad, because each developer installs Python and Node.js versions by hand.

### PostgreSQL installed natively
- Good, because there is no container overhead.
- Bad, because versions and settings drift between machines.
- Bad, because demo data is harder to reset.

## More Information
- Customer agreement: TBD — confirm at the next meeting together with [ADR-0002](0002-use-python-fastapi-and-react.md).
