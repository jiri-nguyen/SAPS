---
id: ADR-0009
title: "ADR-0009: Isolate tenant data in one shared database with tenant_id and row-level security"
status: proposed         # proposed | accepted | rejected | deprecated | superseded
date: 2027-03-01         # date of the latest status change
owner: "Solution Architect (our company)"
deciders: ["Product Owner (Customer)", "Solution Architect (our company)"]
consulted: ["Tech Lead (TBD)"]
last_updated: 2027-03-01
supersedes: ""
superseded_by: ""
related: [DEC-026, DEC-048, DEC-050, DEC-056, NFR-SCAL-001, NFR-MAINT-001, ADR-0003, ADR-0004, ADR-0005, ADR-0007, ADR-0010, TD-02, MTG-20270301-2]
---

# ADR-0009: Isolate tenant data in one shared database with tenant_id and row-level security

## Context and Problem Statement
In Phase 2 the system serves several customer companies (tenants): about 3 in the demo, each with 1,000 invoices per day
and about 30 users in total ([DEC-048](../../01-requirements/decision-log.md#dec-048), [nfr.md](../../01-requirements/nfr.md#2-workload-profile)).
Later the product grows to many companies with 1,000–2,000 invoices per day each, on AWS
([DEC-026](../../01-requirements/decision-log.md#dec-026), [NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)).
A user belongs to exactly one company; matching settings, vendors and ERP data are per company
([DEC-056](../../01-requirements/decision-log.md#dec-056)).

The PoC prepared the data: a `Tenant` entity and a non-null `tenant_id` on every tenant-owned table, but no isolation
enforcement ([ADR-0007](0007-prepare-data-model-for-tenants.md), technical debt [TD-02](../arc42/11-risks-and-technical-debt.md#td-02)).
The Product Owner asked for the options of the database model before deciding
([MTG-20270301-2](../../01-requirements/meetings/2027-03-01-phase-2-requirements.md) Q3).

Information from the Product Owner while preparing the decision (to be recorded in the next minutes):
- The companies are subsidiaries of one group, in several countries; about 3 now, more subsidiaries later.
- No legal or contractual need to keep a subsidiary's data physically apart; no plan to sell or split off a subsidiary;
  no group-wide reporting across subsidiaries; the same retention and infrastructure for all.
- Customers outside the group are a possible later direction, not certain.
- Whether data-residency laws of the countries apply to invoice data is not known
  (see [Assumption](#more-information)).

**Question:** How are the data of the companies kept apart in the SAPS Database?

## Decision Drivers
- One company must never see or change the data of another — [DEC-056](../../01-requirements/decision-log.md#dec-056)
- Subsidiaries of one group: no legal need for physical separation, same retention and infrastructure (Product Owner)
- Possible later: customers outside the group, and data-residency rules per country
- Many companies later without a redesign — [NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001), [DEC-026](../../01-requirements/decision-log.md#dec-026)
- Move to AWS (Amazon RDS for PostgreSQL) after the demo without changing the logic — [NFR-MAINT-001](../../01-requirements/nfr.md#nfr-maint-001)
- 6-month phase with a demo on 2027-08-30; SSO, mailbox intake and multi-tenancy first — [DEC-050](../../01-requirements/decision-log.md#dec-050), [DEC-052](../../01-requirements/decision-log.md#dec-052)
- Reuse what the PoC built: `tenant_id` everywhere, one Alembic history, async SQLAlchemy — [ADR-0005](0005-use-sqlalchemy-and-alembic.md), [ADR-0007](0007-prepare-data-model-for-tenants.md)
- System jobs work across companies (sweeper, [SAPS-37](../../03-features/SAPS-37-stuck-invoice-sweeper.md); worker jobs, [ADR-0004](0004-process-invoices-in-background-worker.md))
- Retention periods are not known yet, but the same for all subsidiaries ([MTG-20270301](../../01-requirements/meetings/2027-03-01-phase-2-kickoff.md) Q10)

## Considered Options
1. Shared database, `tenant_id` filter in the application only (today's code)
2. Shared database, `tenant_id` filter in the application **and** PostgreSQL row-level security (RLS)
3. One schema per company in one database
4. One database per company

## Decision Outcome
**Proposed option:** "Shared database, `tenant_id` filter in the application and PostgreSQL row-level security", because it
builds on the data the PoC already has, keeps one schema and one migration history, scales to many companies with no
per-company infrastructure, and adds a second, database-enforced barrier against a forgotten filter. To be decided with the
Product Owner in the next meeting.

Rules if accepted:
- Every tenant-owned table gets `ENABLE` and `FORCE ROW LEVEL SECURITY` and a policy `tenant_id = current_setting('app.tenant_id')::uuid`.
- The SAPS API and SAPS Worker connect with a role that does not own the tables (RLS applies); each transaction sets the
  company with `SET LOCAL app.tenant_id` (safe with connection pooling, it ends with the transaction).
- The tenant of a request comes from the signed-in user ([ADR-0010](0010-use-one-keycloak-realm-with-company-groups.md));
  worker messages carry the tenant ID next to the invoice ID, and the job sets it for its transaction.
- Jobs that must see every company (the sweeper) use a separate database role with `BYPASSRLS`, only in the SAPS Worker.
- Object keys in file storage get the tenant as a prefix ([ADR-0006](0006-store-invoice-files-in-seaweedfs.md)), so S3 policies can be per company later.
- Tests prove that a query without the setting returns nothing and that one company cannot read another's rows.

### Consequences
- **Good:** No new infrastructure per company; onboarding a company is one `Tenant` row, one Keycloak group and its mailbox.
- **Good:** One Alembic migration path; works the same on local PostgreSQL and on Amazon RDS.
- **Good:** A missing `WHERE tenant_id = …` in code no longer leaks data (closes TD-02).
- **Bad:** All companies share one database: one backup, noisy neighbours share resources; per-company restore needs a filtered export.
- **Bad:** RLS needs care: the setting per transaction, a non-owner role, and a separate role for cross-company jobs.
- **Neutral:** If data-residency rules or customers outside the group appear later, the same stack can be deployed once per region or once per customer group (each deployment uses this model inside); the code does not change, only the deployment ([NFR-MAINT-001](../../01-requirements/nfr.md#nfr-maint-001)).

### Confirmation
- Integration tests on PostgreSQL: cross-company reads and writes are refused for every tenant-owned table; a session without `app.tenant_id` sees no rows.
- Migration check in CI: every tenant-owned table has RLS enabled and forced, with the policy.
- Architecture review against [NFR-MAINT-001](../../01-requirements/nfr.md#nfr-maint-001).

## Pros and Cons of the Options

### Shared database, application filter only
- Good, because it exists already and needs no new work.
- Bad, because one forgotten filter leaks another company's invoices; nothing below the application stops it (TD-02).

### Shared database, application filter and RLS
- Good, because it keeps everything the PoC built and adds a database-enforced barrier.
- Good, because cost and operations do not grow with the number of companies.
- Bad, because per-company backup, restore and deletion are filtered operations, not whole-database ones.
- Bad, because RLS settings and roles must be right; mistakes show up as empty results, so they need tests.

### One schema per company
- Good, because data is separated by schema, and a company can be dumped or dropped as a schema.
- Bad, because every migration runs once per schema, and onboarding creates a schema; the time grows with the number of companies.
- Bad, because each connection must switch `search_path`; a pooled connection with a stale path can reach the wrong company.
- Bad, because cross-company jobs (sweeper) must loop over schemas.

### One database per company
- Good, because it gives the strongest separation: own backup, restore, deletion and, on AWS, possibly own encryption key or instance.
- Bad, because the SAPS API and SAPS Worker need a connection pool per company and a router to pick it; migrations and monitoring run per database.
- Bad, because cost and operations grow with every company (one RDS instance each, or many databases in one instance).
- Bad, because it changes much more code before the demo on 2027-08-30.

## More Information
- Options prepared for [MTG-20270301-2](../../01-requirements/meetings/2027-03-01-phase-2-requirements.md) Q3; the customer agreement will be recorded as a `DEC-*`.
- Related identity decision: [ADR-0010](0010-use-one-keycloak-realm-with-company-groups.md) (one realm with a group per company fits options 1–3).
- > **Assumption:** the countries of the subsidiaries do not require invoice data to stay in the country; if they do, the deployment per region above applies. To be confirmed by the Product Owner with the group legal / IT before the deployment on AWS.
