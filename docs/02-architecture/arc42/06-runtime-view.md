---
title: "§6 Runtime View"
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Tech Lead (TBD)", "Customer representative (Customer)"]
last_updated: 2026-11-21
related: [DEC-003, DEC-004, DEC-005, DEC-006, DEC-007, DEC-008, DEC-009, DEC-010, ADR-0001, ADR-0002, ADR-0003]
---

# §6 Runtime View

> **Draft for review at MTG-20261128** ([MTG-20261121](../../01-requirements/meetings/2026-11-21-requirements-workshop.md) A2).
> Steps marked **(proposal)** depend on open questions Q1–Q4 of MTG-20261121 and may change.

## 6.1 Scenario Index
| # | Scenario | Use cases | Feature specs |
|---|---|---|---|
| 6.2 | Invoice processing end to end (PoC) | — (TBD) | — |

## 6.2 Invoice processing end to end (PoC)
**Trigger:** An Accounting Member uploads an invoice file in the SAPS Web App.
**Preconditions:** The user is signed in ([NFR-SEC-001](../../01-requirements/nfr.md#nfr-sec-001)).
Dummy extraction data and dummy ERP data are loaded ([ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md)).

```mermaid
sequenceDiagram
    autonumber
    actor Member as Accounting Member
    actor Manager as Accounting Manager
    participant Web as SAPS Web App
    participant API as SAPS API
    participant DB as SAPS Database

    Member->>Web: Upload invoice file (PDF or image)
    Web->>API: Upload invoice [HTTPS, multipart/form-data]
    API->>DB: Save invoice with status Uploaded [SQL]
    API->>API: Get extracted data via Extraction Port (dummy, proposal Q1)
    alt Extraction failed (EX1)
        API->>DB: Set status Exception [SQL]
    else Data extracted
        API->>DB: Check duplicate by vendor and invoice number, DEC-008 [SQL]
        API->>API: Derive invoice type from PO number (DEC-005)
        API->>API: Get POs, goods receipts and vendors via ERP Data Port (dummy)
        API->>API: Match line by line, 2-way or 3-way (DEC-006, DEC-007)
        API->>DB: Save matching result and status [SQL]
    end
    API-->>Web: 201 Created with invoice status [HTTPS/JSON]

    loop While status is Exception (EX1 to EX9)
        API-->>Web: In-app notification to Accounting Member
        Member->>Web: Review exception and update invoice
        Web->>API: Update invoice [HTTPS/JSON]
        alt A matching field changed (DEC-010)
            API->>API: Re-run matching
        else No matching field changed, or non-PO invoice reviewed
            API->>API: Mark exception resolved
        end
        API->>DB: Save invoice and new status [SQL]
    end

    alt Total amount incl. tax above 300 USD (DEC-009, non-PO see Q4)
        API->>DB: Set status PendingApproval [SQL]
        API-->>Web: In-app notification to Accounting Manager
        Manager->>Web: Approve or reject invoice
        Web->>API: Send approval decision [HTTPS/JSON]
        alt Approved
            API->>DB: Set status PendingReview [SQL]
        else Rejected (proposal, Q3)
            API->>DB: Set status Rejected [SQL]
        end
    else Total amount 300 USD or less
        API->>DB: Set status PendingReview, proposal Q2 [SQL]
    end

    opt Status is PendingReview
        API-->>Web: In-app notification to Accounting Member
        Member->>Web: Check final result
        Web->>API: Confirm result [HTTPS/JSON]
        API->>DB: Set status Completed [SQL]
    end
```

**Notes:**
- The matching result is only displayed; nothing is posted to an ERP ([SCP-OUT-08](../../01-requirements/scope.md)).
- Processing runs inside the SAPS API request in the PoC; asynchronous processing is a decision for later phases.
- How in-app notifications reach the SAPS Web App (polling or push) is decided in the feature spec.

**Related:** [DEC-003](../../01-requirements/decision-log.md#dec-003) to
[DEC-010](../../01-requirements/decision-log.md#dec-010), [ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md),
[ADR-0002](../adr/0002-use-python-fastapi-and-react.md), [ADR-0003](../adr/0003-use-postgresql-and-docker-compose.md).

### 6.2.1 Invoice lifecycle (proposal)
This diagram moves to `data-model.md` §5 when the data model is created.

```mermaid
stateDiagram-v2
    [*] --> Uploaded: Accounting Member uploads file
    Uploaded --> Exception: EX1 extraction failed
    Uploaded --> Matching: data extracted
    Matching --> Exception: EX2–EX9
    Matching --> PendingApproval: matched, total > 300 USD
    Matching --> PendingReview: matched, total ≤ 300 USD
    Exception --> Matching: matching field updated (DEC-010)
    Exception --> PendingApproval: resolved, total > 300 USD
    Exception --> PendingReview: resolved, total ≤ 300 USD
    Exception --> Rejected: rejected by Accounting Member (Q3)
    PendingApproval --> PendingReview: approved by Accounting Manager
    PendingApproval --> Rejected: rejected by Accounting Manager (Q3)
    PendingReview --> Completed: confirmed by Accounting Member
    PendingReview --> Rejected: rejected at final review (Q3)
    Completed --> [*]
    Rejected --> [*]
```

| State | Meaning | Waiting for |
|---|---|---|
| Uploaded | File received; extraction in progress | System |
| Matching | Duplicate check, type derivation and matching in progress | System |
| Exception | Automatic processing stopped (EX1–EX9) | Accounting Member |
| PendingApproval | Total amount above the approval threshold | Accounting Manager |
| PendingReview | Ready for the final check | Accounting Member |
| Completed | Final result confirmed | — |
| Rejected | Invoice rejected (proposal, Q3) | — |
