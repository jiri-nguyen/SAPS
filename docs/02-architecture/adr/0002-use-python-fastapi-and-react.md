---
id: ADR-0002
title: "ADR-0002: Use Python/FastAPI and React for the PoC"
status: accepted         # proposed | accepted | rejected | deprecated | superseded
date: 2026-11-21         # date of the latest status change
owner: "Solution Architect (our company)"
deciders: ["Solution Architect (our company)"]
consulted: ["Tech Lead (TBD)"]
last_updated: 2026-11-21
supersedes: ""
superseded_by: ""
related: [DEC-003, CON-01, CON-02, NFR-USAB-001, ADR-0001, ADR-0003]
---

# ADR-0002: Use Python/FastAPI and React for the PoC

## Context and Problem Statement
The PoC builds a web application for Accounting Members and Accounting Managers: upload, matching, exception
review, approval and final review ([scope.md](../../01-requirements/scope.md) v0.2). It runs locally and lasts
3 months ([CON-01](../arc42/02-constraints.md), [CON-02](../arc42/02-constraints.md)). Later phases add real invoice
extraction (OCR/AI) and SAP integration through MuleSoft.

**Question:** Which backend and frontend technologies does the PoC use?

## Decision Drivers
- Runs locally — [CON-01](../arc42/02-constraints.md)
- 3-month PoC; fast delivery — [CON-02](../arc42/02-constraints.md)
- Later phases add OCR/AI extraction — [SCP-OUT-01](../../01-requirements/scope.md)
- Contract-first API documented in OpenAPI (company standard) — [CON-04](../arc42/02-constraints.md)
- Choice of the Solution Architect on 2026-11-21

## Considered Options
1. Python 3 / FastAPI backend + React frontend
2. .NET / ASP.NET Core backend + Angular frontend
3. Node.js / NestJS backend + React frontend

## Decision Outcome
**Chosen option:** "Python 3 / FastAPI backend + React frontend", chosen by the Solution Architect. Python has the
widest ecosystem for document AI, OCR and LLM integration, which later phases need, and FastAPI works natively with
OpenAPI schemas.

Container names: **SAPS API** (Python/FastAPI) and **SAPS Web App** (React single-page application).

### Consequences
- **Good:** Real extraction can be added later in the same language as the SAPS API.
- **Good:** FastAPI request/response models map directly to the OpenAPI contract.
- **Bad:** Python is dynamically typed; type hints and a type checker are needed to keep the code safe.
- **Neutral:** Database and local runtime are decided in [ADR-0003](0003-use-postgresql-and-docker-compose.md).
- **Neutral:** Exact versions are fixed in the Developer Guide when the project is set up.

### Confirmation
- The repository skeleton uses FastAPI for the SAPS API and React for the SAPS Web App.
- Revisit before the phase after the PoC, when production hosting (MTG-20261114 Q27) is known.

## Pros and Cons of the Options

### Python 3 / FastAPI + React
- Good, because of the Python ecosystem for OCR, document AI and LLM clients.
- Good, because FastAPI generates and validates against OpenAPI schemas.
- Good, because React has a large ecosystem of UI components for forms and data tables.
- Bad, because Python needs extra tooling (type checker) for type safety.

### .NET / ASP.NET Core + Angular
- Good, because it is strongly typed end to end and mature for enterprise systems.
- Bad, because fewer document AI / OCR libraries are native to .NET than to Python.
- Bad, because Angular is heavier to set up for a short PoC.

### Node.js / NestJS + React
- Good, because one language (TypeScript) is used for backend and frontend.
- Bad, because the document AI / OCR ecosystem is smaller than Python's.

## More Information
- Customer agreement: TBD — confirm at the next meeting whether the customer must agree the PoC stack.
- Database and local runtime: [ADR-0003](0003-use-postgresql-and-docker-compose.md).
