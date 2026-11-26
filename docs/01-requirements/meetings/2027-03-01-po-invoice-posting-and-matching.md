---
id: MTG-20270301-9
title: "MTG-20270301-9 — PO invoice posting and trade PO matching"
status: draft            # draft | in-review | approved
owner: "Solution Architect (our company)"
reviewers: ["Solution Architect (our company)"]
last_updated: 2027-03-01
related: [DEC-005, DEC-006, DEC-007, DEC-010, DEC-013, DEC-014, DEC-021, DEC-023, DEC-032, DEC-033, DEC-034, DEC-035, DEC-041, SAPS-49, SAPS-51, SAPS-53]
---

# MTG-20270301-9 — PO invoice posting and trade PO matching

> **Assumption:** this meeting took place on the same day as the Phase 2 kickoff (2027-03-01). To be confirmed by the
> Solution Architect (our company).

## 1. Meeting Info
| Field | Value |
|---|---|
| Date | 2027-03-01 |
| Time | TBD |
| Type | requirements workshop |
| Channel | TBD |
| Facilitator | Solution Architect (our company) |
| Note taker | Solution Architect (our company) |
| Recording / slides | none |

## 2. Attendees
| Name | Organization | Role | Present |
|---|---|---|---|
| TBD | Customer | Product Owner | Yes |
| TBD | Our company | Solution Architect | Yes |

