---
title: Runbook
status: draft            # draft | in-review | approved | deprecated
owner: "{{DevOps}}"
reviewers: ["{{Tech Lead}}", "{{Solution Architect}}"]
last_updated: YYYY-MM-DD
related: []
---
<!--
TEMPLATE: Runbook
Copy to: docs/07-operations/runbook.md   (one file per project)
Purpose: step-by-step procedures for responding to alerts, routine operations and recovery,
usable at 3 a.m. by someone who did not build the system.
Rules:
- Every alert (ALR-*) in monitoring-alerting.md has a procedure here, and the procedure links back to it.
- Steps are exact: console paths, commands, queries, expected output. Use {{placeholders}} for values;
  NEVER write secrets, passwords or tokens here.
- Each procedure ends with verification and with "escalate if" criteria.
- After every incident, update the relevant procedure (or add one) and record the incident in §6.
IDs: RB-NNN — permanent, never reused. Item headings are the ID only.
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# Runbook

## 1. System Overview
<!-- Just enough to orient an on-call engineer. Details: arc42 §5 and §7. -->
{{one-paragraph description of the system and its critical paths}}

- Architecture: [arc42 §5 Building Blocks](../02-architecture/arc42/05-building-block-view.md) · [§7 Deployment](../02-architecture/arc42/07-deployment-view.md)
- Monitoring & alerts: [Monitoring & Alerting](monitoring-alerting.md)
- Deployment & rollback: [Deployment Guide](../06-release/deployment-guide.md)

## 2. Quick Reference
| Resource | prod | stg |
|---|---|---|
| Cloud console / account | {{link / account alias}} | {{link}} |
| Dashboards | {{link}} | {{link}} |
| Logs query | {{link to saved query}} | {{link}} |
| CI/CD | {{link}} | {{link}} |
| Status page / incident channel | {{link}} | — |

## 3. Contacts & Escalation
<!-- Use roles and team channels; personal phone numbers belong in the on-call tool, not here. -->
| Level | Who | When | Channel |
|---|---|---|---|
| L1 | {{on-call engineer}} | {{alert fires}} | {{PagerDuty / Teams}} |
| L2 | {{Tech Lead}} | {{not resolved in n min / SEV1}} | {{channel}} |
| L3 | {{Solution Architect / cloud vendor support}} | {{infrastructure or design issue}} | {{channel / support case}} |
| Customer | {{customer IT contact role}} | {{SEV1–SEV2, or customer action needed}} | {{channel}} |
| Third parties | {{ERP vendor / IdP}} | {{integration down}} | {{support portal}} |

## 4. Procedures

| ID | Title | Type | Triggered by |
|---|---|---|---|
| [RB-001](#rb-001) | {{title}} | {{Alert response / Routine / Recovery}} | {{[ALR-NNN](monitoring-alerting.md#alr-nnn) / schedule / on request}} |

<!-- Typical procedures to add: restart / scale a service, reprocess dead-letter messages, rotate a secret,
     renew a certificate, restore a database from backup (DR), fail over to another AZ/region,
     grant / revoke user access, clear a stuck batch job, put the system in maintenance mode. -->

### RB-001
**{{Procedure title}}**

| Field | Value |
|---|---|
| Type | {{Alert response / Routine / Recovery}} |
| Triggered by | {{[ALR-NNN](monitoring-alerting.md#alr-nnn) / schedule / request}} |
| User impact | {{what users experience while this is happening}} |
| Required access | {{role / permission}} |
| Expected duration | {{n min}} |

**Diagnose**
1. {{check dashboard … — look for …}}
2. {{run query:}}
   ```
   {{log / metric query}}
   ```
3. {{decide: if … go to Resolve A; if … go to Resolve B}}

**Resolve**
1. {{step, with exact command or console path}}
   ```bash
   {{command}}
   ```
2. {{step}}

**Verify**
- {{alert resolved, metric back to normal, smoke test passes}}

**Escalate if**
- {{not resolved within n min / data loss suspected / root cause outside our system → L2 / L3 / customer}}

**Related:** {{incidents, ADRs, tickets}}

## 5. Incident Response
<!-- Severity definitions are in monitoring-alerting.md §6. -->
1. **Acknowledge** the alert within the response time for its severity.
2. **Assess** impact and set the severity; open an incident channel / ticket for SEV1–SEV2.
3. **Communicate** — first update within {{15 / 30}} min, then every {{30 / 60}} min, using the template below.
4. **Mitigate** using the matching RB procedure; roll back if a recent deployment is the likely cause.
5. **Resolve** and confirm with monitoring.
6. **Review** — for SEV1–SEV2, write an RCA (`_templates/rca.md`) within {{5}} business days and record it in §6.

**Status update template**
```
[{{SEV}}] {{System}} — {{Investigating / Identified / Monitoring / Resolved}}
Impact: {{who is affected and how}}
Started: {{YYYY-MM-DD HH:MM ICT}}
Current action: {{what we are doing}}
Next update: {{HH:MM ICT}}
```

## 6. Incident History
| Date | Incident | Severity | Duration | Root cause | Actions | RCA |
|---|---|---|---|---|---|---|
| YYYY-MM-DD | {{title}} | {{SEV}} | {{n min}} | {{root cause}} | {{tickets}} | {{[RCA-YYYYMMDD](rca/YYYY-MM-DD-BUG-KEY-title.md) / —}} |

## 7. Scheduled Operations
<!-- Recurring tasks that keep the system healthy and prove recovery works. -->
| Task | Frequency | Owner | Procedure | Last done |
|---|---|---|---|---|
| {{Backup restore test}} | {{quarterly}} | {{DevOps}} | {{[RB-NNN](#rb-nnn)}} | YYYY-MM-DD |
| {{Access review}} | {{quarterly}} | {{Tech Lead}} | {{RB-NNN}} | YYYY-MM-DD |
| {{OS / runtime patching}} | {{monthly}} | {{DevOps}} | {{RB-NNN}} | YYYY-MM-DD |
| {{Certificate expiry check}} | {{monthly}} | {{DevOps}} | {{RB-NNN}} | YYYY-MM-DD |
