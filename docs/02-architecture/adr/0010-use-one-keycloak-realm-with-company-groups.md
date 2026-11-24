---
id: ADR-0010
title: "ADR-0010: Use one Keycloak realm with a group per company; broker Microsoft Entra ID later"
status: proposed         # proposed | accepted | rejected | deprecated | superseded
date: 2027-03-01         # date of the latest status change
owner: "Solution Architect (our company)"
deciders: ["Product Owner (Customer)", "Solution Architect (our company)"]
consulted: ["Tech Lead (TBD)"]
last_updated: 2027-03-01
supersedes: ""
superseded_by: ""
related: [DEC-026, DEC-049, DEC-053, DEC-054, DEC-056, NFR-SEC-001, NFR-MAINT-001, ADR-0008, ADR-0009, MTG-20270301-2]
---

# ADR-0010: Use one Keycloak realm with a group per company; broker Microsoft Entra ID later

## Context and Problem Statement
Single Sign-On uses Keycloak ([DEC-049](../../01-requirements/decision-log.md#dec-049)). For the Phase 2 demo the team runs
Keycloak in Docker Compose ([DEC-053](../../01-requirements/decision-log.md#dec-053)) and manages users, their company and
their roles in the Keycloak admin console ([DEC-054](../../01-requirements/decision-log.md#dec-054)); no real Entra ID is
used for the demo. Each user belongs to exactly one company ([DEC-056](../../01-requirements/decision-log.md#dec-056)).

Information from the Product Owner while preparing the decision (to be recorded in the next minutes):
- The companies are subsidiaries of one group, in several countries; about 3 now, more subsidiaries later.
- All subsidiaries sign in with **one shared Microsoft Entra ID** of the group; each subsidiary has its own e-mail domain
  (for example `vn.xxx.com`, `sg.xxx.com`).
- Integration with Entra ID is expected in a later phase. Customers outside the group are a possible later direction, not certain.

In Keycloak a **realm** is a separate space of users, roles, clients, sign-in settings and identity providers. Keycloak can
**broker** an external identity provider such as Entra ID: users sign in at Entra ID, Keycloak still issues the tokens to the
SAPS Web App and SAPS API. Keycloak 26 also offers **Organizations** (several companies in one realm, each linked to its own
identity provider and domains).

**Question:** How are the companies represented in Keycloak, so that the SAPS API knows the company of every user, now
with local users and later with the group's Entra ID?

## Decision Drivers
- A user belongs to exactly one company; the SAPS API must know it reliably — [DEC-056](../../01-requirements/decision-log.md#dec-056), [ADR-0009](0009-isolate-tenant-data-in-a-shared-database.md)
- The team assigns company and role in the admin console now — [DEC-054](../../01-requirements/decision-log.md#dec-054)
- One shared Entra ID for all subsidiaries later, without changing the SAPS code — [NFR-MAINT-001](../../01-requirements/nfr.md#nfr-maint-001)
- One sign-in page and one SAPS Web App URL for every subsidiary
- More subsidiaries later; customers outside the group possible — [DEC-026](../../01-requirements/decision-log.md#dec-026), [NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)

## Considered Options
1. One realm; one group per company, roles as realm roles
2. One realm with Keycloak Organizations (one organization per company)
3. One realm per company

## Decision Outcome
**Proposed option:** "One realm; one group per company", because one shared Entra ID cannot be split into one identity
provider per company, so the main strength of Organizations and of realms per company does not apply; a group per company
is the simplest model the team can manage in the admin console, and later Entra ID groups can fill the same Keycloak groups
with a built-in mapper. To be decided with the Product Owner in the next meeting.

Rules if accepted:
- One realm `saps`; one client for the SAPS Web App / SAPS API.
- One group per company under `/companies` (for example `/companies/vn`); the `Tenant` row stores the group path and the
  company's e-mail domains. The token carries the groups (group membership mapper).
- Roles `ACCOUNTING_MEMBER` and `ACCOUNTING_MANAGER` are realm roles.
- The SAPS API accepts a user only if the token has exactly one company group that matches a known tenant **and** the
  user's e-mail domain belongs to that tenant; otherwise `403` (protects against a wrong group assignment).
- The SAPS code uses only standard OpenID Connect (issuer, signature, claims); no Keycloak-specific API. Claim names are
  configuration.
- How the SAPS Web App signs in (keeping the HttpOnly session cookie of [ADR-0008](0008-use-session-cookies-for-authentication.md)
  through the SAPS API, or tokens in the browser) is a separate ADR.

**Later, with Entra ID (configuration in Keycloak only):**
1. Add the group's Entra ID to the realm as an OpenID Connect identity provider; users sign in with their Entra accounts.
2. Either the team keeps assigning company and role in Keycloak, or Entra ID security groups are mapped to the Keycloak
   company groups and roles with Keycloak's claim-to-group and claim-to-role mappers.
3. Existing local users are linked to their Entra accounts by e-mail on first sign-in.
The SAPS API keeps receiving tokens from the same Keycloak issuer, so its code does not change.

### Consequences
- **Good:** Simple to set up and to manage for 3 subsidiaries; works with any Keycloak version.
- **Good:** Moving to Entra ID later is a Keycloak configuration change, not a code change.
- **Good:** The e-mail domain check catches a user put into the wrong company group.
- **Bad:** Company assignment is manual until Entra ID groups are mapped.
- **Bad:** If customers outside the group come later, each with its own identity provider, Organizations may be the better
  model then; that would be a new ADR (the SAPS code only reads "the company of the token", so the change stays in Keycloak
  and in the claim configuration).
- **Neutral:** All companies share realm settings (password policy, session length, theme); acceptable for one group.

### Confirmation
- Integration test: a user of company A cannot read data of company B; a token with no or two company groups, or with an
  e-mail domain of another company, is refused.
- The realm export used for the demo is kept in the repository and reviewed against these rules.

## Pros and Cons of the Options

### One realm; group per company
- Good, because it is the simplest model and fits one shared identity provider.
- Good, because Entra ID groups can later be mapped onto the same groups with built-in mappers.
- Bad, because a wrong group assignment would give a user another company (mitigated by the e-mail domain check).

### One realm with Keycloak Organizations
- Good, because it is Keycloak's model for many companies in one realm, with per-company identity providers and domains.
- Bad, because one shared Entra ID does not fit "one identity provider per organization"; the extra concepts bring no benefit for one group.
- Neutral, because it becomes interesting if customers outside the group, each with its own identity provider, are added.

### One realm per company
- Good, because it gives full separation per company.
- Bad, because the same Entra ID would have to be configured in every realm, and the Web App must know the company before sign-in.
- Bad, because every new subsidiary needs a new realm configured the same way; more admin work and drift risk.

## More Information
- Options prepared for [MTG-20270301-2](../../01-requirements/meetings/2027-03-01-phase-2-requirements.md) Q2; the customer agreement will be recorded as a `DEC-*`.
- > **Assumption:** the e-mail domain of a user identifies the subsidiary (one domain per subsidiary). To be confirmed by the Product Owner with the group IT.
- [NFR-SEC-001](../../01-requirements/nfr.md#nfr-sec-001) ("simple user accounts") needs a new version once SSO is decided in detail.
