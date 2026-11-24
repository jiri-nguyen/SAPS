---
id: ADR-0012
title: "ADR-0012: Poll the company mailboxes from the SAPS Worker through a mail port (Microsoft Graph later, IMAP test server for the demo)"
status: accepted         # proposed | accepted | rejected | deprecated | superseded
date: 2027-03-01         # date of the latest status change
owner: "Solution Architect / Tech Lead (our company)"
deciders: ["Solution Architect / Tech Lead (our company)"]
consulted: []
last_updated: 2027-03-01
supersedes: ""
superseded_by: ""
related: [RSK-03, DEC-048, DEC-053, DEC-055, DEC-056, DEC-061, NFR-MAINT-001, NFR-SCAL-001, ADR-0001, ADR-0004, ADR-0006, ADR-0009, SAPS-17, SAPS-37, SAPS-40, SAPS-45]
---

# ADR-0012: Poll the company mailboxes from the SAPS Worker through a mail port (Microsoft Graph later, IMAP test server for the demo)

## Context and Problem Statement
In Phase 2 invoices also arrive by e-mail ([DEC-048](../../01-requirements/decision-log.md#dec-048)). Each company has its
own mailbox; the real mail system later is Outlook (Microsoft 365) of the group. The mailbox that receives a mail sets the
company. PDF, PNG and JPG attachments are taken, one attachment = one invoice; a mail without a valid attachment is skipped
and logged; the sender is not checked in Phase 2 ([DEC-055](../../01-requirements/decision-log.md#dec-055)).
The Phase 2 demo runs locally with Docker Compose and a local test mail server; no real Outlook mailbox is used
([DEC-053](../../01-requirements/decision-log.md#dec-053)). The design must make the real mail system easy to add later
([NFR-MAINT-001](../../01-requirements/nfr.md#nfr-maint-001)).

Today an invoice enters only through `uploadInvoice` (SAPS-17): checks on size and type (magic bytes), storage in SeaweedFS,
an Invoice in status Uploaded, then `process_invoice` ([ADR-0004](0004-process-invoices-in-background-worker.md),
[ADR-0006](0006-store-invoice-files-in-seaweedfs.md)). The sweeper already runs as a timer inside the SAPS Worker
([SAPS-37](../../03-features/SAPS-37-stuck-invoice-sweeper.md)).

**Question:** How does the system read the companies' mailboxes, now with a local test server and later with Outlook, and
how do mail attachments enter the invoice flow?

## Decision Drivers
- One mailbox per company; the mailbox sets the company — [DEC-055](../../01-requirements/decision-log.md#dec-055), [ADR-0009](0009-isolate-tenant-data-in-a-shared-database.md)
- Local test mail server for the demo; Outlook later without changing the intake logic — [DEC-053](../../01-requirements/decision-log.md#dec-053), [NFR-MAINT-001](../../01-requirements/nfr.md#nfr-maint-001)
- The same checks and the same flow as an upload; no second way for a file to become an invoice — SAPS-17
- No mail imported twice and no mail lost when a worker or the broker fails — [ADR-0004](0004-process-invoices-in-background-worker.md) S1, S2
- Nothing must call into the local stack from the internet (no public endpoint in the demo)
- About 3 companies × 1,000 invoices per day; many companies later — [nfr.md](../../01-requirements/nfr.md#2-workload-profile), [NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)

## Considered Options
**How mail is read**
1. **Mail port in the SAPS Worker, polled by a timer:** Microsoft Graph adapter (app-only) for Outlook later, IMAP adapter for the local test server
2. **Microsoft Graph change notifications (push):** Graph calls a public SAPS endpoint when a mail arrives
3. **Mail flow outside the system:** an Outlook rule or a Power Automate flow forwards attachments to an SAPS upload endpoint
4. **IMAP for every mail system**, also for Outlook (IMAP with OAuth 2.0)

**Local test mail server** (for option 1): GreenMail (SMTP and IMAP, mailboxes created on first use) or Mailpit (SMTP with a web UI, no IMAP).

## Decision Outcome
**Chosen option:** "Mail port in the SAPS Worker, polled by a timer", with a **Microsoft Graph adapter** for Outlook later
and an **IMAP adapter** against a **GreenMail** container for the demo, because it keeps the intake logic independent of the
mail system ([ADR-0001](0001-isolate-extraction-and-erp-behind-ports.md) style), needs no public endpoint, reuses the
worker timer of the sweeper, and uses the access Microsoft recommends for Outlook (Graph with OAuth 2.0).

Rules:
- **Mail port** (`MailboxPort`): list new mails of one mailbox, read a mail's attachments, mark a mail as done. Adapters:
  `imap` (demo, tests) and `graph` (Outlook, later). The adapter is chosen by configuration, like `EXTRACTION_ADAPTER`.
- **Which mailbox belongs to which company:** the `Tenant` holds its mailbox address. The worker reads only these mailboxes.
- **Polling:** a timer in each SAPS Worker process, started like the sweeper, every `MAIL_POLL_SECONDS` (default 60 s);
  a PostgreSQL advisory lock per mailbox lets one process read a mailbox at a time.
- **Intake:** each valid attachment goes through the same use case as an upload (size, type by magic bytes, storage,
  Invoice in Uploaded, `process_invoice`); the invoice records the channel `MAIL` and the mail's sender, subject and date.
  The uploader of a mail invoice is the system, not a user (data model change in the feature spec of
  [SAPS-45](https://linear.app/jiringuyen/issue/SAPS-45)).
- **Exactly once:** an `InboundMail` record per mail (tenant, mailbox, the mail system's message ID, status) with a unique
  key; each attachment uses an idempotency key derived from the message ID and the attachment's position, so a retry after a
  crash creates no second invoice. A mail is marked done in the mailbox (moved to a `Processed` folder) only after its
  invoices are committed; a mail found again is skipped by its record.
- **Invalid mails:** no valid attachment → recorded as skipped with the reason, logged, moved to a `Skipped` folder; nobody is
  notified (DEC-055). A file that fails the upload checks is skipped the same way, the other attachments of the mail go on.
- **Graph later:** one app registration in the group's Entra ID with the application permission to read and move mail,
  limited by Exchange to the companies' mailboxes; incremental reading with Graph delta queries; secrets from configuration.
- **Attachments are untrusted input:** the same limits as uploads (size, type by content). Virus scanning is not in Phase 2
  ([RSK-03](../arc42/11-risks-and-technical-debt.md#rsk-03)).

### Consequences
- **Good:** The intake logic does not know whether mail comes from GreenMail or Outlook; switching is a configuration change.
- **Good:** No public endpoint and no subscription to renew; works the same locally and on AWS.
- **Good:** Mail invoices follow exactly the upload path: same checks, duplicate detection, matching and notifications.
- **Bad:** Up to `MAIL_POLL_SECONDS` delay before a mail is read (no target exists; acceptable for invoices).
- **Bad:** The Graph adapter cannot be tested against a real mailbox before the group gives access; it is tested against
  recorded Graph responses until then.
- **Bad:** One more timer and one more table to run and monitor in the worker.
- **Neutral:** Push notifications (option 2) can be added later to shorten the delay, behind the same port.

### Confirmation
- Integration tests with GreenMail (Testcontainers): a mail with two PDFs becomes two invoices of the right company; a mail
  without a valid attachment is skipped and logged; a crash between import and "mark done" creates no second invoice; two
  workers do not read the same mailbox at once.
- Compose smoke test: a test mail sent to the demo mailbox of a company reaches Pending review.
- Graph adapter unit tests against recorded responses; architecture review against NFR-MAINT-001.

## Pros and Cons of the Options

### Mail port, polled by a timer (Graph later, IMAP for the demo)
- Good, because it keeps the mail system behind a port and works without a public endpoint.
- Good, because it reuses the worker timer, the upload use case and the advisory-lock pattern of the sweeper.
- Bad, because two adapters exist and only the IMAP one runs in the demo.

### Graph change notifications (push)
- Good, because mails are read within seconds.
- Bad, because Graph must reach a public HTTPS endpoint of the SAPS API; the local demo has none.
- Bad, because subscriptions expire after a few days and must be renewed; missed notifications still need a polling fallback.

### Mail flow outside the system (Outlook rule, Power Automate)
- Good, because the SAPS API only receives files over HTTPS.
- Bad, because the intake depends on flows configured in the group's Microsoft 365 that the team does not control or test.
- Bad, because it also needs a public endpoint and its own authentication for each flow.

### IMAP for every mail system
- Good, because one adapter covers the demo and Outlook.
- Bad, because Microsoft recommends Graph for Exchange Online; IMAP there needs OAuth 2.0 setup per mailbox and gives no delta reading.

## More Information
- Linear: [SAPS-40](https://linear.app/jiringuyen/issue/SAPS-40); implementation and data model: feature spec of [SAPS-45](https://linear.app/jiringuyen/issue/SAPS-45).
- Accepted by the Solution Architect / Tech Lead on 2027-03-01, with `MAIL_POLL_SECONDS` = 60 s and risk [RSK-03](../arc42/11-risks-and-technical-debt.md#rsk-03).
- Customer agreement: not required (implements [DEC-055](../../01-requirements/decision-log.md#dec-055)); the Graph app registration needs the group IT later.
