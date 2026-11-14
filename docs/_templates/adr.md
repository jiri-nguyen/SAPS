---
id: ADR-NNNN
title: "ADR-NNNN: {{Short decision title, imperative — e.g. Use Amazon SQS for invoice processing}}"
status: proposed         # proposed | accepted | rejected | deprecated | superseded
date: YYYY-MM-DD         # date of the latest status change
owner: "{{Solution Architect}}"
deciders: ["{{name}}"]   # who makes the final call
consulted: ["{{name}}"]  # whose input was sought (customer IT, security, DevOps …)
last_updated: YYYY-MM-DD
supersedes: ""           # ADR-NNNN or empty
superseded_by: ""        # ADR-NNNN or empty
related: []              # e.g. [NFR-AVAIL-001, CON-02, DEC-007]
---
<!--
TEMPLATE: Architecture Decision Record (based on MADR)
Copy to: docs/02-architecture/adr/NNNN-<kebab-title>.md   NNNN = highest existing number + 1.
When to write one: a decision that is hard to reverse or affects structure, technology, quality attributes,
integration, cost or team skills. Business/scope decisions go to decision-log.md instead.
Rules:
- Consider at least 2 options; "do nothing / keep current" is a valid option.
- Decision drivers MUST link the NFRs, constraints (CON-*) and decisions (DEC-*) behind them.
- After the ADR is accepted it is immutable — only status / superseded_by may change.
  To change the decision, write a new ADR that supersedes this one.
- When the customer must agree, record the agreement as a DEC-* and link it under "More Information".
- Add/update the row in arc42/09-architecture-decisions.md.
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# ADR-NNNN: {{Short decision title}}

## Context and Problem Statement
<!-- 2–5 sentences: the situation, the forces at play, and the question to answer. -->
{{context}}

**Question:** {{the decision to make, phrased as a question}}

## Decision Drivers
- {{driver}} — [NFR-CAT-NNN](../../01-requirements/nfr.md#nfr-cat-nnn)
- {{driver}} — [CON-NN](../arc42/02-constraints.md)
- {{driver, e.g. team skills, cost, time to market}}

## Considered Options
1. {{Option 1}}
2. {{Option 2}}
3. {{Option 3}}

## Decision Outcome
**Chosen option:** "{{Option N}}", because {{justification referring to the decision drivers}}.

### Consequences
- **Good:** {{positive consequence}}
- **Bad:** {{negative consequence, accepted trade-off}}
- **Neutral:** {{other effect, e.g. new skill needed, cost change}}

### Confirmation
<!-- How we will check the decision is implemented and still holds: code review rule, architecture test,
     load test (PSR), cost review, revisit date. -->
{{confirmation}}

## Pros and Cons of the Options

### {{Option 1}}
<!-- One-line description, optional link to docs / PoC. -->
- Good, because {{argument}}
- Bad, because {{argument}}

### {{Option 2}}
- Good, because {{argument}}
- Bad, because {{argument}}

### {{Option 3}}
- Good, because {{argument}}
- Bad, because {{argument}}

## More Information
<!-- optional — PoC / spike results, cost comparison, customer agreement, revisit triggers. -->
- Customer agreement: {{[DEC-NNN](../../01-requirements/decision-log.md#dec-nnn) / not required}}
- {{links}}
