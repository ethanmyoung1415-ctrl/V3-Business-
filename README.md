# V3 Operations Guard

**Status: locally tested engineering prototype — NOT production or customer-data ready.**

V3 is an AI-assisted *managed catalog change-control service* under development. Its current implementation is a standard-library Python prototype. It can compare synthetic supplier catalog updates, hold dangerous changes, generate operator decisions, and independently verify reviewed output. It cannot run a paid, autonomous hosted business yet.

## Quickest demonstration (no accounts or dependencies)

Python 3.10+ required:

```bash
python -m unittest discover -v -p 'test_*.py'
python demo.py
python benchmark.py --rows 1000
```

The demo runs two isolated **fictional** customer jobs, explicitly approves their synthetic updates, exports verified CSVs, and tests that customer B cannot read customer A's job. Nothing is sent online.

## Authenticated preproduction web portal

A separate Django-based, **local-only** portal now supports mock customer logins, tenant-scoped uploads, operator review and verified downloads. Its server is not approved for the public internet. See [Portal Demo](docs/PORTAL_DEMO.md). The portal uses a local polling worker and has no payment processor or live e-commerce integration.

## Local operator console

```bash
python operations.py --db demo.sqlite3 enqueue examples/baseline.csv examples/supplier_update.csv
python app.py --db demo.sqlite3 --actor local-operator
```

Open the local address printed in the terminal, normally http://127.0.0.1:8765/.

Use the dashboard to review exceptions, enter a reason for every approval or rejection, and download a CSV only after all holds and pending decisions are resolved. An independent QA comparison is mandatory before export.

A separate *synthetic* local inbox can be enabled:

```bash
python app.py --db demo.sqlite3 --inbox ./incoming --actor local-operator
```

For each sample job, create a subdirectory containing `baseline.csv`, `update.csv` and an empty `READY` file. The worker processes each ready folder once, changes the marker to `QUEUED`, and places the job in the review queue. Do not use this with actual customer uploads.

## Current components

| Module | Role |
|---|---|
| `engine.py` | Catalog validation, conservative holds, audited human decisions |
| `intake.py` | Private local CSV snapshots, file hashing, symlink rejection |
| `operations.py` | Persistent queue, deduplication, bounded retries, stale-worker handling |
| `inbox.py`, `worker.py` | Optional local polling intake and analysis |
| `operator_dashboard.py`, `app.py` | Local review and export UI, no remote access |
| `triage.py`, `advisor.py` | Rule-based explanations and a future read-only AI response boundary |
| `qa.py` | Independent verification of final files |
| `metrics.py` | Operator attention summary and failure counts |
| `workspaces.py` | Separate databases for *simulated* customers |
| `identity.py`, `secure_operations.py` | Password/session and tenant-scoped service authorization, **not yet integrated with browser** |
| `backup.py` | Offline database-only backup and integrity-checked restore |
| `supervisor.py` | Ranked operator exception briefings, no autonomous decisions |
| `catalog_portal/`, `v3portal/` | Django preproduction login, upload, review and download workflow |
| `demo.py`, `benchmark.py` | Synthetic workflows and workload checks |

## Safety model

- Unknown SKUs, duplicate rows, blanks, unsafe spreadsheet text and other ambiguities are held.
- Legitimate zero-stock updates are supported, but still require approval.
- No autonomous approvals, customer emails, billing, account access, live Shopify actions, or remote integrations.
- A verified export never overwrites an existing file and cannot be repeated for the same job.
- Local browser is loopback-only. **It has no real login or production isolation.**
- The repository is public; do not commit secrets, customer data, or real catalog files.
- Database backups **do not include** the staged CSV inputs and exported files.

## Development / release checklist

See [Production Gate](docs/PRODUCTION_GATE.md), [Operator Playbook](docs/OPERATOR_PLAYBOOK.md), and [GitHub issues](https://github.com/ethanmyoung1415-ctrl/V3-Business-/issues).

**Before any real customer data:** complete identity integration, enforced tenant isolation, secure hosted intake, file retention and deletion, encrypted storage and backups, monitoring, disaster recovery, legal/payment arrangements, and an independent security review. Demonstrate measured accuracy and customer value in controlled pilots.

**Design principle:** automation executes routine work; deterministic safeguards enforce limits; people authorize consequential changes.

## Latest local milestones
- The portal now rejects unsafe or unprocessable CSVs before creating jobs and explicitly blocks non-loopback traffic. Public deployment is disabled at the configuration level.
- Portal events record submissions, review decisions, export verification, downloads and synthetic-upload deletion. The operator sees prioritized jobs across stores they are authorized to manage.
- A small-stock **human-triggered** batch approval exists, limited to nonzero stock movements of at most 5 units and 10%; price, title, zero-stock and unusual changes remain individually reviewed.
- A dry-run-first local retention command can delete old terminal **synthetic source uploads**, but this is not complete customer-data erasure.
- A stale-portal-job recovery command marks interrupted processing failed for investigation rather than retrying silently.
- A proposed marketing concept is in [site/index.html](site/index.html), with no tracking, data collection or checkout.
- Commercial pilot prerequisites and adult account responsibilities are documented in [PILOT_PLAN.md](docs/PILOT_PLAN.md) and [ADULT_HANDOFF.md](docs/ADULT_HANDOFF.md).

Neither the engine nor portal has been tested or approved as a commercial hosted service. No real customer data should be processed.
