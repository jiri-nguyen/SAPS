---
id: MTG-YYYYMMDD
title: "MTG-YYYYMMDD — {{Meeting topic}}"
status: draft            # draft | in-review | approved
owner: "{{note taker}}"
reviewers: ["{{facilitator}}"]
last_updated: YYYY-MM-DD
related: []              # e.g. [MTG-20261107, DEC-004]
---
<!--
TEMPLATE: Meeting Minutes
Copy to: docs/01-requirements/meetings/YYYY-MM-DD-<topic>.md   (one file per meeting)
ID: MTG-YYYYMMDD; add -2, -3 … if there is more than one meeting on the same day.
Rules:
- Record what was said and agreed. Do not interpret or add requirements that nobody stated.
- Every decision goes to the Decisions table, then into decision-log.md (DEC-NNN) once confirmed.
- Every new piece of requirement information goes to "Requirements Captured" and is promoted
  to scope.md (SCP-*), nfr.md (NFR-*), the backlog (Jira) or arc42 §2 (constraints).
- Send the summary to the customer and fill in "Customer Confirmation".
- Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# MTG-YYYYMMDD — {{Meeting topic}}

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | YYYY-MM-DD |
| Time | {{HH:MM–HH:MM}} ICT |
| Type | {{kickoff \| requirements workshop \| design review \| status \| demo}} |
| Channel | {{Teams / Zoom / onsite at …}} |
| Facilitator | {{name}} |
| Note taker | {{name}} |
| Recording / slides | {{link or "none"}} |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| {{name}} | {{customer / our company / 3rd party}} | {{role}} | {{Yes / No}} |

## 3. Follow-up from Previous Meetings
<!-- Carry over every action item and open question that is not closed yet. Link the meeting it came from.
     Example row:
| [MTG-20261107](2026-11-07-kickoff.md) #Q2 | Expected invoice volume per month? | Answered: ~30,000 invoices/month → see Requirements Captured #3 |
-->
| From | Item | Update / new status |
|---|---|---|
| [MTG-YYYYMMDD]({{YYYY-MM-DD-topic}}.md) #{{A1 / Q1}} | {{action item or question}} | {{closed / still open / answer}} |

## 4. Agenda
1. {{agenda topic}}
2. {{agenda topic}}

## 5. Discussion
<!-- One subsection per agenda topic. Short bullets of key points; name who said what only when it matters. -->
### 5.1 {{agenda topic}}
- {{key point}}

### 5.2 {{agenda topic}}
- {{key point}}

## 6. Decisions
<!-- "Logged as": the DEC-NNN link once added to decision-log.md, or "pending" until confirmed by the customer. -->
| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | {{decision}} | {{name (organization)}} | {{[DEC-NNN](../decision-log.md#dec-nnn) / pending}} |

## 7. Requirements Captured
<!-- Every new or changed requirement/information from this meeting.
     Type: Functional | NFR | Constraint | Scope | Assumption
     Proposed target: where it will live → SCP-IN/OUT-NN (scope.md), NFR-<CAT>-NNN (nfr.md), Jira key (backlog),
                      arc42 §2 (constraint), or "assumption" (scope.md §5).
     Status: proposed (not yet written to target) | logged (written, link the ID) | rejected (with reason)
     Example row:
| R3 | ~30,000 invoices/month, peak 3× in the last 3 days of the month | NFR | NFR-PERF-002 + workload profile | logged |
-->
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | {{what was stated}} | {{Functional / NFR / Constraint / Scope / Assumption}} | {{SCP-IN-NN / NFR-CAT-NNN / Jira key / arc42 §2}} | {{proposed / logged / rejected}} |

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | {{action}} | {{name (organization)}} | YYYY-MM-DD | {{open / done}} |

## 9. Open Questions
| # | Question | Asked to | Due | Answer / status |
|---|---|---|---|---|
| Q1 | {{question}} | {{name (organization)}} | YYYY-MM-DD | {{open}} |

## 10. Next Meeting
<!-- optional -->
- Date: YYYY-MM-DD {{HH:MM}} ICT
- Planned topics: {{topics}}

## 11. Customer Confirmation
| Field | Value |
|---|---|
| Summary sent on | YYYY-MM-DD by {{name}} |
| Confirmed on | {{YYYY-MM-DD by name / pending}} |
| Reference | {{email subject or link}} |
| Corrections received | {{none / short description — update the sections above}} |
