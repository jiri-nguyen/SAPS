---
id: ADR-0013
title: "ADR-0013: Post invoices to the ERP through a posting port in a separate worker job"
status: proposed         # proposed | accepted | rejected | deprecated | superseded
date: 2027-03-01         # date of the latest status change
owner: "Solution Architect / Tech Lead (our company)"
deciders: ["Solution Architect / Tech Lead (our company)"]
consulted: []
last_updated: 2027-03-01
supersedes: ""
superseded_by: ""
related: [DEC-063, DEC-064, DEC-067, NFR-MAINT-001, NFR-SCAL-001, ADR-0001, ADR-0004, SAPS-37, SAPS-38, SAPS-48, SAPS-49]
---

# ADR-0013: Post invoices to the ERP through a posting port in a separate worker job

## Context and Problem Statement
Invoices are now posted to the ERP through MuleSoft at the end of the workflow, without a final review
([DEC-063](../../01-requirements/decision-log.md#dec-063)). MuleSoft and the ERP do not exist yet; until then a mock answers
"ok" ([DEC-064](../../01-requirements/decision-log.md#dec-064)). The real adapter must replace the mock without changes to
the workflow ([NFR-MAINT-001](../../01-requirements/nfr.md#nfr-maint-001)).

Processing runs in the SAPS Worker with Dramatiq and PostgreSQL ([ADR-0004](0004-process-invoices-in-background-worker.md)):
one transaction per job, idempotent actors, retries with back-off, and a sweeper that re-sends lost messages for invoices
stuck in Uploaded or Matching ([SAPS-37](../../03-features/SAPS-37-stuck-invoice-sweeper.md)). A posting is a call to
another system that has effects outside our database: it must happen once per invoice, also when a worker stops, a message is
delivered twice or the ERP answers after our transaction failed.

**Question:** Where and how does the system call the ERP to post an invoice, so that each invoice is posted exactly once and
the mock can be replaced by MuleSoft later?

## Decision Drivers
- Each invoice is posted once; a retry never creates a second ERP document — [DEC-064](../../01-requirements/decision-log.md#dec-064)
- No call to another system inside a database transaction that may roll back — [ADR-0004](0004-process-invoices-in-background-worker.md) S2
- The mock is replaced by MuleSoft without changes to the workflow — [NFR-MAINT-001](../../01-requirements/nfr.md#nfr-maint-001), [ADR-0001](0001-isolate-extraction-and-erp-behind-ports.md)
- Recovery with the mechanisms that exist (retries, sweeper); no new infrastructure for the demo — [DEC-053](../../01-requirements/decision-log.md#dec-053)
- About 1,000 invoices per day per company — [NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)

## Considered Options
1. **Separate `post_invoice` job with a Posting status:** matching commits the invoice in status Posting and sends
   `post_invoice`; that job calls the posting port with the invoice ID as idempotency key and sets Posted.
2. **Post inside the matching job:** after the checks pass, the matching job calls the ERP and sets Posted in the same
   transaction.
3. **Transactional outbox table:** matching writes a posting request row; a relay process reads the table and calls the ERP.

## Decision Outcome
**Chosen option:** "Separate `post_invoice` job with a Posting status", because it keeps the external call out of the
matching transaction, gives a visible state for invoices waiting for the ERP, and reuses Dramatiq retries and the sweeper for
recovery, so no new process or table is needed.

Rules:
- **ERP posting port** (`ErpPostingPort.post(company_code, request) → result`): the request carries the invoice ID as
  idempotency key, the header, and the lines with PO, PO line and matched lot. The result carries the ERP document number.
  Adapters: `mock` now, `mulesoft` later ([SAPS-48](https://linear.app/jiringuyen/issue/SAPS-48)), chosen by
  `ERP_POSTING_ADAPTER`.
- **Statuses:** Matching or Pending approval → **Posting** → **Posted**. The message is sent after the commit; a failed send
  leaves the invoice in Posting.
- **The `post_invoice` actor** locks the invoice; anything but Posting → no change (idempotent). It calls the port outside
  any open transaction, then sets Posted, the document number and the posting time in a new transaction.
- **Exactly once:** the adapter passes the idempotency key to the ERP side; the MuleSoft API must return the same document
  for the same key. The mock derives the document number from the invoice ID.
- **Recovery:** Dramatiq retries a failing call with back-off; the sweeper also re-sends `post_invoice` for invoices in
  Posting older than `SWEEPER_STUCK_AFTER_SECONDS`, with the same re-send limit.
- **API removal without `/v2`:** `confirmInvoice` is removed and `resolveInvoiceExceptions` answers `202` in API 0.10.0.
  The only client is the SAPS Web App, released together with the SAPS API; the API is pre-1.0.

### Consequences
- **Good:** A failed or slow ERP never rolls back a matching result; the invoice simply waits in Posting.
- **Good:** Replacing the mock by MuleSoft is a new adapter and a configuration value.
- **Good:** Users see which invoices wait for the ERP (status Posting) in All invoices.
- **Bad:** Exactly once depends on the ERP side honoring the idempotency key; this is a requirement for the MuleSoft API
  ([SAPS-48](https://linear.app/jiringuyen/issue/SAPS-48)).
- **Bad:** One more actor and one more status to test and to cover in the sweeper.
- **Neutral:** A posting the ERP rejects for business reasons needs a new exception type ("Posting failed"), built with the
  MuleSoft adapter (DEC-064).

### Confirmation
- Integration tests: an invoice in Posting is posted once when `post_invoice` runs twice; a stop between the ERP answer and
  the commit is recovered by the sweeper with the same document number; a closed day leaves it in Posting.
- Compose smoke test: DS-01 reaches Posted with a mock document number.
- Architecture test: the workflow imports only the port, not an adapter (import-linter).

## Pros and Cons of the Options

### Separate `post_invoice` job with a Posting status
- Good, because the external call is outside the matching transaction and recovery uses existing mechanisms.
- Good, because the waiting state is visible to users and operators.
- Bad, because a posting takes one more message and job.

### Post inside the matching job
- Good, because it is the shortest path; no extra status.
- Bad, because a rollback after the ERP answered leaves a posted document without a Posted invoice; a retry would post again
  unless the ERP is idempotent.
- Bad, because a slow ERP holds the PO line locks of matching (SAPS-19 EC-02) and blocks other invoices.

### Transactional outbox table
- Good, because the request is stored in the same transaction as the matching result and never lost.
- Bad, because it needs a new table and a relay process; the status Posting with the sweeper already gives the same
  guarantee here, since the invoice row itself is the record of the pending posting.

## More Information
- Feature spec: [SAPS-49](../../03-features/SAPS-49-straight-through-posting.md); Linear [SAPS-49](https://linear.app/jiringuyen/issue/SAPS-49).
- Customer agreement: not required (implements [DEC-063](../../01-requirements/decision-log.md#dec-063) and [DEC-064](../../01-requirements/decision-log.md#dec-064)).
