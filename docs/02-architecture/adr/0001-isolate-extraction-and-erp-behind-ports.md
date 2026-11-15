---
id: ADR-0001
title: "ADR-0001: Isolate invoice extraction and ERP data behind ports"
status: accepted         # proposed | accepted | rejected | deprecated | superseded
date: 2026-11-21         # date of the latest status change
owner: "Solution Architect (our company)"
deciders: ["Solution Architect (our company)"]
consulted: ["Tech Lead (TBD)"]
last_updated: 2026-11-21
supersedes: ""
superseded_by: ""
related: [DEC-004, CON-01, CON-02, CON-03, SCP-OUT-01, SCP-OUT-02]
---

# ADR-0001: Isolate invoice extraction and ERP data behind ports

## Context and Problem Statement
In the PoC, invoice extraction results and ERP data (purchase orders, goods receipts, vendors) are dummy data
([DEC-004](../../01-requirements/decision-log.md#dec-004)). After the PoC, extraction will use a real OCR/AI service
and ERP data will come from SAP ECC or SAP S/4HANA through MuleSoft APIs or MuleSoft MCP Tools
([CON-03](../arc42/02-constraints.md)). The matching logic built in the PoC should survive that change.

**Question:** How does the SAPS API access invoice extraction and ERP data so that dummy sources can be replaced later?

## Decision Drivers
- Dummy data in the PoC, real sources later — [DEC-004](../../01-requirements/decision-log.md#dec-004), [CON-03](../arc42/02-constraints.md)
- The PoC runs locally — [CON-01](../arc42/02-constraints.md)
- 3-month PoC; keep the moving parts small — [CON-02](../arc42/02-constraints.md)
- Demo scenarios, including every exception type, must be reproducible — [DEC-003](../../01-requirements/decision-log.md#dec-003)
- The real MuleSoft API contract is not known yet

## Considered Options
1. Ports and adapters inside the SAPS API, with dummy adapters that read fixture files
2. Separate mock services that simulate the extraction service and the MuleSoft APIs over HTTP
3. Dummy data loaded directly into the SAPS Database; matching logic reads those tables

## Decision Outcome
**Chosen option:** "Ports and adapters inside the SAPS API", because it keeps the matching logic independent of the
data source (CON-03) with the fewest moving parts for a local, 3-month PoC (CON-01, CON-02), and it does not force us
to guess the MuleSoft HTTP contract now.

The SAPS API defines two ports (interfaces) used by the matching logic:

| Port | Provides | PoC adapter | Later adapter |
|---|---|---|---|
| Extraction Port | Extracted invoice data (header and lines) for an uploaded file | Dummy Extraction Adapter (fixture files) | OCR/AI extraction adapter |
| ERP Data Port | Purchase orders, goods receipts, vendors | Dummy ERP Adapter (fixture files) | MuleSoft API or MuleSoft MCP Tools adapter |

The adapter for each port is selected by configuration at startup.

### Consequences
- **Good:** Matching logic and its tests do not change when real sources arrive.
- **Good:** Demo scenarios are reproducible: each scenario is a set of fixture files.
- **Good:** The ports can be unit-tested with in-memory fakes.
- **Bad:** The port interfaces are designed before the real MuleSoft contract is known; they may need changes later.
- **Neutral:** Fixture files must be kept consistent with the demo scenarios (one owner: QA or Tech Lead).
- **Neutral:** How an upload is linked to its dummy extraction data is open
  ([MTG-20261121](../../01-requirements/meetings/2026-11-21-requirements-workshop.md) Q1); the Dummy Extraction Adapter implements whatever is agreed.

### Confirmation
- Code review rule: matching and workflow code imports ports only, never adapters.
- Automated architecture test in CI (e.g. an import-rule check) fails if domain code imports an adapter module.
- Revisit when the MuleSoft API or MCP Tools contract is available.

## Pros and Cons of the Options

### Ports and adapters inside the SAPS API
Interfaces in the domain layer; dummy implementations read JSON fixture files.
- Good, because the source can be swapped by configuration without touching matching logic.
- Good, because there is only one service to run locally.
- Bad, because there is no network behavior (latency, timeouts, errors) to test in the PoC.

### Separate mock services over HTTP
Mock HTTP services that imitate the extraction service and the MuleSoft APIs.
- Good, because the PoC exercises real network calls and error handling.
- Bad, because we must invent an HTTP contract that the real MuleSoft APIs will probably not match.
- Bad, because there are more services to build and run in a 3-month local PoC.

### Dummy data loaded into the SAPS Database
Seed scripts put POs, goods receipts and extracted data straight into the database.
- Good, because it is the fastest to build.
- Bad, because matching logic becomes coupled to the local tables; replacing them with MuleSoft calls means rewriting it.
- Bad, because real ERP data would be copied into the SAPS Database later, which raises data ownership questions.

## More Information
- Customer agreement: not required (internal design decision; does not change scope).
- Related scope items: [SCP-IN-02](../../01-requirements/scope.md), [SCP-IN-09](../../01-requirements/scope.md),
  [SCP-OUT-01](../../01-requirements/scope.md), [SCP-OUT-02](../../01-requirements/scope.md).
