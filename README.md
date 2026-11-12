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
