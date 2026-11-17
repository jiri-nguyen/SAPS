---
title: "§6 Runtime View"
status: draft            # draft | in-review | approved | deprecated
owner: "Solution Architect (our company)"
reviewers: ["Tech Lead (TBD)", "Product Owner (Customer)"]
last_updated: 2026-12-08
related: [DEC-003, DEC-004, DEC-005, DEC-006, DEC-007, DEC-008, DEC-009, DEC-010, DEC-012, DEC-013, DEC-014, DEC-016, DEC-021, ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006]
---

# §6 Runtime View

The business flow was approved by the Product Owner in
[MTG-20261128](../../01-requirements/meetings/2026-11-28-poc-flow-review.md) R2. Processing is asynchronous
([ADR-0004](../adr/0004-process-invoices-in-background-worker.md)); files are stored in SAPS File Storage
([ADR-0006](../adr/0006-store-invoice-files-in-seaweedfs.md)).

## 6.1 Scenario Index
| # | Scenario | Use cases | Feature specs |
|---|---|---|---|
| 6.2 | Invoice processing end to end (PoC) | UC-02 to UC-06, UC-08 ([§1](01-introduction-and-goals.md#use-cases)) | — |
| 6.3 | Recovery of stuck invoices (sweeper) | — (system) | — |

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
    participant Files as SAPS File Storage
    participant DB as SAPS Database
    participant MQ as SAPS Message Broker
    participant Worker as SAPS Worker

    Member->>Web: Upload invoice file (PDF or image)
    Web->>API: Upload invoice [HTTPS, multipart/form-data]
    API->>Files: Store file under invoices/invoice-id/sha256 [S3 API/HTTP]
    API->>DB: Insert invoice with status Uploaded, commit [SQL]
    API->>MQ: Send process_invoice(invoice_id) [Redis]
    API-->>Web: 202 Accepted with invoice id [HTTPS/JSON]

    MQ->>Worker: Deliver process_invoice
    Worker->>DB: Lock invoice row, continue only if status is Uploaded [SQL]
    Worker->>Worker: Get extracted data via Extraction Port (dummy sample set by SHA-256, DEC-012)
    alt Extraction failed or file not in sample set (EX1)
        Worker->>DB: Set status Exception, notify Accounting Members [SQL]
    else Data extracted
        Worker->>DB: Check duplicate by vendor and invoice number, DEC-008 [SQL]
        Worker->>Worker: Derive invoice type from PO number (DEC-005)
        Worker->>Worker: Get POs, goods receipts and vendors via ERP Data Port (dummy)
        Worker->>Worker: Match line by line, 2-way or 3-way (DEC-006, DEC-007)
        Worker->>DB: Save result, next status and notifications, commit [SQL]
    end
    Worker-->>MQ: Acknowledge message

    loop While status is Exception (EX1 to EX10, DEC-016)
        Web->>API: Poll status and notifications [HTTPS/JSON]
        API-->>Web: Notification for Accounting Members (DEC-021)
        Member->>Web: Pick invoice from queue, review and update it
        Web->>API: Update invoice [HTTPS/JSON]
        alt A matching field changed (DEC-010)
            API->>DB: Save changes [SQL]
            API->>MQ: Send rematch_invoice(invoice_id) [Redis]
            MQ->>Worker: Deliver rematch_invoice
            Worker->>DB: Lock row, re-run matching, save next status [SQL]
        else No matching field changed, or non-PO invoice reviewed
            API->>DB: Mark exception resolved, set next status [SQL]
        end
    end

    alt Total amount incl. tax above approval threshold (DEC-009, DEC-013, DEC-015)
        Web->>API: Poll notifications [HTTPS/JSON]
        API-->>Web: Notification for Accounting Manager (DEC-021)
        Manager->>Web: Approve or reject invoice
        Web->>API: Send approval decision [HTTPS/JSON]
        alt Approved
            API->>DB: Save approval, set status PendingReview [SQL]
        else Rejected, final state (DEC-014)
            API->>DB: Save approval, set status Rejected [SQL]
        end
    else Total amount at or below approval threshold
        Note over DB: Status already PendingReview
    end

    opt Status is PendingReview
        Web->>API: Poll notifications [HTTPS/JSON]
        API-->>Web: Notification for Accounting Members (DEC-021)
        Member->>Web: Check final result (file via SAPS API)
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
- Worker actors are idempotent: they lock the invoice row and do nothing if the status is no longer the expected one
  ([ADR-0004](../adr/0004-process-invoices-in-background-worker.md) S2).
- The SAPS Web App polls for status and notifications; push (e.g. WebSocket) can be decided in the feature spec.
- During exception handling an Accounting Member can also reject the invoice ([DEC-014](../../01-requirements/decision-log.md#dec-014)); see the lifecycle.
- The invoice lifecycle (states and transitions) is in [data-model.md §5](../data-model.md#invoice-lifecycle).

## 6.3 Recovery of stuck invoices (sweeper)
**Trigger:** Timer in the SAPS Worker (APScheduler), every few seconds.
**Purpose:** Recover invoices whose message was lost (crash between commit and send, Redis restart) or whose worker
crashed mid-job ([ADR-0004](../adr/0004-process-invoices-in-background-worker.md) S1, verified in spike
[SAPS-34](https://linear.app/jiringuyen/issue/SAPS-34)).

```mermaid
sequenceDiagram
    autonumber
    participant Worker as SAPS Worker
    participant DB as SAPS Database
    participant MQ as SAPS Message Broker

    Worker->>DB: Begin, try advisory lock for the sweeper [SQL]
    alt Lock held by another SAPS Worker instance
        DB-->>Worker: false
        Note over Worker: Skip this tick
    else Lock acquired
        Worker->>DB: Select invoices in Uploaded or Matching older than the limit, FOR UPDATE SKIP LOCKED [SQL]
        Note over DB: Invoices whose job is running are row-locked and skipped
        loop Each stuck invoice
            Worker->>MQ: Send process_invoice if Uploaded, rematch_invoice if Matching [Redis]
            Worker->>DB: Update updated_at, record InvoiceEvent [SQL]
        end
        Worker->>DB: Commit, lock released [SQL]
    end
```

**Related:** [DEC-003](../../01-requirements/decision-log.md#dec-003) to
[DEC-021](../../01-requirements/decision-log.md#dec-021), [ADR-0001](../adr/0001-isolate-extraction-and-erp-behind-ports.md),
[ADR-0004](../adr/0004-process-invoices-in-background-worker.md), [ADR-0006](../adr/0006-store-invoice-files-in-seaweedfs.md).
