---
id: vX.Y.Z
title: "Release vX.Y.Z"
version: "1.0"           # document version (not the release version); bump if the notes are corrected
status: draft            # draft | in-review | approved
owner: "{{Tech Lead}}"
reviewers: ["{{PM}}", "{{QA}}"]
last_updated: YYYY-MM-DD
related: []              # e.g. [ADR-0007, APA-123]
---
<!--
TEMPLATE: Release Notes (customer-facing)
Copy to: docs/06-release/release-notes/vX.Y.Z.md   (one file per release deployed to stg or prod)
SemVer: MAJOR = breaking change for users or API consumers · MINOR = new features, backward compatible ·
        PATCH = fixes only. Hotfix = PATCH deployed outside the normal schedule.
Rules:
- Write for the customer: describe changes in business terms; technical detail goes in the linked specs.
- Every row links its Jira key. Only list items that are actually in this build.
- Breaking changes and required actions are never omitted; write "None" explicitly.
- Delete sections that are empty, except §5 Breaking Changes and §10 Known Issues (write "None").
Delete all guidance comments and {{placeholders}} before setting status: in-review.
-->

# Release vX.Y.Z

## 1. Summary
<!-- 2–4 bullets: what users get from this release. -->
- {{highlight}}

## 2. Release Info
| Item | Value |
|---|---|
| Release type | {{Major / Minor / Patch / Hotfix}} |
| Build | {{commit SHA / image tags}} |
| Deployed to stg | YYYY-MM-DD |
| Deployed to prod | {{YYYY-MM-DD HH:MM ICT / planned}} |
| Downtime | {{none / n minutes in window …}} |
| Release manager | {{name}} |
| Previous release | [vX.Y.Z](vX.Y.Z.md) |

## 3. New Features
| Ticket | Feature | Description | Spec |
|---|---|---|---|
| [{{KEY-NN}}]({{url}}) | {{feature name}} | {{what users can now do}} | {{[spec](../../03-features/KEY-NN-title.md) / —}} |

## 4. Improvements & Bug Fixes
| Ticket | Type | Description | Severity |
|---|---|---|---|
| [{{KEY-NN}}]({{url}}) | {{Improvement / Fix}} | {{what changed, in user terms}} | {{for fixes: Critical / High / Medium / Low}} |

## 5. Breaking Changes & Required Actions
<!-- Who must do what, by when. Write "None." if there are none. -->
| Change | Affected | Required action | By |
|---|---|---|---|
| {{change}} | {{API consumers / admins / users}} | {{action}} | YYYY-MM-DD |

## 6. API & Integration Changes
<!-- optional -->
| API / event | Operation / channel | Change | Spec version |
|---|---|---|---|
| {{API name}} | {{operationId / channel}} | {{new / modified / deprecated (removal in vX)}} | {{0.3.0}} |

## 7. Infrastructure, Configuration & Data Changes
<!-- optional — new cloud resources, config keys, scaling changes, data migrations and their duration. -->
| Change | Environment | Impact | Reference |
|---|---|---|---|
| {{change}} | {{stg, prod}} | {{impact, e.g. +USD 30/month, 5-min migration}} | {{ADR / ticket}} |

## 8. Architecture Decisions
<!-- optional — ADRs accepted or superseded in this release. -->
- [ADR-NNNN](../../02-architecture/adr/NNNN-title.md) — {{title}} ({{accepted / superseded}})

## 9. Quality & Verification
| Check | Result | Evidence |
|---|---|---|
| Regression tests | {{passed n / n}} | {{link}} |
| Performance | {{PASS / not required}} | {{[PSR-YYYYMMDD](../../05-testing/performance/YYYY-MM-DD-psr-scope.md)}} |
| Security scans | {{no Critical / High open}} | {{link}} |
| UAT | {{signed off on YYYY-MM-DD / not required}} | {{reference}} |

## 10. Known Issues
<!-- Write "None." if there are none. -->
| Ticket | Issue | Workaround | Planned fix |
|---|---|---|---|
| [{{KEY-NN}}]({{url}}) | {{issue}} | {{workaround}} | {{vX.Y.Z}} |

## 11. Change History
| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | YYYY-MM-DD | {{name}} | Initial release notes |
