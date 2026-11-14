---
title: "§8 Cross-cutting Concepts"
status: draft            # draft | in-review | approved | deprecated
owner: "{{Solution Architect}}"
reviewers: ["{{Tech Lead}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: arc42 §8 Cross-cutting Concepts
Copy to: docs/02-architecture/arc42/08-crosscutting-concepts.md
Purpose: rules and solutions that apply across many containers, so each feature does not reinvent them.
Write each concept as concrete rules the team follows ("All APIs MUST …"), link the ADR for rationale
and the NFRs it satisfies. Delete concepts that do not apply.
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# §8 Cross-cutting Concepts

## 8.1 Domain Model
<!-- Short overview of core entities and their relationships; details in data-model.md. -->
See [Data Model](../data-model.md). {{key domain rules, aggregates, ownership of entities per container}}

## 8.2 Security
<!-- Satisfies NFR-SEC-*. Cover:
- Authentication: IdP, protocol (OIDC / SAML), token lifetime, service-to-service auth.
- Authorization: role model, where checks happen, data-level access. Role × permission matrix if small.
- Secrets: store (Secrets Manager / Key Vault), rotation.
- Encryption: in transit (TLS ≥ 1.2), at rest (KMS / Key Vault keys).
- Input validation, OWASP Top 10 controls, audit logging. -->
### Authentication
{{rules}}

### Authorization
| Role | {{Permission 1}} | {{Permission 2}} |
|---|---|---|
| {{role}} | {{✓ / —}} | {{✓ / —}} |

### Secrets & Encryption
{{rules}}

## 8.3 Error Handling & Resilience
<!-- API error format (RFC 9457 problem+json), timeouts, retries with backoff, circuit breakers,
     idempotency keys, dead-letter queues and how they are reprocessed. -->
{{rules}}

## 8.4 Logging, Monitoring & Tracing
<!-- Structured log format and mandatory fields (timestamp UTC, level, correlationId, service), PII masking,
     trace propagation (W3C traceparent), metrics naming. Targets/alerts live in monitoring-alerting.md. -->
{{rules}} — see [Monitoring & Alerting](../../07-operations/monitoring-alerting.md).

## 8.5 Configuration Management
<!-- Where config lives (env vars, Parameter Store / App Configuration), per-environment overrides, feature flags. -->
{{rules}}

## 8.6 Data Management
<!-- Transactions and consistency (incl. across services), audit fields (createdAt/By …), soft delete,
     retention and archival (link NFR-COMP), file/document storage. -->
{{rules}}

## 8.7 Integration Patterns
<!-- Sync vs async choice, messaging conventions (event naming, CloudEvents envelope, versioning),
     outbox pattern, file-based exchange rules. -->
{{rules}}

## 8.8 Internationalization
<!-- optional — languages, time zones (store UTC, display ICT), currency and number formats. -->
{{rules}}

## 8.9 Testability
<!-- optional — test data strategy, contract tests, how external systems are mocked. Details in test-strategy.md. -->
{{rules}}
