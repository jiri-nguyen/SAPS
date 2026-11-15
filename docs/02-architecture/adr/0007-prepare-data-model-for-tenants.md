---
id: ADR-0007
title: "ADR-0007: Prepare the PoC data model for tenants; defer the multi-tenancy model"
status: accepted         # proposed | accepted | rejected | deprecated | superseded
date: 2026-12-05         # date of the latest status change
owner: "Solution Architect (our company)"
deciders: ["Solution Architect (our company)"]
consulted: ["Tech Lead (TBD)"]
last_updated: 2026-12-05
supersedes: ""
superseded_by: ""
related: [DEC-026, NFR-SCAL-001, CON-02, CON-06, ADR-0003, ADR-0005, ADR-0006, SAPS-35]
---

# ADR-0007: Prepare the PoC data model for tenants; defer the multi-tenancy model

## Context and Problem Statement
After the PoC, Smart-AP-Suite serves many customer companies (tenants) on AWS, each with 1,000–2,000 invoices per day
([DEC-026](../../01-requirements/decision-log.md#dec-026)). The PoC serves one company. The current
[data model](../data-model.md) and ADRs assume a single customer.
Choosing the real multi-tenancy model (isolation level, AWS account and infrastructure layout, onboarding, per-tenant
ERP connections) needs requirements that are not known yet, and the Solution Architect wants to analyze it after the PoC.
Adding a tenant identifier to a schema that already holds data and code is expensive; adding it now is cheap.

**Question:** How much multi-tenancy does the PoC build, given that the multi-tenancy model is decided after the PoC?

## Decision Drivers
- Future multi-company system — [DEC-026](../../01-requirements/decision-log.md#dec-026), [NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)
- 3-month PoC; no work that the demo does not need — [CON-02](../arc42/02-constraints.md)
- Keep all later isolation models possible (shared database, schema per tenant, database or account per tenant)
- Avoid a costly schema migration later

## Considered Options
1. Single-tenant PoC: no tenant concept at all
2. Tenant-ready data model: a `Tenant` entity and a `tenant_id` on every tenant-owned table, one default tenant, no isolation enforcement
3. Full multi-tenancy in the PoC: tenant context per request, PostgreSQL row-level security, tenant administration

## Decision Outcome
**Chosen option:** "Tenant-ready data model", because it costs little in the PoC, avoids adding a key to every table
later, and does not commit to any isolation model.

In the PoC:
- New entity `Tenant`; one tenant is seeded by the first migration.
- Every tenant-owned table gets a non-null `tenant_id` (FK → Tenant), including child tables, so that any later model
  (e.g. row-level security) works without back-filling: UserAccount, Invoice, InvoiceLine, InvoiceException, Approval,
  InvoiceEvent, Notification. `MatchingSettings` becomes one row per tenant.
- The duplicate-detection index becomes (`tenant_id`, `vendor_code`, `invoice_number`).
- Application code takes `tenant_id` from the signed-in user's account. With one tenant this is **not** a security
  boundary and is not tested as one.

Not in the PoC, decided in a separate ADR after the PoC:
- Isolation model: shared database with row-level security, schema per tenant, database per tenant, or AWS account per tenant.
- Tenant onboarding and administration; per-tenant ERP / MuleSoft connections and extraction configuration.
- Per-tenant file storage layout (the object key in [ADR-0006](0006-store-invoice-files-in-seaweedfs.md) stays as it is in the PoC),
  per-tenant queues, noisy-neighbor protection, per-tenant data residency and retention.

### Consequences
- **Good:** Every later isolation model starts from data that already carries the tenant.
- **Good:** Matching settings per company come for free.
- **Bad:** A little extra work in the PoC (one table, one column per table, one filter per query).
- **Bad:** A reader may assume the PoC is multi-tenant; it is not (recorded as technical debt TD-02 in arc42 §11).
- **Neutral:** If the post-PoC ADR chooses database or account per tenant, `tenant_id` becomes redundant but harmless.

### Confirmation
- Code review / migration check: every tenant-owned table has a non-null `tenant_id`.
- The post-PoC multi-tenancy ADR references and, where needed, supersedes this ADR.

## Pros and Cons of the Options

### Single-tenant PoC
- Good, because it is the least work now.
- Bad, because every table, query and index needs changing later, with data already in place.

### Tenant-ready data model
- Good, because the expensive part (schema shape) is done early and cheaply.
- Good, because it leaves the isolation model open.
- Bad, because unused columns may look like isolation that does not exist.

### Full multi-tenancy in the PoC
- Good, because isolation could be shown early.
- Bad, because the isolation model would be chosen without the information the Solution Architect wants to gather after the PoC.
- Bad, because the demo does not need it (one company), so it takes time from the 3-month PoC.

## More Information
- Linear: [SAPS-35](https://linear.app/jiringuyen/issue/SAPS-35)
- Customer agreement: not required (internal design decision; follows [DEC-026](../../01-requirements/decision-log.md#dec-026)).
