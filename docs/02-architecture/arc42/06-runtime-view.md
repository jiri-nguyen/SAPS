---
title: "§6 Runtime View"
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Tech Lead (TBD)", "Customer representative (Customer)"]
last_updated: 2026-11-28
related: [DEC-003, DEC-004, DEC-005, DEC-006, DEC-007, DEC-008, DEC-009, DEC-010, DEC-012, DEC-013, DEC-014, DEC-016, DEC-021, ADR-0001, ADR-0002, ADR-0003]
---

# §6 Runtime View

The end-to-end flow was approved by the Product Owner in
[MTG-20261128](../../01-requirements/meetings/2026-11-28-poc-flow-review.md) R2.

## 6.1 Scenario Index
| # | Scenario | Use cases | Feature specs |
|---|---|---|---|
| 6.2 | Invoice processing end to end (PoC) | UC-02 to UC-06, UC-08 ([§1](01-introduction-and-goals.md#use-cases)) | — |

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
    API->>API: Get extracted data via Extraction Port (dummy sample set, DEC-012)
    alt Extraction failed or file not in sample set (EX1)
        API->>DB: Set status Exception [SQL]
    else Data extracted
        API->>DB: Check duplicate by vendor and invoice number, DEC-008 [SQL]
        API->>API: Derive invoice type from PO number (DEC-005)
        API->>API: Get POs, goods receipts and vendors via ERP Data Port (dummy)
        API->>API: Match line by line, 2-way or 3-way (DEC-006, DEC-007)
        API->>DB: Save matching result and status [SQL]
    end
    API-->>Web: 201 Created with invoice status [HTTPS/JSON]

    loop While status is Exception (EX1 to EX9, DEC-016)
        API-->>Web: In-app notification to Accounting Members (DEC-021)
        Member->>Web: Pick invoice from queue, review and update it
        Web->>API: Update invoice [HTTPS/JSON]
        alt A matching field changed (DEC-010)
            API->>API: Re-run matching
        else No matching field changed, or non-PO invoice reviewed
            API->>API: Mark exception resolved
        end
        API->>DB: Save invoice and new status [SQL]
    end

    alt Total amount incl. tax above approval threshold (DEC-009, DEC-013, DEC-015)
        API->>DB: Set status PendingApproval [SQL]
        API-->>Web: In-app notification to Accounting Manager (DEC-021)
        Manager->>Web: Approve or reject invoice
        Web->>API: Send approval decision [HTTPS/JSON]
        alt Approved
            API->>DB: Set status PendingReview [SQL]
        else Rejected, final state (DEC-014)
            API->>DB: Set status Rejected [SQL]
        end
    else Total amount at or below approval threshold
        API->>DB: Set status PendingReview [SQL]
    end

    opt Status is PendingReview
        API-->>Web: In-app notification to Accounting Members (DEC-021)
        Member->>Web: Check final result
        Web->>API: Confirm or reject result [HTTPS/JSON]
        alt Confirmed
            API->>DB: Set status Completed [SQL]
        else Rejected, final state (DEC-014)
            API->>DB: Set status Rejected [SQL]
        end
    end
```

**Notes:**
- The matching result is only displayed; nothing is posted to an ERP ([SCP-OUT-08](../../01-requirements/scope.md)).
- Processing runs inside the SAPS API request in this draft; the processing model is decided in an ADR ([SAPS-33](https://linear.app/jiringuyen/issue/SAPS-33), driven by [NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)).
- During exception handling an Accounting Member can also reject the invoice (DEC-014); see the lifecycle below.
- How in-app notifications reach the SAPS Web App (polling or push) is decided in the feature spec.

**Related:** [DEC-003](../../01-requirements/decision-log.md#dec-003) to
[DEC-010](../../01-requirements/decision-log.md#dec-010), [ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md),
[ADR-0002](../adr/0002-use-python-fastapi-and-react.md), [ADR-0003](../adr/0003-use-postgresql-and-docker-compose.md).

### 6.2.1 Invoice lifecycle
This diagram moves to `data-model.md` §5 when the data model is created ([SAPS-31](https://linear.app/jiringuyen/issue/SAPS-31)).

```mermaid
stateDiagram-v2
    [*] --> Uploaded: Accounting Member uploads file
    Uploaded --> Exception: EX1 extraction failed or unknown file
    Uploaded --> Matching: data extracted
    Matching --> Exception: EX2–EX9
    Matching --> PendingApproval: matched, total above threshold
    Matching --> PendingReview: matched, total at or below threshold
    Exception --> Matching: matching field updated (DEC-010)
    Exception --> PendingApproval: resolved, total above threshold
    Exception --> PendingReview: resolved, total at or below threshold
    Exception --> Rejected: rejected by Accounting Member (DEC-014)
    PendingApproval --> PendingReview: approved by Accounting Manager
    PendingApproval --> Rejected: rejected by Accounting Manager (DEC-014)
    PendingReview --> Completed: confirmed by Accounting Member
    PendingReview --> Rejected: rejected at final review (DEC-014)
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
| Rejected | Invoice rejected; final state (DEC-014) | — |
