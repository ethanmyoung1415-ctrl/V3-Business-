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
