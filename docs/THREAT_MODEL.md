# V3 Threat Model — Engineering Review Draft

**Classification:** unreviewed design document for a synthetic, localhost-only prototype. It does not certify production safety.

## Assets to protect
Customer catalog files and supplier updates; SKU/price/stock information; operator approvals, reasons, source hashes and audit records; identity/session state; export files; future billing and provider credentials.

## Current data flow
1. Authenticated account receives a store membership (Django test environment).
2. Upload form validates CSV, optionally using a store-bound explicit supplier profile.
3. A submitted-file hash is stored and verified before the worker stages the bytes.
4. Per-store engine SQLite databases process canonicalized rows and preserve previous values.
5. Duplicate/unknown/blank values are held. The operator may exclude a held source record (never apply its value), with an audited reason.
6. Every proposed change requires an explicit decision; narrowly bounded nonzero stock adjustments may be approved in one **human-triggered** batch.
7. Independent QA verifies the generated CSV before status becomes ready.
8. Only members of that store can download the verified export and evidence-based report.
9. A customer can **claim** it imported the result externally, establishing the next catalog baseline. V3 does not validate the actual remote store import.

## Trust boundaries and threats

| Boundary | Potential attack | Existing preproduction safeguard | Missing launch control |
|---|---|---|---|
| Public network -> portal | Unauthorized remote access | Loopback-only middleware and fail-closed release gate | Reviewed HTTPS ingress, WAF, security headers, MFA, production rate limits |
| Session -> store | Cross-tenant file access | Django authenticated membership checks and separate demo workspaces | Central enforced tenant IDs in durable DB, object store, queues and every service |
| Customer -> upload | CSV injection, malformed rows, huge files | File-size/header/type/row/price/stock checks, formula-prefix screening | Malware scanning, resource quotas, validation fuzzing and secure object storage |
| Uploaded file -> worker | File changes after submission | Recorded SHA-256 and immutable local staging | Immutable object storage, signed upload sessions, retention and lifecycle controls |
| Supplier text -> model | Prompt injection and misleading advice | No model tools, strict output validation, deterministic risk override | Vendor privacy review, model evals, monitored rate/budget controls, approved provider |
| Operator -> state | Incorrect approval or invalid exclusion | Role checks, required reasons, audit events, QA blocks | MFA, scoped delegation, audit protection, dual approval for sensitive actions |
| Engine -> exported CSV | Unapproved or tampered edits | Immutable baseline, held-row exclusions preserve original, separate QA, export hashes | Transactional delivery, durable job ledger, reconciliation under concurrency |
| Worker -> queue | Crash, replay or duplicate work | Stable IDs, conservative retries, stale-job failure states | Durable queue with leases/heartbeats, worker fencing, incident alerts, recovery drill |
| Browser -> download | Data leakage / stale session | Store membership and verification on download, no-store headers | Short-lived signed links, audit access logging, session hardening and CDN rules |
| Local disk -> backup | Loss, theft, partial restore | Synthetic archive and hash-checked restore | Encrypted offsite backups, key rotation, portal DB and upload restoration, RPO/RTO exercises |
| Repository -> public | Secret or real catalog committed | Ignore rules and CI guard for obvious token/file patterns | Private production repository, repository permissions, professional secret scanning |

## Fail-closed rules
- A catalog cannot be exported while pending changes or unresolved holds remain.
- Excluding a bad row requires explicit operator justification and never applies the bad value.
- Model responses are suggestions only and may not grant approval, execute tools, access credentials or send customer data.
- Interrupted exports can only be recovered after independent QA and a committed engine audit.
- Invalid file hashes, unknown schema, insufficient permissions, or another tenant's job block processing.
- The emergency stop blocks new writes and downloads while preserving evidence.

## Critical current gaps
- Production database/storage encryption, password/account recovery, real MFA, customer invitations and revocation audit review.
- Security testing of cross-tenant concurrency, file service permissions, concurrent uploads, symlink races and high-volume denial of service.
- Authenticated tenant isolation not yet measured on a hosted deployment.
- Complete, encrypted backups covering portal identity DB, uploaded originals, staged files, exports and keys; verified restore sequence.
- Formal incident response, data retention/deletion terms, privacy policy and vulnerability disclosure.
- Integration authorization and billing isolation have not been designed or tested with real providers.

## Independent reviewer acceptance checklist
1. Verify identity roles, user provisioning and removal; test IDOR against every endpoint.
2. Fuzz upload handling; confirm unknown schemas, malicious CSV formulas and oversized data fail closed.
3. Perform live race tests: simultaneous submissions, retries, exclusions, approvals and downloads.
4. Confirm that no model-generated output may change authorization or bypass QA.
5. Validate end-to-end backups, restores, access logs, encryption, incident stop and key rotation.
6. Confirm no public launch or real data until owners formally accept every relevant risk and provider term.

**Do not process real customer information based on this document alone.**
