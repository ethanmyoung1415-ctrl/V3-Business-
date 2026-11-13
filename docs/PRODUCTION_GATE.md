# V3 Production Launch Gate

**Release decision: NOT APPROVED for paying customers or live data.**

The repository now contains a working local change-control engine and a separate Django preproduction portal. Both test suites run through GitHub Actions. Passing tests is not a production security certification.

## Implemented and test-covered
- CSV validation, conservative holds, duplicate detection, valid zero-stock processing
- Immutable local staging and file-hash checks
- Local queued processing, bounded retries, fail-closed stale-worker handling
- Read-only rule-based exception triage, evidence-based operator briefing
- Operator approval with required reason and audit events
- Independent QA gating and integrity-verified CSV export
- Synthetic tenant-specific workspaces and account-scoped service authorization
- Django login, session/CSRF checks, per-store membership checks, private local uploads
- Separate customer submission and operator review interface, local polling command
- Tenant-specific engine processing and authorized customer download
- Locally verified SQLite backup/restore (database only; not full disaster recovery)
- Synthetic end-to-end and regression tests in supported Python versions

## Hard blockers before launch
1. **Authorized commercial accounts:** A responsible adult/legal signatory may be required to open/operate banking, hosting, payment and provider accounts. Obtain permission and choose business ownership and tax treatment.
2. **Production identity:** Approved account creation/invites, MFA or equivalent safeguards, rate limiting, secure account recovery, access revocation, session/device security and user audits.
3. **Production data protection:** TLS, encrypted file storage, tenant isolation at database/object-store/worker layers, signed links, malware scanning, retention/deletion and appropriate customer data agreements.
4. **Reliable infrastructure:** Production database and task queue, monitoring/alerts, idempotent processing, graceful shutdown, retry/dead-letter policy, fault injection and restore drills covering files and databases.
5. **External integrations:** Any Shopify/store access requires least-privilege authorization and explicit customer approvals. No live-store write may be enabled before independent testing and scope approval.
6. **Optional AI investigator:** A paid/provider-authorized AI integration, model evaluation, privacy terms and a strict no-action boundary. Model advice cannot approve changes.
7. **Business operation:** Contracts, pricing/limits, payment processing, refunds/cancellations, support/security incident workflow, liability arrangements and customer onboarding.
8. **Measured performance:** Accuracy and false alarm rates on representative datasets, vulnerability assessment, load testing, availability evidence and user-acceptance testing.
9. **Privacy/security review:** Independent technical review before handling real customer data and documented owner acceptance.

## Current limitations
- The Django portal runs locally with SQLite. Its authenticated pages are a demonstration, not a hardened hosted service.
- The local operational queue and portal worker are not a production multi-worker system.
- All changes still require an operator approval; exception-only supervision and safe low-risk auto-approval under customer policy are not yet implemented.
- No real billing, customer communications, Shopify integration, provider-connected AI, security monitoring or autonomous customer onboarding.
- Database backup does not include the uploaded originals, staged files or exports.
- This repository is public. Keep client files, credentials and confidential business information out of version control.

## Go/no-go rule
No real customer data, payments or external store actions until all relevant launch gates have documented evidence and are explicitly accepted by the business's authorized adult/legal signatory and technical operator. Do not remove tests or bypass safeguards to ship faster.

See [PORTAL_DEMO.md](PORTAL_DEMO.md) and [OPERATOR_PLAYBOOK.md](OPERATOR_PLAYBOOK.md).
