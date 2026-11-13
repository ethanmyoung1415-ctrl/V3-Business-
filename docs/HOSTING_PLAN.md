# V3 Production Architecture Proposal — Not Deployed

**Goal:** migrate the verified local workflow into a commercially usable managed catalog service without weakening protections. No provider or spending authorization has been given.

## Recommended separation of responsibility
- **Web application:** Django web app behind approved HTTPS/TLS, with secure login, MFA or equivalent, invite/recovery flows, CSRF and tenant-scoped authorization.
- **Relational database:** managed PostgreSQL for users, stores, jobs, policy versions, approvals, audit events, subscriptions and outbox. Use migrations and backups.
- **Private object storage:** encrypted storage for source CSVs, normalized snapshots, reports and verified exports. Unique tenant-prefixed keys, least-privilege access and lifecycle rules; never serve via a public bucket.
- **Job execution:** durable queue and isolated workers that claim and reconcile jobs using stable IDs, lease fencing and bounded retries.
- **Advisory processor:** separate read-only worker. Provider output passes through the strict schema and deterministic validation. No model has approval, database write, billing or store-import authority.
- **Independent QA:** separate verifier compares approved changes with the preserved baseline; only verified artifact hashes become downloadable.
- **Monitoring:** logs without sensitive customer data, queue latency, stale processing, export failures, customer isolation violations, rate limits and uptime/error alerts.
- **Secrets:** provider-managed secret store, no secrets in GitHub, source files or model prompts. Separate credentials and permissions for worker, web and deployment.

## Logical execution
Customer -> HTTPS upload -> tenant-authorized record -> private object store
-> durable queue -> deterministic validation -> advisory read-only findings
-> operator review -> QA reconciler -> private verified output
-> customer-initiated download -> optional customer import confirmation
-> next supplier cycle.

## Production acceptance gates
1. Authorized adult/business signatory has approved provider accounts, budget and legal obligations.
2. A security reviewer signs off on hosting, identity, encryption, data retention and tenant isolation.
3. Synthetic staging uses the same architecture as production and shows successful clean deployment.
4. Migrate from local SQLite with reconciliation tests, schema version control and rollback procedures.
5. Complete threat-model test plan and destructive concurrency/fault tests in staging.
6. Verify full backups and restores including portal database, objects, approval audit and report hashes.
7. Establish support process and service-level commitments based on measured performance.
8. Run a limited authorized pilot with customer data only under agreed privacy/security terms.
9. Enable billing and any customer/store connections only after separate approval and a repeatable value test.

## Spending guardrail
Prepare an itemized cost estimate for web, database, object storage, queue, monitoring, model usage, payment fees, domain and professional services **before ordering anything**. Set approved monthly/total limits, billing alarms and cancellation ownership.

## Decisions the owner/parent needs to make
- Who is authorized to sign provider and customer agreements and pay bills?
- Which hosting region, data-retention periods and providers satisfy customer needs?
- Whether external AI receives *any* customer content, and under what agreement and budget.
- Whether any future store API is read-only or has controlled write privileges.

## Deliberately absent
No production container image, public endpoint, cloud account, payment processor, Shopify token, customer credentials, provider API key or launch approval is created by this plan.
