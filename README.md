# V3 Operations Guard

An early-stage, **offline-only** supplier catalog change-control engine.

## Current status
This is a prototype, **not** a customer-ready or autonomous hosted service. Do not upload real customer data or connect it to a live store.

## What it does
- Compare baseline and supplier-update CSVs keyed by SKU
- Validate headers, prices, quantities, duplicates, blanks, and unknown SKUs
- Preserve valid zero-stock changes and prevent blank values from deleting data
- Put all proposed changes through explicit operator approval or rejection
- Block exports when unresolved holds or pending decisions remain
- Keep a local SQLite audit trail and SHA-256 source hashes
- Export approved full-catalog snapshots, never overwrite originals

## Local setup
Requires Python 3.10 or newer. No third-party packages required.

```bash
python -m unittest -v test_engine.py
python engine.py --db v3.sqlite3 ingest examples/baseline.csv examples/supplier_update.csv
python engine.py --db v3.sqlite3 review JOB_ID
python engine.py --db v3.sqlite3 decide CHANGE_ID approved --actor operator --reason "Verified"
python engine.py --db v3.sqlite3 export JOB_ID approved.csv
```

## Current limitations
- No customer authentication, tenancy isolation, encryption, safe file upload, or production hosting
- No AI operations manager, scheduler, email delivery, billing, Shopify API, or dashboard
- No automated approval; every change requires explicit human review
- A held record must be corrected by restarting a job with corrected source files
- Only simple SKU/title/price/stock CSVs; no variants, supplier mappings, currencies, or Shopify-specific CSV guarantees
- Tests are initial checks, not proof of operational or data safety

## Production milestones
1. Expand validation tests for malformed CSV and business rules
2. Add customer isolation, encrypted storage, file-retention rules, incident response and backups
3. Add queue/scheduler with idempotent retries, monitoring, and structured exception review
4. Implement deterministic validations and separate QA before any selective automation
5. Build operator dashboard and customer-facing secure intake and delivery
6. Conduct staged pilots with customer approval and no direct live writes

**Operating principle:** AI executes routine work, software enforces safety, humans handle judgment and customer commitments.


## Local operator console (prototype)
After queuing and analyzing sample files, start:

```bash
python operator_dashboard.py --db v3.sqlite3 --actor operator
```

Open the printed local URL (normally http://127.0.0.1:8765/). Review queued and failed work, open jobs, and approve or reject proposed changes with a recorded reason.

**Never expose the dashboard to the internet or a tunnel.** It is bound to `127.0.0.1`, has a CSRF token and HTML escaping, but **no authentication, authorization, tenant isolation, or hardened production deployment**. Use synthetic data only. No automatic export, customer communication, or store write is enabled.

Run `python -m unittest discover -v` before trying it. Check GitHub Actions for the latest CI result.


## Current milestone: local automated operations and independent verification

The project now includes:
- `worker.py` — optional polling worker for previously queued files, with no approval/export permissions
- `app.py` — starts the local dashboard and worker together; stops the worker when the dashboard stops
- `triage.py` — evidence-based, deterministic exception explanations; **not an LLM** and never an approval authority
- `qa.py` — independent output reconciliation against preserved baseline and approved changes
- `test_workflow_safety.py`, `test_triage.py`, and `test_qa.py` — safety and correctness regression tests

### Sample-only walkthrough
```bash
python -m unittest discover -v
python operations.py --db demo.sqlite3 enqueue examples/baseline.csv examples/supplier_update.csv
python app.py --db demo.sqlite3 --actor local-operator
```
Open the local URL displayed in the terminal. The worker processes the queued CSV and presents pending changes and triage recommendations. Human approvals require reasons. To export, first resolve all pending decisions and holds, then use `engine.py export` and run `qa.py` on the resulting file. Only verified outputs should ever be used for a future customer pilot.

### Critical deployment limitations
This remains a **single-user, local, synthetic-data prototype**. Do **not** expose the web console to the network or put real customer data in it. It has no customer accounts, authorization, tenancy, encrypted data lifecycle, payment integration, production-grade web security, continuous uptime, or provider-approved AI integration. The repository is public. Never commit customer files, secrets, tokens, or personal data. Before production, have an experienced technical/security reviewer evaluate the architecture, threat model, storage, backups, access controls, recovery tests, and contractual obligations.
