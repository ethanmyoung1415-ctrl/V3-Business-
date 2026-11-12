# V3: Production launch gate

Status: **NOT APPROVED FOR LIVE CUSTOMER DATA**. Current release is a single-user, local, sample-data prototype.

## Work already implemented
- Deterministic SKU-level catalog validation, exception holds, change review and reasoned approvals
- Persistent queue with idempotent enqueue, bounded retries, and fail-closed stale leases
- Local browser console; explicit export after all decisions and holds resolve
- Read-only deterministic triage with cited evidence from the source rows
- Independent reconciliation of approved exports before files are released
- GitHub Actions unit/regression testing

## Non-negotiable production blockers
1. **Identity and authorization:** Customer and operator accounts, enforced RBAC and fresh permission for consequential actions; password and session handling; authenticated file transfer.
2. **Tenant isolation:** Every queue job, database row, file, log, export, and payment record belongs to one tenant. Cross-tenant tests must pass.
3. **Storage security:** Private repository, encrypted data at rest, secure transmission, encrypted/verified backup and restore, strict retention/deletion, malware/file-size screening, secrets management, access logs.
4. **Operational reliability:** A durable production queue with isolated workers, graceful restarts, idempotent deliveries, alerts, dead-letter handling, rate limits, observability, incident response and recovery drills.
5. **AI policy:** AI produces explanations or suggested resolutions only. Rule-based checks and customer/operator approvals override models. No model may access credentials or independently authorize account/price changes.
6. **Integrations:** Explicit customer authorization for Shopify (if chosen), least-privilege scopes, staging/sandbox validation, customer import approvals and rollback plans.
7. **Billing and legal:** Business/contract owner, payment processor and banking verified, written service agreement, privacy/data processing notices, support commitments, lawful handling of customer data.
8. **Product acceptance:** Repeatable representative-file tests, security review, performance/load testing, independent QA benchmarks and controlled paid pilots.

## Service boundary
The current software neither modifies live stores nor delivers files to customers. It should not be marketed as autonomous production software. A human must still supervise initial pilots.

## Deployment decisions requiring account owner
- Hosting region/platform and ownership of hosting/payment accounts
- Company/legal signatory and payment processor setup
- Exact customer data types, retention rules and target integrations
- Security/privacy requirements and approval of going live

## Release rule
Do not label V3 production-ready until all blockers are documented, verified and signed off with evidence. Passing unit tests is necessary but not sufficient.