## 3. Follow-up from Previous Meetings
| From | Item | Update / new status |
|---|---|---|
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #Q4 | Kickoff Q7: priority of ERP integration, non-PO checks, posting, GR-based verification | Partly answered: posting of PO invoices and GR-based (DO) matching for trade PO invoices are urgent (R2, R5 – R8); MuleSoft and the ERP are not available yet (R3). Priority of the non-PO checks (SAPS-50) still open |
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #Q4 | Kickoff Q8 – Q12: NFR targets, peaks, retention, load test, UI language | Still open |
| [MTG-20270301-2](2027-03-01-phase-2-requirements.md) #Q1 | Go-live date and budget | Still open |
| [MTG-20270301-3](2027-03-01-tenancy-and-identity.md) #Q1 | Data residency per country | Still open |
| [SAPS-53](https://linear.app/jiringuyen/issue/SAPS-53) | Microsoft Graph adapter for the mailbox | Deferred by the Product Owner: it will be built later with a work mailbox (R10) |

## 4. Agenda
1. Invoice types
2. Automatic posting of PO invoices
3. ERP data without MuleSoft
4. Matching of trade PO invoices: PO or delivery order, 3-way matching, price check, tolerance

## 5. Discussion
- The system handles three invoice types: trade PO invoices, non-trade PO invoices and non-PO invoices.
- A PO invoice whose workflow runs without any exception that needs a confirmation is posted to the ERP automatically
  through MuleSoft. Nobody reviews it.
- There is no MuleSoft flow and no ERP yet. Until they exist, posting returns the status "ok".
- The Product Owner asked whether the open PO list can come from a mocked ERP while nothing is implemented for the ERP.
  The Solution Architect answered yes: the ERP is already behind a port with dummy data
  ([ADR-0001](../../02-architecture/adr/0001-isolate-extraction-and-erp-behind-ports.md)); the dummy data gets the
  open PO list and the new data (DO numbers on goods receipts, PIR prices), and the MuleSoft adapter replaces it later
  ([SCP-IN-15](../scope.md)).
- Trade PO invoices:
  - match by PO number when the PO has few deliveries, and by delivery order (DO) number when the PO is delivered in
    several lots;
  - each invoice pays exactly the lot that was received;
  - the workflow does 3-way matching (PO – GR – invoice): the quantity is checked against the goods receipt, the unit
    price against the purchasing info record (PIR) from the ERP, mocked for now;
  - the price tolerance still applies, 0.5 USD by default;
  - the DO number is written on the goods receipt, so the invoice can be reconciled with it.

- Answers to the Solution Architect's questions (§9):
  - Approval above the threshold stays before posting (Q1).
  - When the exceptions of an invoice are resolved, the workflow runs again; if it passes, the invoice is posted
    automatically (Q2).
  - The main idea of the Product Owner: an invoice with no problem, or whose exceptions were corrected, is posted
    automatically. No final review by an Accounting Member or Accounting Manager any more. This holds for non-PO
    invoices too, after the manual review (Q3).
  - Several goods receipts → the DO number is required. A DO number on the invoice that differs from the DO numbers on
    the goods receipts raises "Invalid DO number" (Q4).
  - The DO number is recorded on the goods receipt in the ERP; the system only reads it (Q8).
  - Q5 – Q7 and Q9 – Q14: the proposals are accepted.
  - The workflow that runs again means the processing after extraction (duplicate detection, type derivation,
    matching, approval decision, posting). It never repeats extraction, nor OCR / AI later, because of its cost.

## 6. Decisions
Proposed by the Solution Architect and confirmed by the Product Owner; logged in the decision log.

| # | Decision | Decided by | Logged as |
|---|---|---|---|
| D1 | `[CR]` Straight-through posting, no final review: the workflow ends with posting for every invoice type. An invoice is posted automatically when matching passes; above the approval threshold, after the Accounting Manager approves (Q1). When an Accounting Member closes the last exception (correction or acceptance), the workflow runs again, without extraction, and the invoice is posted if it passes (Q2, Q3); accepted exceptions are not raised again while their values are unchanged (Q12); invoices in Pending review at the upgrade are posted once (Q13). The final review step (SCP-IN-05) is withdrawn. Supersedes DEC-013 (order with final review), DEC-041; changes DEC-014 (rejection points), DEC-021 (final review notification) | Product Owner (Customer) | [DEC-063](../decision-log.md#dec-063) |
| D2 | Posting through an ERP posting port; until MuleSoft and the ERP exist, a mock adapter accepts every posting ("ok") and returns a mock ERP document number. New final status **Posted** with the ERP document number and the posting time; Completed stays for invoices finished before the change (Q9). A posting rejected by the real ERP raises "Posting failed", built with the MuleSoft adapter (Q10). Posted counts as invoiced (DEC-023) | Product Owner (Customer), on a proposal by the Solution Architect | [DEC-064](../decision-log.md#dec-064) |
| D3 | `[CR]` Trade PO invoices are matched per received lot (Q4 – Q6, Q8): a PO line with one goods receipt is matched by PO number; with several, the invoice line must carry the DO number of one goods receipt. The DO number is recorded on the goods receipt in the ERP and only read. The invoice quantity must not exceed the not yet invoiced quantity of that lot (EX7). One invoice may cover several lots, one DO per line. Supersedes DEC-034, refines DEC-007 and DEC-032. SCP-IN-21 detailed (Must) | Product Owner (Customer) | [DEC-065](../decision-log.md#dec-065) |
| D4 | The unit price of a trade PO invoice line is checked against the PIR price valid on the invoice date (vendor + material + company), with the configurable price tolerance (default 0.5 USD, DEC-015). PO lines carry a material number. Non-trade PO invoices keep the check against the PO price (Q7). Partly supersedes DEC-006 | Product Owner (Customer) | [DEC-066](../decision-log.md#dec-066) |
| D5 | Until the ERP integration (SCP-IN-15), the dummy ERP data per company holds the open PO list, goods receipts with DO numbers and PIR prices. A PO that is not open (closed or fully invoiced) raises EX4 "PO is not open" (Q11). Extends DEC-004 to Phase 2; changes SCP-IN-09 | Product Owner (Customer), on a proposal by the Solution Architect | [DEC-067](../decision-log.md#dec-067) |
| D6 | New exception types: EX11 DO number missing, EX12 No purchasing info record, EX13 Invalid DO number; EX8 stays for a PO line without any goods receipt (Q4, Q6, Q7, Q14). Extends DEC-033 | Product Owner (Customer) | [DEC-068](../decision-log.md#dec-068) |

The three invoice types (R1) are already decided in [DEC-005](../decision-log.md#dec-005); no new decision.

## 7. Requirements Captured
| # | Information / requirement | Type | Proposed target | Status |
|---|---|---|---|---|
| R1 | Three invoice types: trade PO, non-trade PO, non-PO | Functional | [DEC-005](../decision-log.md#dec-005) (unchanged) | confirmed |
| R2 | PO invoices without an exception that needs a confirmation are posted to the ERP through MuleSoft automatically, without review | Functional | DEC-063 `[CR]`; SCP-IN-05, SCP-IN-17; [SAPS-49](https://linear.app/jiringuyen/issue/SAPS-49) | logged |
| R3 | No MuleSoft flow and no ERP yet: posting returns "ok" | Functional | DEC-064; SAPS-49 | logged |
| R4 | Open PO list from a mocked ERP until the ERP integration | Functional | DEC-067; SCP-IN-09; [SAPS-51](https://linear.app/jiringuyen/issue/SAPS-51) | logged |
| R5 | Trade PO invoices: match by PO number for few deliveries, by DO number for several; each invoice pays exactly the received lot | Functional | DEC-065 `[CR]`; SCP-IN-03, SCP-IN-21; SAPS-51 | logged |
| R6 | Trade PO invoices: 3-way matching PO – GR – invoice; quantity against the GR, unit price against the PIR (mocked) | Functional | DEC-065, DEC-066; SAPS-51 | logged |
| R7 | Trade PO invoices: price tolerance still applies, 0.5 USD by default | Functional | DEC-066 (tolerance as in [DEC-015](../decision-log.md#dec-015), [DEC-045](../decision-log.md#dec-045)) | logged |
| R8 | The DO number is recorded on the goods receipt in the ERP; the system reads it for the reconciliation | Functional | DEC-065, DEC-067 | logged |
| R9 | These items are urgent | Priority | SCP-IN-17, SCP-IN-21 priority Must | logged |
| R10 | SAPS-53 (Microsoft Graph adapter) deferred: it will be built with a work mailbox | Priority | backlog only | logged |
| R11 | After the exceptions are resolved, the workflow (without extraction) runs again; if it passes, the invoice is posted automatically | Functional | DEC-063; refines [DEC-010](../decision-log.md#dec-010); SAPS-49 | logged |
| R12 | No final review by an Accounting Member or Accounting Manager; non-PO invoices are posted after the manual review | Functional | DEC-063 `[CR]`; SCP-IN-05 withdrawn | logged |
| R13 | A DO number on the invoice that differs from the DO numbers on the goods receipts raises "Invalid DO number" | Functional | DEC-068; SAPS-51 | logged |

### 7.1 Conflicts with existing items
| Existing item | Conflict | Proposed resolution |
|---|---|---|
| [SCP-IN-05](../scope.md), [DEC-013](../decision-log.md#dec-013), [DEC-041](../decision-log.md#dec-041), [SAPS-21](../../03-features/SAPS-21-final-result-review.md) | Final review is the end of the flow for every invoice; R12 removes it | DEC-063 withdraws SCP-IN-05 and supersedes DEC-013 and DEC-041; approval (DEC-009, SCP-IN-06) stays, before posting |
| [DEC-014](../decision-log.md#dec-014), [SCP-IN-14](../scope.md) | One of the three rejection points is the final review | DEC-063: two rejection points remain (approval, exception handling) |
| [DEC-021](../decision-log.md#dec-021), [SCP-IN-08](../scope.md) | Notification "Invoice ready for final review" | DEC-063 removes it; Q13 |
| [DEC-035](../decision-log.md#dec-035), [DEC-010](../decision-log.md#dec-010) | Re-running the workflow after an acceptance as is raises the accepted exception again (EX2 is raised on every run of a non-PO invoice) | Q12 |
| [DEC-034](../decision-log.md#dec-034), [SCP-IN-03](../scope.md) | The PoC matches cumulatively per PO line, with no DO / GR reference; R5 and R8 match per DO | DEC-065 supersedes DEC-034 for trade PO invoices |
| [DEC-007](../decision-log.md#dec-007) | "Several goods receipts for one PO line: their quantities are summed"; R5 pays exactly one lot | DEC-065 refines DEC-007 for trade PO invoices |
| [DEC-032](../decision-log.md#dec-032) | A smaller quantity passes (partial invoicing) | Kept, per lot (Q5) |
| [DEC-006](../decision-log.md#dec-006) | The unit price is checked against the PO price; R6 checks it against the PIR | DEC-066 partly supersedes DEC-006 for trade PO invoices |
| [DEC-023](../decision-log.md#dec-023) | The already invoiced quantity counts PendingApproval, PendingReview and Completed; Posted must count too | DEC-064 adds Posted to DEC-023's list |
| Completed in the [glossary](../../02-architecture/arc42/12-glossary.md) | "Posting to the ERP happens outside Smart-AP-Suite"; R2 posts from the system | Glossary and SCP-IN-17 updated with DEC-064 |
| [DEC-033](../decision-log.md#dec-033) | New exception types; changes need a new decision | DEC-068 |
| Q6 (EX8 for an unknown DO) and R13 ("Invalid DO number") | The Product Owner agreed to both; they overlap | Q14 |

### 7.2 ADR needs
- **ADR-0013 — Post invoices to the ERP through a posting port.** Port and adapter (mock now, MuleSoft later),
  idempotency so that an invoice is posted once (retries, worker restarts), and where a failed posting goes. Options:
  post inside the matching job, or a separate posting job after commit (outbox style).

## 8. Action Items
| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| A1 | Confirm or correct D1 – D6 and answer Q12 – Q14 | Product Owner (Customer) | 2027-03-01 | done |
| A2 | Apply D1 – D6 to the decision log and scope (version 0.10) once confirmed | Solution Architect (our company) | 2027-03-01 | done |
| A3 | Feature specs for SAPS-51 (trade PO matching per lot, PIR, dummy ERP data) and SAPS-49 (posting, re-run, final review removed); ADR-0013 | Solution Architect (our company) | after A1 | open |
| A4 | Update the demo scenario catalog for the new flows (SAPS-47) | Solution Architect (our company) | after A3 | open |

## 9. Open Questions
| # | Question | Proposal (Solution Architect) | Owner | Due | Status |
|---|---|---|---|---|---|
| Q1 | An invoice without exceptions but above the approval threshold (300 USD by default): does it still need the Accounting Manager's approval before posting? | Yes, approval stays (DEC-009 control); after approval it is posted without final review | Product Owner (Customer) | — | answered: yes → D1 |
| Q2 | An invoice that had exceptions, which an Accounting Member resolved or accepted: final review before posting, or posted after the exceptions are closed? | Final review, then posting on confirmation | Product Owner (Customer) | — | answered: the workflow runs again and posts if it passes (R11) → D1 |
| Q3 | Non-PO invoices: are they posted too, after the manual review (EX2) and final review? | Yes, posted when the Accounting Member confirms at final review | Product Owner (Customer) | — | answered: posted after the manual review, no final review for any invoice (R12) → D1 |
| Q4 | How does the system tell "few deliveries" from "several lots"? | By the goods receipts of the PO line: one GR → match by PO number; several GRs → the invoice line must carry the DO number; DO number missing → new exception "DO number missing" (EX11) | Product Owner (Customer) | — | answered: yes, plus "Invalid DO number" (R13) → D3, D6 |
| Q5 | Must the invoice quantity equal the lot quantity, or may it be smaller? | Must not exceed the not yet invoiced quantity of that lot (as DEC-032); larger → EX7. One invoice may cover several lots, one DO per line | Product Owner (Customer) | — | answered: yes → D3 |
| Q6 | A DO number that no goods receipt of that PO line carries: which exception? | EX8 "Missing goods receipt", with the DO number in the message | Product Owner (Customer) | — | answered: yes; overlaps R13, see Q14 |
| Q7 | PIR: what identifies the record, and what if none is found? | Vendor + material + company, with a validity period; the price valid on the invoice date; PO lines get a material number; no valid PIR → EX12 "No purchasing info record" | Product Owner (Customer) | — | answered: yes → D4, D6 |
| Q8 | Is the DO number recorded on the GR in the ERP at goods receipt, and the system only reads it? | Yes; the system does not write to the ERP | Product Owner (Customer) | — | answered: yes → D3 |
| Q9 | Status after posting, and what the user sees | New final status Posted with the ERP document number (mock) and the posting time; Completed stays for older invoices | Product Owner (Customer) | — | answered: yes → D2 |
| Q10 | When the real ERP rejects a posting later: what happens? | New exception "Posting failed"; built with the MuleSoft adapter, not now | Product Owner (Customer) | — | answered: yes → D2 |
| Q11 | Is a closed or fully invoiced PO treated as "not found" (EX4)? | Yes, EX4 with the message "PO is not open" | Product Owner (Customer) | — | answered: yes → D5 |
| Q12 | When the workflow runs again after the exceptions are closed, what happens to exceptions accepted as is (EX2, EX6, EX7, EX9, DEC-035)? Without a rule they are raised again on every run, and a non-PO invoice never gets posted | An accepted exception stays accepted while the values it was raised on are unchanged (same line, quantity, price, vendor, invoice number); the run skips it. A changed value or a new problem raises a new exception. Fresh ERP data is read on the run | Product Owner (Customer) | — | answered: yes → D1 |
| Q13 | Removing the final review: what happens to invoices already in Pending review at the upgrade, and to the final review screen and its notification? | Invoices in Pending review at the upgrade are posted by a one-time run (or stay for a last confirmation, if preferred); the final review screen and the notification "ready for final review" are removed; the outcome stays visible in the invoice detail and All invoices | Product Owner (Customer) | — | answered: yes → D1 |
| Q14 | Q6 (EX8 for a DO number that no goods receipt carries) and the new "Invalid DO number" overlap. Which applies? | EX13 "Invalid DO number" when the invoice DO number matches no goods receipt of that PO line; EX8 only when the PO line has no goods receipt at all | Product Owner (Customer) | — | answered: yes → D3, D6 |

## 10. Next Meeting
- On demand.

## 11. Customer Confirmation
| Field | Value |
|---|---|
| Summary sent on | not sent; the Product Owner reviews the minutes directly |
| Confirmed on | pending |
| Reference | this document |
| Corrections received | none |
