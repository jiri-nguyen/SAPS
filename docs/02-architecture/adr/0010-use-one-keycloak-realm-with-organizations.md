---
id: ADR-0010
title: "ADR-0010: Use one Keycloak realm with Keycloak Organizations for the companies"
status: proposed         # proposed | accepted | rejected | deprecated | superseded
date: 2027-03-01         # date of the latest status change
owner: "Solution Architect (our company)"
deciders: ["Product Owner (Customer)", "Solution Architect (our company)"]
consulted: ["Tech Lead (TBD)"]
last_updated: 2027-03-01
supersedes: ""
superseded_by: ""
related: [DEC-049, DEC-053, DEC-054, DEC-055, DEC-056, NFR-SEC-001, NFR-MAINT-001, ADR-0008, ADR-0009, MTG-20270301-2]
---

# ADR-0010: Use one Keycloak realm with Keycloak Organizations for the companies

## Context and Problem Statement
Single Sign-On uses Keycloak ([DEC-049](../../01-requirements/decision-log.md#dec-049)). For the Phase 2 demo the team runs
Keycloak in Docker Compose ([DEC-053](../../01-requirements/decision-log.md#dec-053)); users and roles are managed in the
Keycloak admin console, with no user screens in the Web App ([DEC-054](../../01-requirements/decision-log.md#dec-054)).
About 3 companies and about 30 users take part in the demo; each user belongs to exactly one company
([DEC-056](../../01-requirements/decision-log.md#dec-056)). The companies use Outlook (Microsoft 365) for mail
([DEC-055](../../01-requirements/decision-log.md#dec-055)), so they may later want to sign in with their own Microsoft accounts.

In Keycloak a **realm** is a separate space of users, roles, clients, sign-in settings and identity providers. Since
Keycloak 26, **Organizations** let one realm hold several companies: each organization has members, can be linked to the
company's own identity provider and e-mail domains, and the access token can carry the user's organization.

The Product Owner asked for the options before deciding ([MTG-20270301-2](../../01-requirements/meetings/2027-03-01-phase-2-requirements.md) Q2).

**Question:** How are the companies represented in Keycloak: one realm for all, or one realm per company?

## Decision Drivers
- A user belongs to exactly one company; the SAPS API must know the company of every request reliably — [DEC-056](../../01-requirements/decision-log.md#dec-056), [ADR-0009](0009-isolate-tenant-data-in-a-shared-database.md)
- Users and roles managed by the team in the admin console; little work per new company — [DEC-054](../../01-requirements/decision-log.md#dec-054)
- Later: a company may sign in with its own Microsoft account (assumption, see More Information) — [NFR-MAINT-001](../../01-requirements/nfr.md#nfr-maint-001)
- One sign-in page and one SAPS Web App URL for every company in the demo
- Many companies later without new infrastructure per company — [NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)

## Considered Options
1. One realm; the company is a group or a user attribute
2. One realm with Keycloak Organizations (one organization per company)
3. One realm per company

## Decision Outcome
**Proposed option:** "One realm with Keycloak Organizations", because it gives one sign-in page and one client for all
companies, puts the company into the token through a built-in feature instead of custom mappers, and keeps the door open
for each company's own identity provider later, without the operations of many realms. To be decided with the Product
Owner in the next meeting.

Rules if accepted:
- One realm `saps`; one organization per company; the `Tenant` row stores the organization ID.
- Roles `ACCOUNTING_MEMBER` and `ACCOUNTING_MANAGER` are realm roles, assigned in the admin console.
- The SAPS API accepts a user only if the token names exactly one organization that matches a known tenant; otherwise `403`.
- How the SAPS Web App signs in with Keycloak (keeping the HttpOnly session cookie of [ADR-0008](0008-use-session-cookies-for-authentication.md)
  through the SAPS API, or tokens in the browser) is a separate ADR.

### Consequences
- **Good:** One Keycloak configuration, one client, one sign-in page; adding a company is one organization plus its users.
- **Good:** The company comes from a supported token claim; no custom group-to-claim mapping.
- **Good:** Later, an organization can be linked to the company's Microsoft Entra ID and e-mail domain, so its users sign in with their own accounts.
- **Bad:** All companies share realm-wide settings (password policy, session length, theme); per-company differences need extra work.
- **Bad:** Organizations require Keycloak 26 or later; the team must learn the feature.
- **Neutral:** Keycloak administrators see users of all companies (acceptable: only the team administers, [DEC-054](../../01-requirements/decision-log.md#dec-054)).

### Confirmation
- Integration test: a user of company A cannot read data of company B; a token without exactly one organization is refused.
- Review of the realm export (kept in the repository for the demo) against these rules.

## Pros and Cons of the Options

### One realm; company as group or attribute
- Good, because it works on any Keycloak version and is simple to set up.
- Bad, because the company claim needs custom mappers; a wrong group assignment silently gives a user another company.
- Bad, because linking a company's own identity provider later needs custom routing.

### One realm with Keycloak Organizations
- Good, because it is Keycloak's built-in model for several companies in one realm, including per-company identity providers and domains.
- Good, because it matches a shared database with `tenant_id` ([ADR-0009](0009-isolate-tenant-data-in-a-shared-database.md)).
- Bad, because all companies share realm settings, and the feature is newer than realms and groups.

### One realm per company
- Good, because it gives full separation: own users, settings, theme, identity provider and administrators per company.
- Bad, because the SAPS Web App must know the company before sign-in (a URL or sub-domain per company, or a company picker), and the SAPS API must trust several issuers.
- Bad, because every new company needs a new realm configured the same way (clients, roles, mappers); more admin work and drift risk.
- Bad, because many realms make Keycloak heavier to run and to upgrade as the number of companies grows.

## More Information
- Options prepared for [MTG-20270301-2](../../01-requirements/meetings/2027-03-01-phase-2-requirements.md) Q2; the customer agreement will be recorded as a `DEC-*`.
- > **Assumption:** the companies may later sign in with their own Microsoft 365 / Entra ID accounts (they use Outlook). To be confirmed by the Product Owner.
- [NFR-SEC-001](../../01-requirements/nfr.md#nfr-sec-001) ("simple user accounts") needs a new version once SSO is decided in detail.
