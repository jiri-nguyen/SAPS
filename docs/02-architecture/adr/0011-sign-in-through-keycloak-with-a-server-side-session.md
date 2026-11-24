---
id: ADR-0011
title: "ADR-0011: Sign in through Keycloak in the SAPS API and keep a server-side session cookie"
status: accepted         # proposed | accepted | rejected | deprecated | superseded
date: 2027-03-01         # date of the latest status change
owner: "Solution Architect / Tech Lead (our company)"
deciders: ["Solution Architect / Tech Lead (our company)"]
consulted: []
last_updated: 2027-03-01
supersedes: "ADR-0008"
superseded_by: ""
related: [DEC-049, DEC-053, DEC-054, DEC-059, DEC-061, NFR-SEC-001, NFR-MAINT-001, ADR-0007, ADR-0008, ADR-0009, ADR-0010, SAPS-39, SAPS-43, SAPS-44]
---

# ADR-0011: Sign in through Keycloak in the SAPS API and keep a server-side session cookie

## Context and Problem Statement
In the PoC the SAPS API checks a username and password itself and keeps a server-side session whose ID travels in an
HttpOnly cookie ([ADR-0008](0008-use-session-cookies-for-authentication.md)). In Phase 2 users sign in through Keycloak
([DEC-049](../../01-requirements/decision-log.md#dec-049)): one realm, one group per company, realm roles Accounting Member
and Accounting Manager, the company checked against the e-mail domain
([ADR-0010](0010-use-one-keycloak-realm-with-company-groups.md), [DEC-059](../../01-requirements/decision-log.md#dec-059)).
The group's Microsoft Entra ID is brokered by Keycloak later ([DEC-061](../../01-requirements/decision-log.md#dec-061)).
Users and roles are managed in the Keycloak admin console; the Web App has no user screens
([DEC-054](../../01-requirements/decision-log.md#dec-054)).

The only interactive client is still the SAPS Web App, a React single-page application served from the same origin as
the SAPS API. Every request must carry the user's company for row-level security ([ADR-0009](0009-isolate-tenant-data-in-a-shared-database.md)).

**Question:** How does the SAPS Web App sign users in with Keycloak, and how does the SAPS API know the user, the company
and the role of every request?

## Decision Drivers
- Single Sign-On with Keycloak, later Entra ID behind it, without SAPS code changes — [DEC-049](../../01-requirements/decision-log.md#dec-049), [ADR-0010](0010-use-one-keycloak-realm-with-company-groups.md), [NFR-MAINT-001](../../01-requirements/nfr.md#nfr-maint-001)
- No credential readable by JavaScript (token theft through XSS), as in the PoC — [ADR-0008](0008-use-session-cookies-for-authentication.md)
- The company and the role of every request come from Keycloak and are checked by the SAPS API — [DEC-059](../../01-requirements/decision-log.md#dec-059), [ADR-0009](0009-isolate-tenant-data-in-a-shared-database.md)
- A user removed or deactivated in Keycloak loses access within minutes
- Keep what works: same-origin Web App, Origin check against CSRF, session timeouts, the `401` → sign-in page behaviour
- Demo on 2027-08-30; few new moving parts — [DEC-052](../../01-requirements/decision-log.md#dec-052)

## Considered Options
1. **Backend for frontend (BFF):** the SAPS API is a confidential OpenID Connect client of Keycloak; the browser only holds the HttpOnly session cookie
2. **Tokens in the browser:** the Web App is a public client (Authorization Code with PKCE) and sends the access token as a bearer token to the SAPS API
3. **Authenticating reverse proxy** (for example oauth2-proxy) in front of the SAPS API, passing the user in HTTP headers

## Decision Outcome
**Chosen option:** "Backend for frontend", because it keeps every token out of the browser, keeps the session, cookie
and CSRF rules of the PoC that are already built and tested, and needs no extra component.

Rules:
- **Sign-in:** the Web App sends the user to `/v1/session/sign-in`; the SAPS API starts the Authorization Code flow with
  PKCE, `state` and `nonce` and redirects to Keycloak. Keycloak returns to `/v1/session/callback`; the SAPS API exchanges
  the code with its client secret, validates the ID token (signature from the realm's JWKS, issuer, audience, expiry,
  `nonce`) and creates the session. The exact operations are specified in the feature spec of [SAPS-44](https://linear.app/jiringuyen/issue/SAPS-44).
- **Who the user is:** subject (`sub`) and issuer identify the user; e-mail, name, company group and realm roles come from
  the token. The user is accepted only with exactly one company group of a known tenant, an e-mail domain of that tenant
  and exactly one of the two roles; otherwise sign-in ends with `403` and no session ([ADR-0010](0010-use-one-keycloak-realm-with-company-groups.md)).
  Claim names (groups, roles) are configuration; no Keycloak-specific API is called.
- **User record:** the SAPS Database keeps a `UserAccount` per person (needed for display names, claims, approvals and
  history), created or updated at each sign-in from the token, keyed by issuer and subject. The password hash of the PoC
  is removed; there are no passwords in the SAPS Database.
- **Session (kept from ADR-0008):** random 256-bit session ID in cookie `saps_session` (`HttpOnly`, `SameSite=Lax`, `Path=/`,
  `Secure` over HTTPS); only its hash is stored; idle timeout 30 min and absolute timeout 8 h (configurable); Origin check
  on every state-changing request. The session stores the user, company and role, and the refresh token encrypted at rest;
  tokens never reach the browser.
- **Staying current with Keycloak:** when the access token of the session has expired, the next request refreshes it at
  Keycloak; a refused refresh (user disabled, session ended in Keycloak) ends the SAPS session with `401`. Role or company
  changes therefore apply within one access-token lifetime (Keycloak default 5 min). Keycloak back-channel logout to
  `/v1/session/backchannel-logout` ends SAPS sessions at once when an administrator signs a user out.
- **Sign-out:** `deleteSession` ends the SAPS session and sends the browser to Keycloak's end-session endpoint, so the
  Keycloak session ends too.
- **Hostnames:** the browser reaches Keycloak at its public URL, the SAPS API at an internal URL; the token issuer is the
  public URL (Keycloak hostname settings). On AWS only these URLs change ([NFR-MAINT-001](../../01-requirements/nfr.md#nfr-maint-001)).
- **Other clients later** (partners, tools) may use bearer tokens from Keycloak; that is a separate decision.

### Consequences
- **Good:** No token in the browser; the PoC's cookie, session and CSRF protection stay and keep their tests.
- **Good:** The SAPS API is a standard OpenID Connect client; putting Entra ID behind Keycloak changes nothing in the SAPS code.
- **Good:** Disabling a user in Keycloak removes access within minutes, or at once with back-channel logout.
- **Bad:** The SAPS API must store refresh tokens (encrypted) and handle the redirect flow, `state`, `nonce` and PKCE; a
  maintained OpenID Connect client library is used rather than hand-written code.
- **Bad:** Each SAPS API instance must reach Keycloak (token, JWKS); Keycloak down means no new sign-ins, while existing
  sessions continue until their access token needs a refresh.
- **Neutral:** Tests need a token issuer: unit and integration tests use a local test issuer with its own keys; the compose
  smoke test signs in through the real Keycloak container ([SAPS-43](https://linear.app/jiringuyen/issue/SAPS-43)).

### Confirmation
- Integration tests: a valid callback creates a session with the right company and role; wrong `state`, `nonce`, issuer,
  audience or signature are refused; no or two company groups, a foreign e-mail domain or no role give `403`; a refused
  refresh gives `401`; back-channel logout ends the session.
- The PoC tests for cookie flags, Origin check and timeouts still pass.
- Compose smoke test: sign-in through Keycloak for a member and a manager of two companies.

## Pros and Cons of the Options

### Backend for frontend
- Good, because no token is exposed to JavaScript and the PoC session model stays.
- Good, because it is the pattern recommended for browser-based apps that have their own backend.
- Bad, because the SAPS API keeps state (sessions, refresh tokens) and must reach Keycloak.

### Tokens in the browser
- Good, because the SAPS API stays stateless and only validates bearer tokens.
- Bad, because access and refresh tokens live in the browser, where an XSS bug can steal them.
- Bad, because the cookie and CSRF model of the PoC is replaced, and silent token renewal in the browser is fragile with third-party cookie blocking.

### Authenticating reverse proxy
- Good, because the SAPS API code barely changes.
- Bad, because it adds a component to run and secure, and the SAPS API must trust headers set by the proxy.
- Bad, because company and role checks move partly outside the SAPS API and are harder to test.

## More Information
- Supersedes [ADR-0008](0008-use-session-cookies-for-authentication.md) (sign-in with passwords); its cookie, session and
  CSRF rules are carried over above.
- Accepted by the Solution Architect / Tech Lead on 2027-03-01 together with the new version of
  [NFR-SEC-001](../../01-requirements/nfr.md#nfr-sec-001) (Single Sign-On instead of simple accounts).
- Customer agreement: not required (implements [DEC-049](../../01-requirements/decision-log.md#dec-049)).
- References: OAuth 2.0 for Browser-Based Applications (IETF draft, backend-for-frontend pattern); OpenID Connect Core and
  RP-Initiated Logout; OWASP Session Management and CSRF Prevention Cheat Sheets.
- Linear: [SAPS-39](https://linear.app/jiringuyen/issue/SAPS-39).
