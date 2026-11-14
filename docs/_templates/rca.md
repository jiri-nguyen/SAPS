---
id: RCA-YYYYMMDD
title: "RCA-YYYYMMDD — {{Short description of the problem}}"
version: "0.1"           # 1.0 = first version shared with the customer
status: draft            # draft | in-review | approved
owner: "{{investigating developer / Tech Lead}}"
reviewers: ["{{Solution Architect}}", "{{QA}}"]
last_updated: YYYY-MM-DD
ticket: "{{BUG-KEY}}"    # Jira / Azure Boards bug or incident ticket
severity: "{{Critical / High / Medium / Low}}"   # Test Strategy §7; SEV1–SEV4 for prod incidents
related: []              # e.g. [ALR-003, RB-002, ADR-0009, APA-200]
---
<!--
TEMPLATE: Root Cause Analysis (bug investigation & post-incident review)
Copy to: docs/07-operations/rca/YYYY-MM-DD-<BUG-KEY>-<kebab-title>.md   (date = detection date)
Write an RCA when ANY of these is true (otherwise the Jira ticket is enough):
- prod incident SEV1 / SEV2, data loss or corruption, or a security issue
- root cause is unclear after a first look, or the bug spans several containers
- there is more than one viable fix and a decision is needed
- the customer asks for a formal report
Rules:
- Blameless: analyze systems and processes, never individuals.
- Facts with evidence (logs, metrics, queries); label guesses as hypotheses.
- If the chosen fix changes the architecture → write an ADR; if it is as big as a feature → write a feature spec
  (03-features/<BUG-KEY>-<title>.md). Link both here.
- Every preventive action gets a ticket. For prod incidents, add a row to runbook.md §6 linking this RCA.
- No secrets or real personal data in evidence — mask them.
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# RCA-YYYYMMDD — {{Short description of the problem}}

## 1. Summary
<!-- 3–5 sentences for a reader who reads nothing else: what happened, impact, root cause, fix status. -->
{{summary}}

| Field | Value |
|---|---|
| Ticket | [{{BUG-KEY}}]({{tracker base URL}}{{BUG-KEY}}) |
| Environment | {{dev / stg / prod}} |
| Affected versions | {{vX.Y.Z – vX.Y.Z}} |
| Severity | {{severity}} |
| Detected | {{YYYY-MM-DD HH:MM ICT}} by {{alert ALR-NNN / test / customer / developer}} |
| Resolved | {{YYYY-MM-DD HH:MM ICT / workaround in place / open}} |
| Fixed in | {{vX.Y.Z / planned}} |

## 2. Problem Description
**Steps to reproduce**
1. {{start state: role, data, URL}}
2. {{step}}

**Expected:** {{expected behavior — cite acceptance criterion / business rule}}
**Actual:** {{actual behavior, exact error message}}

## 3. Impact
| Aspect | Impact |
|---|---|
| Users | {{who and how many}} |
| Functions | {{what could not be done}} |
| Data | {{records affected / none}} |
| Duration | {{from – to, or "test environment only"}} |
| Business / SLO | {{e.g. 40 invoices paid late; 60 % of SLO-01 error budget used}} |

## 4. Timeline
<!-- optional for bugs found in testing; required for prod incidents. Times in ICT. -->
| Time (ICT) | Event |
|---|---|
| YYYY-MM-DD HH:MM | {{event: deploy, first error, alert, acknowledge, mitigation, resolution}} |

## 5. Investigation
<!-- What was checked, in order. Result: confirmed | rejected | inconclusive. -->
| # | Hypothesis | Evidence | Result |
|---|---|---|---|
| H1 | {{hypothesis}} | {{log query / metric / test / code reference}} | {{confirmed / rejected}} |

## 6. Root Cause
{{Root cause in 2–4 sentences: the technical cause and the condition that triggered it.}}

**5 Whys**
1. Why {{symptom}}? — Because {{…}}
2. Why {{…}}? — Because {{…}}
3. Why {{…}}? — Because {{…}}

**Why it was not caught earlier:** {{missing test, monitoring gap, review gap, unclear requirement}}

## 7. Solution Options
<!-- Include short-term (workaround / hotfix) and long-term options. Effort: S / M / L. Risk: Low / Medium / High. -->
| # | Option | Pros | Cons | Effort | Risk |
|---|---|---|---|---|---|
| O1 | {{option}} | {{pros}} | {{cons}} | {{S/M/L}} | {{L/M/H}} |
| O2 | {{option}} | {{pros}} | {{cons}} | {{S/M/L}} | {{L/M/H}} |

**Chosen:** {{O#}} — {{rationale}}. {{Short-term mitigation, if different: O#.}}
**Decision by:** {{name, date}} · {{[ADR-NNNN](../../02-architecture/adr/NNNN-title.md) / [feature spec](../../03-features/BUG-KEY-title.md) / —}}

## 8. Fix & Data Correction
- Fix: {{PR link}} · released in {{vX.Y.Z}}
- Tests added: {{test name / level}}
- Data correction: {{none / scope, script, verification, customer approval reference}}

## 9. Preventive Actions
<!-- Type: Test | Monitoring | Code | Design | Process | Documentation. -->
| # | Action | Type | Owner | Ticket | Due | Status |
|---|---|---|---|---|---|---|
| P1 | {{action}} | {{type}} | {{name}} | {{[KEY-NN](url)}} | YYYY-MM-DD | {{open / done}} |

## 10. Lessons Learned
- **Went well:** {{…}}
- **To improve:** {{…}}

## 11. Change History
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | YYYY-MM-DD | {{name}} | Initial draft |
