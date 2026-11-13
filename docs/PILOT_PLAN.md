# V3 Controlled Pilot Plan — Not Yet Authorized

This is a proposed validation protocol, not an invitation to send live data today.

## Pilot objective
Determine whether retailers with recurring supplier CSV updates will pay for a managed, reviewed service and whether V3 can deliver it safely, economically, and on schedule.

## Ideal prospect
- Online retailer managing roughly 500–5,000 SKUs
- Receives supplier updates weekly
- Already spends meaningful time correcting or checking catalog changes
- Willing to describe current workflow and validate a sample outcome
- Has an authorized representative who can approve sharing data

## Qualification questions
1. How many suppliers and SKUs are involved?
2. How often are updates received, and in what formats?
3. What software is currently used?
4. What happened the last time an incorrect price or stock change was imported?
5. How much staff time is spent checking updates?
6. Who authorizes catalog imports?
7. What would a reliable reviewed update be worth monthly?

## Pilot scope proposal
- One retailer, one store, one agreed supplier CSV format
- Fixed row/file count and turnaround expectation; not yet priced or promised
- Explicit boundaries: no real storefront write access; merchant imports changes after approving
- A secure data-handling agreement and consent before any real files are processed
- Original data preserved with backups and defined deletion time
- A dedicated named operator responsible for all approvals
- Documented QA of every exported update

## Acceptance metrics
- 100% of intentional test-case anomalies detected in curated fixtures
- No known unauthorized changes, data mixing, or unverified exports
- Measured false-positive and false-negative rates on representative anonymized or permissioned cases
- Minutes of operator time per file and per customer
- Jobs delivered on time, held and failed jobs, mean remediation time
- Customer's independently confirmed time saved and willingness to continue paying
- Direct service costs, contribution margin and support effort

These are test gates, not established product performance.

## Release stages
1. Synthetic local tests — current stage.
2. Independent security and data-flow review — not yet done.
3. Staging on approved hosting accounts with fabricated data — not yet done.
4. Authorized, tightly controlled pilot with agreements — not yet done.
5. Paid recurring subscriptions, only if pilots show repeatable value and safe operations.

## Stop rules
Stop or roll back immediately if a test shows cross-customer access, unapproved changes, failed independent QA, corrupted outputs, unbounded processing costs, leaked credentials, or missing audit evidence.

## Role of the business owner
Choose commercial scope, price and customers; approve material customer commitments, inspect weekly quality/margins, and make decisions on escalated incidents. Routine validation should remain automated within enforceable safeguards.
