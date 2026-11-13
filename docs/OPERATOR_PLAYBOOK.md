# V3 Operator Playbook — Development Edition

**Purpose:** teach the founder to manage exceptions and business performance, not manually edit every supplier row.

**Scope:** synthetic local training only. Do not treat this as a production SOP.

## Daily operator check (target: 10–15 minutes once workflows mature)
1. Open the local dashboard and review **operator attention**. Any failed/stalled job is high priority.
2. Examine unresolved holds. Duplicates, missing/unknown SKUs, and blank updates must be corrected in the supplier source and resubmitted, never approved away.
3. Read each proposed change with previous value, new value, risk, and supporting evidence. Approve or reject only after making an informed decision.
4. Confirm exports were independently verified. Never send an unverified file.
5. Record unusual patterns for process improvement: recurring supplier issues, common field mismatches, and false alarms.

## Decision authority

| Situation | System action | Human decision |
|---|---|---|
| Identical file submitted again | Deduplicate | Usually none |
| Normal upload arrives | Stage and analyze | No manual file handling |
| Duplicate SKU | Hold entire affected SKU | Obtain corrected data |
| Valid zero-stock | Flag and preserve as proposed | Confirm source and approve if correct |
| Price spike | High-risk flag | Verify supplier costs, currency and pricing rules |
| Unknown SKU | Hold | Confirm mapping or onboarding policy |
| Worker stalls | Fail closed | Investigate; do not blindly restart |
| All changes reviewed | Offer verified export | Confirm delivery scope |
| QA mismatch | Block and delete partial output | Investigate before retry |
| Customer asks for custom behavior | No silent policy change | Evaluate scope, price and risk |

## Business scorecard (monthly, once commercial)
- MRR and billed/collected revenue (not implemented yet)
- Gross margin and hours spent per customer
- On-time completed jobs and failure rates
- Human decisions per 100 processed changes
- Detected issues and verified false-positive/false-negative rates
- Customer retention/churn and reasons for cancellation
- Security incidents and backup recovery test results

Only call savings or avoided losses 'verified' when a defensible counterfactual or customer-confirmed impact supports the claim.

## When escalating
A useful escalation includes: affected customer, file/job ID, SKU, previous and proposed data, risk rule triggered, source evidence, options, recommended next step, and what is blocked. Avoid copying unnecessary customer data into messages.

## Failure recovery
1. Stop any attempted delivery or import.
2. Preserve affected job IDs, source hashes and audit events.
3. Investigate root cause. Re-run from a known-good snapshot, not an arbitrary modified file.
4. Recheck approvals and independently verify the final export.
5. Document the incident, customer impact, correction and preventative test.
6. Never 'fix' a failure by deleting holds or disabling QA.

## What AI may do
Summarize a problem, classify known cases, draft a customer-friendly explanation, recommend checks, and identify recurring issues. Its output is untrusted advice. It cannot use credentials, approve changes, send customer data, execute commands, or modify live stores.

## Launch gate
Production hosting, customer accounts, payment collection, contracts, and processing real data require separate permissions, safeguards and review. See [PRODUCTION_GATE.md](PRODUCTION_GATE.md). A parent or appropriately authorized business signatory may be required for commercial account and legal arrangements.
