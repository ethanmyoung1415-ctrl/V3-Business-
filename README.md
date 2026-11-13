# V3 Operations Guard

**Preproduction status: working local synthetic-data prototype, not a public service.**

V3 is a proposed managed catalog-change review service for retailers that receive recurring supplier CSVs. Its software compares records, holds ambiguous changes, presents operator exceptions, and returns independently verified CSVs and change reports.

It is **not** a paid business or secure public customer portal. Do not upload real customer data, secrets or live-store credentials. The repository is public.

## Run local tests

Python 3.10+ is required.

```bash
python -m unittest discover -v -p 'test_*.py'
python demo.py
python benchmark.py --rows 5000
```

The standard-library demo runs fictional stores and verifies isolation, approval and QA. For a customer/operator browser demo see [Portal Demo](docs/PORTAL_DEMO.md).

The project uses three automated GitHub Actions workflows:
- Engine, queue, QA and synthetic benchmarks on Python 3.10 and 3.13
- Django portal login, upload, store isolation, migration and recovery tests on Python 3.10 and 3.13
- Public-repository guard against obvious committed secrets and local business files

[View current GitHub Actions](https://github.com/ethanmyoung1415-ctrl/V3-Business-/actions).

## Demonstrable features
- Local customer login with store-scoped access; demo user accounts created only for synthetic use
- CSV validation, source hashes, immutable staging and explicit supplier header mappings
- Source rows with blanks, duplicates or unknown SKUs held, not silently applied
- Explicit, auditable operator decisions and safe exclusion of a held source row
- Human-triggered batch review only for narrowly bounded nonzero stock adjustments
- Read-only deterministic advisory notes, provider-disabled model adapter with schema enforcement
- Stable job IDs, crash/retry reconciliation and independent export QA
- Private in-app alerts, per-user read receipts and failure-notice recovery
- Verified CSV and JSON change-report downloads
- Customer confirmation of an external import and safe reuse of that confirmed catalog as the next baseline
- Local emergency stop; dry-run-first source retention cleanup
- Synthetic verified workspace archive/restore and independent local database backup
- Operator metrics and incident/security handoff documentation

## Architecture overview

| Component | Responsibility |
|---|---|
| `engine.py`, `qa.py`, `reporting.py` | Deterministic catalog state, approvals, independent reconciliation and reports |
| `mapping.py`, `intake.py` | Explicit source header mapping and protected local file snapshots |
| `operations.py`, `worker.py`, `inbox.py` | Local offline queue and sample-file processing |
| `triage.py`, `advisor.py`, `advice_jobs.py` | Deterministic review advice and persisted recommendations |
| `provider_openai.py` | Optional **disabled** read-only provider adapter; no API calls by default |
| `catalog_portal/`, `v3portal/` | Local Django portal, tenant-scoped workflows, private notices and state management |
| `backup.py`, `workspace_archive.py` | Synthetic local backups; **not encrypted production recovery** |
| `repo_guard.py` | Basic public repository secret/file checks |
| `demo.py`, `benchmark.py` | Fictional full-process and workload tests |
| `site/index.html` | Prelaunch marketing concept, no signup or tracking |

## Absolute safety constraints
- No public hosting: the portal fails closed without local-only configuration and rejects non-loopback traffic.
- No real-store imports: even when a customer confirms an import, V3 **only records their statement**.
- No autonomous model approval: recommendations cannot change catalog state.
- No customer data or revenue is present in the prototype.
- No payment account, billing, email/SMS service, store API key or real AI provider is connected.
- A verified CSV cannot be downloaded if independent reconciliation fails.

## Additional independently tested preproduction work

- `audit_integrity.py` checks that every decided change has a matching recorded human decision and that held rows match documented exclusions. Export and post-release verification reject inconsistent audit evidence. This is database-consistency checking, **not cryptographic proof against a privileged administrator**.
- `manual_rollback.py` prepares a prior baseline as an explicit operator-reviewed *manual recovery* file; it never imports anything into a live store.
- `autonomy_simulator.py` measures which extremely low-risk stock changes *might* become eligible for future automation. It never approves changes. The Django operator can inspect a read-only preview.
- `release_preflight.py --strict` runs the fictional end-to-end and anomaly checks and **always reports production NO-GO** until external release gates are met. CI runs this command.
- `release_receipt.py` provides optional HMAC-SHA256 file integrity receipts, requiring a separately managed local signing secret. It does not certify live-store import.
- Local-only single-use customer invitations can be issued by authorized store operators, with no public signup or email service.

See [Automation Simulation](docs/AUTOMATION_SIMULATION.md), [Manual Recovery](docs/MANUAL_RECOVERY.md),
[Release Receipts](docs/RELEASE_RECEIPTS.md), and [Local Invitations](docs/LOCAL_INVITATIONS.md).

## Restricted Excel supplier intake

The local portal can now accept standard CSV or a deliberately limited,
single-visible-sheet `.xlsx` workbook. Formula cells, macros, links, hidden/
merged data, styled numeric/date cells, ambiguous multiple sheets, and numeric
SKU cells are rejected rather than guessed. Original uploaded workbook bytes
remain private and hashed; the comparison engine receives only a separately
validated CSV. Custom supplier-header mappings currently require CSV.

See [XLSX Intake](docs/XLSX_INTAKE.md). This is **not** support for arbitrary
Excel files, and real customer workbooks remain prohibited until security
review and controlled pilots.

## Reproducible preproduction rehearsal

V3 can now be built in a **non-root, network-isolated test container** and
checked without cloud accounts. The GitHub workflow
[Synthetic container rehearsal](.github/workflows/container-smoke.yml) builds
`deploy/Dockerfile.test` and runs the Django tests plus a full fictional
recovery drill. No image is published, no port is exposed and no public server
starts.

The synthetic-only recovery tools now include a combined archive of the local
portal database, original uploads, and per-store workspaces/exports, with
integrity-checked restoration to a new location. This archive is **not encrypted**
and must never be used with real customer data.

Local queue-admission limits help prevent accidental submission floods. They
are explicitly not sufficient as production-wide distributed rate limits.

See [Synthetic Staging Rehearsal](docs/SYNTHETIC_STAGING.md) for exact
commands and limitations. The existing public-deployment safety gate remains
enabled.

## Critical remaining commercial work
See [Production Gate](docs/PRODUCTION_GATE.md), [Threat Model](docs/THREAT_MODEL.md), [Hosting Plan](docs/HOSTING_PLAN.md), [AI Evaluation Plan](docs/AI_EVALUATION_PLAN.md) and [Preproduction Handoff](docs/PREPRODUCTION_HANDOFF.md).

The next phase needs authorized hosting/provider/payment accounts, appropriate adult/legal arrangements, a professional security review, staging deployment, customer agreements and pilot evidence. Passing synthetic tests is not permission to handle real store data.

**Design principle:** routine work is automated, evidence is preserved, and consequential changes remain controlled by enforceable rules and authorized humans.
