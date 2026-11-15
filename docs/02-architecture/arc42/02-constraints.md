---
title: "§2 Architecture Constraints"
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Tech Lead (TBD)"]
last_updated: 2026-11-28
related: [DEC-002, DEC-003, DEC-017, MTG-20261121]
---

# §2 Architecture Constraints

## 2.1 Technical Constraints
| ID | Constraint | Impact on the architecture | Source |
|---|---|---|---|
| CON-01 | The PoC runs on a local machine; no cloud environment | All components must run locally; no managed cloud services in the PoC | [DEC-003](../../01-requirements/decision-log.md#dec-003) |
| CON-03 | After the PoC, ERP data (POs, goods receipts, vendors) comes from SAP ECC or SAP S/4HANA through MuleSoft APIs or MuleSoft MCP Tools | ERP access must be replaceable without changing the matching logic ([ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md)) | [MTG-20261121](../../01-requirements/meetings/2026-11-21-requirements-workshop.md) R4 |

## 2.2 Organizational Constraints
| ID | Constraint | Impact on the architecture | Source |
|---|---|---|---|
| CON-02 | The PoC lasts 3 months from 2026-11-21; the demo is on 2027-02-22 | Favors simple, well-known technology and a single deployable stack | [DEC-003](../../01-requirements/decision-log.md#dec-003), [DEC-017](../../01-requirements/decision-log.md#dec-017) |

## 2.3 Regulatory & Legal Constraints
None identified yet. Data residency and retention are open (MTG-20261114 Q28, Q30).

## 2.4 Conventions
| ID | Convention | Reference |
|---|---|---|
| CON-04 | Documentation follows the company documentation standard | [CLAUDE.md](../../../CLAUDE.md) |
| CON-05 | Work items are tracked in Linear with keys `SAPS-NNN` | [DEC-002](../../01-requirements/decision-log.md#dec-002) |
