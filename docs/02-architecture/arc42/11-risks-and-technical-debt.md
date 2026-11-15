---
title: "§11 Risks and Technical Debt"
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Tech Lead (TBD)"]
last_updated: 2026-12-01
related: [ADR-0001, ADR-0004, CON-03, SAPS-34]
---

# §11 Risks and Technical Debt

Probability and impact are the Solution Architect's assessment; reviewed at each milestone.

## 11.1 Risks

| ID | Title | Probability | Impact | Owner | Status |
|---|---|---|---|---|---|
| [RSK-01](#rsk-01) | Real SAP / MuleSoft data differs from the dummy data model | Medium | Medium | Solution Architect | open |

### RSK-01
**Real SAP / MuleSoft data differs from the dummy data model**

| Field | Value |
|---|---|
| Description | The PoC uses dummy ERP fixtures shaped by our logical model ([data-model.md §4.2](../data-model.md#42-external-entities-read-through-ports-not-stored)). The real SAP ECC / S/4HANA data and the MuleSoft API contract are unknown ([CON-03](02-constraints.md)), so the ERP Data Port and matching may need changes after the PoC. |
| Probability | Medium |
| Impact | Medium — rework of adapters and matching after the PoC; schedule of the next phase |
| Mitigation | Keep ERP access behind the ERP Data Port ([ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md)); keep fixtures close to standard SAP purchasing entities; request MuleSoft API specifications as early as possible after the PoC. |
| Contingency | Map SAP fields to the logical model inside the adapter; extend the model where needed. |
| Owner | Solution Architect |
| Status | open |
| Source | [ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md), [Test Strategy §13](../../05-testing/test-strategy.md#13-risks--assumptions) |

## 11.2 Technical Debt

| ID | Title | Impact | Remediation effort | Status |
|---|---|---|---|---|
| [TD-01](#td-01) | Worker holds a database transaction for the whole job | M | M | open |

### TD-01
**Worker holds a database transaction for the whole job**

| Field | Value |
|---|---|
| Description | A SAPS Worker actor locks the invoice row and keeps one transaction open from start to end of the job. The lock also tells the sweeper that the job is running (`FOR UPDATE SKIP LOCKED`). |
| Cause | Simplest correct design for the PoC, where extraction and ERP data are dummy and a job takes milliseconds ([ADR-0004](../adr/0004-process-invoices-in-background-worker.md), spike [SAPS-34](https://linear.app/jiringuyen/issue/SAPS-34)). |
| Impact | With real OCR / AI and SAP calls (seconds or longer), long transactions hold database connections and locks, which limits throughput ([NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)). |
| Remediation | Replace the long transaction with a lease: set status Matching with a `processing_until` timestamp in a short transaction, call external services outside any transaction, save the result in a second short transaction; the sweeper re-sends invoices whose lease has expired. |
| Effort | M |
| Backlog | TBD — before real extraction or SAP integration starts |
| Status | open |
