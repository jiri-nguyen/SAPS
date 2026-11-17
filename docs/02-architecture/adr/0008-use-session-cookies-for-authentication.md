---
id: ADR-0008
title: "ADR-0008: Use server-side sessions in HttpOnly cookies for PoC authentication"
status: accepted         # proposed | accepted | rejected | deprecated | superseded
date: 2026-12-05         # date of the latest status change
owner: "Solution Architect / Tech Lead (our company)"
deciders: ["Solution Architect / Tech Lead (our company)"]
consulted: []
last_updated: 2026-12-05
supersedes: ""
superseded_by: ""
related: [NFR-SEC-001, SCP-OUT-10, CON-01, CON-02, DEC-026, ADR-0003, ADR-0007]
---

# ADR-0008: Use server-side sessions in HttpOnly cookies for PoC authentication

## Context and Problem Statement
In the PoC, users sign in with simple user accounts; Single Sign-On is out of scope
([NFR-SEC-001](../../01-requirements/nfr.md#nfr-sec-001), [SCP-OUT-10](../../01-requirements/scope.md#4-out-of-scope)).
The only client of the SAPS API is the SAPS Web App, a React single-page application served from the same site.
The company OpenAPI template defaults to bearer JWTs issued by an identity provider, but the PoC has no identity
provider and runs locally ([CON-01](../arc42/02-constraints.md)). After the PoC the product serves many companies on
AWS ([DEC-026](../../01-requirements/decision-log.md#dec-026)) and will probably use an identity provider.

**Question:** How does the SAPS Web App authenticate its calls to the SAPS API in the PoC?

## Decision Drivers
- Simple user accounts, no SSO — [NFR-SEC-001](../../01-requirements/nfr.md#nfr-sec-001)
- Credentials must not be readable by JavaScript (protection against token theft through XSS)
- Sign-out and deactivated users take effect immediately
- 3-month PoC; few moving parts — [CON-02](../arc42/02-constraints.md)
- Do not block an identity provider (SSO, JWT) after the PoC — [DEC-026](../../01-requirements/decision-log.md#dec-026)
- Tenant comes from the signed-in user — [ADR-0007](0007-prepare-data-model-for-tenants.md)

## Considered Options
1. Server-side session, session ID in an HttpOnly cookie
2. JWT access token issued by the SAPS API, with a refresh token
3. External identity provider (e.g. Amazon Cognito) already in the PoC

## Decision Outcome
**Chosen option:** "Server-side session, session ID in an HttpOnly cookie", because JavaScript cannot read the
credential, sessions can be revoked at once, and it is the simplest secure option for a single same-site browser client.

Rules:
- `createSession` checks the password (Argon2id hash) and sets cookie `saps_session`: random 256-bit value,
  `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` whenever served over HTTPS (configurable; off only for local HTTP).
- Sessions are stored in the SAPS Database (entity `UserSession`); only a hash of the cookie value is stored.
  A new session is created at every sign-in; `deleteSession` revokes it.
- Idle timeout and absolute timeout are configurable (defaults 30 min and 8 h, chosen by the Solution Architect).
- **CSRF protection:** in addition to `SameSite=Lax`, every state-changing request (POST, PUT, PATCH, DELETE) must carry an
  `Origin` header that matches the configured SAPS Web App origin; otherwise the SAPS API returns `403`.
- The SAPS Web App and the SAPS API are served from the same origin (Vite dev proxy locally; one origin in Docker Compose).
- The tenant of a request is the tenant of the session's user (ADR-0007).

### Consequences
- **Good:** No token in JavaScript-accessible storage; XSS cannot steal the credential.
- **Good:** Immediate sign-out and user deactivation.
- **Good:** No key management or refresh-token flow in the PoC.
- **Bad:** CSRF must be handled explicitly (SameSite plus Origin check).
- **Bad:** One session lookup per request (an indexed query; negligible at PoC volume).
- **Bad:** Only suitable for browser clients on the same site; other clients (mailbox intake, partners, MCP tools) need tokens later.
- **Neutral:** After the PoC, an identity provider can be introduced; the SPA can keep a cookie (backend-for-frontend
  pattern) while other clients use JWTs. That change needs a new ADR that supersedes this one.

### Confirmation
- Integration tests: cookie flags are set; a state-changing request with a foreign `Origin` gets `403`; a revoked or
  expired session gets `401`.
- Demo scenario DS-19 (sign-in and role access) passes.
- The OpenAPI security scheme `sessionCookie` references this ADR.

## Pros and Cons of the Options

### Server-side session in an HttpOnly cookie
- Good, because the credential is not readable by JavaScript.
- Good, because sessions are revocable at once.
- Bad, because it needs CSRF protection and works only for same-site browser clients.

### JWT issued by the SAPS API, with a refresh token
- Good, because it is stateless and works for any client.
- Bad, because a token in localStorage can be stolen through XSS; keeping it in memory needs a refresh token, usually in a cookie anyway.
- Bad, because revocation needs a deny list, and signing keys must be managed.

### External identity provider already in the PoC
- Good, because it is closest to the expected production setup.
- Bad, because SSO is out of the PoC scope (SCP-OUT-10) and the PoC runs locally without cloud services (CON-01).

## More Information
- Customer agreement: not required (within NFR-SEC-001).
- OWASP Session Management and CSRF Prevention Cheat Sheets are the reference for the cookie and Origin rules.
