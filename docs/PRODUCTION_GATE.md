# V3 production release gate

**Decision: NO-GO.** The current software is a localhost-only, synthetic-data preproduction demonstration. GitHub Actions passing does **not** authorize real customer files, cloud exposure, payment collection, or store API writes.

## Built and tested in the preproduction project

- Deterministic catalog comparison (SKU, title, stock, price), decimal normalization, source-row holds, duplicate protection and valid zero-stock processing
- Immutable sample intake snapshots, submission/staging file hashes, explicit tenant-scoped supplier header mappings and frozen per-job mapping versions
- Persistent local queue/worker, stable processing IDs, safe operator-reviewed retries, stale-worker detection and emergency stop
- Read-only deterministic triage, persisted advisory notes and a separately gated **optional** AI provider adapter. **No provider credentials, calls or customer data are connected.**
- Audited individual approvals, carefully restricted human batch stock review, and explicitly justified held-row exclusions that never apply the invalid value
- Independent export QA, duplicate export prevention, integrity checks at download, and a deterministic JSON customer change report
- Local Django sessions, tenant membership checks, CSRF protections, local login throttling, no-store headers and loopback-only execution
- Local per-store notifications and read receipts, plus customer-stated imported catalog confirmation and verified baseline lineage for recurring updates
- Synthetic SQLite database and workspace archives, integrity-checked restore, dry-run-first old file cleanup, and audit/operational scorecards
- 5,000-SKU synthetic benchmark, end-to-end tests, cross-store access regression cases, public repository file/secret guard
- Marketing concept and proposed pilot/business processes (not publicly hosted; not accepting signup/payment)
- Independent internal audit reconciliation across decisions and held-row exclusions, released-file SHA-256 pinning, a manual prior-snapshot recovery generator, and optional separately keyed HMAC receipts
- Read-only, disabled-by-default automation eligibility simulations that can quantify possible operator workload reduction without approving anything
- Local-only, operator-issued, expiring single-use synthetic customer invitations; **not** production invitation identity verification
- A combined synthetic preflight command that always returns production NO-GO until authorized release gates are met


## Prerequisites for a real service

| Gate | Status | Required evidence |
|---|---|---|
| Adult/business authorization | Pending | Who may own/sign accounts, contracts, banking and payment relationships; approved spending limit |
| Hosting & domain | Pending | Authorized provider, region, account and secure infrastructure |
| Customer identity | Pending | Production MFA/invitations/recovery, rate limiting, session revocation and proper tenant isolation |
| Data protection | Pending | Encryption at rest/transit, private object storage, deletion/retention, backups, malware checks and storage permissions |
| Job reliability | Pending | Durable production queue, worker fencing/leases, observability, alerts, restored backups and load/failure drills |
| External AI | Disabled | Approved provider, synthetic evaluation, privacy terms, budgets, read-only permissions and strict fallback |
| Store integration | Absent | Explicit customer authorization, least-privilege scopes, staging, rollback and independent safeguards |
| Billing | Absent | Eligible legal signatory, merchant processor and account authorization, refunds/cancellation process |
| Commercial validation | Not started | Evidence from qualified customer interviews, permitted pilots, measured costs and renewed demand |
| Independent security review | Pending | Penetration testing, threat-model review, access-control verification and written go/no-go |

## Current security and scope limitations
- **Public repository**: never push customer data or real credentials; the CI repository guard is only a first layer, not professional secret scanning.
- Django is locked to loopback and uses a development SQLite database; **it must not be exposed through a tunnel, public web server or production domain**.
- Local workspace archives are **unencrypted**, exclude the separate portal identity database and original uploads, and are NOT complete disaster recovery.
- A customer-confirmed import means only that a logged-in user asserted they imported the verified CSV. V3 has **no access to or verification of the live store**.
- Model advice is not a decision maker. A future provider cannot approve or execute operational changes, read secrets, bill customers, or send messages.
- Routine changes still require human decision or a narrow explicitly operator-triggered batch. The new autonomy simulation never executes changes. Fully unattended execution is **not proven**.
- Prices are draft ideas, not validated market rates; V3 has no customer subscriptions or revenue.
- Consumer-grade or sample-scale test success is not production certification.

## Required next release sequence
1. Confirm authorized business signatory, budget and account ownership with parent/qualified adviser if appropriate.
2. Independent technical/security review of [Threat Model](THREAT_MODEL.md) and [Hosting Plan](HOSTING_PLAN.md).
3. Provision staging using authorized accounts **only with synthetic data**; prove deployment, storage permissions, worker isolation, backup restoration and rollback.
4. Optionally connect external AI only after approval and [Evaluation Plan](AI_EVALUATION_PLAN.md), preserving read-only authority.
5. Measure performance, operational labor, robustness and exact false-positive/false-negative counts on representative fixtures.
6. Negotiate/approve contracts and data terms before any consented real-data pilot.
7. Enable payment processing, real store connections, or subscriptions **only after separate authorization and acceptance**.

**No-go stays in effect until each relevant safeguard has auditable acceptance evidence and an authorized person approves release.**
