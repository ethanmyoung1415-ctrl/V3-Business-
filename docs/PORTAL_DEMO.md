# V3 Local Portal Demo — Synthetic Data Only

**Never run this server publicly or submit real customer data, live credentials or payment details.**

## Setup

Python 3.10+ on macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-portal.txt
export V3_LOCAL_DEV=1
python manage.py migrate
python manage.py seed_portal_demo --synthetic-only
python manage.py runserver 127.0.0.1:8000
```

For Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` and set `$env:V3_LOCAL_DEV="1"`.

The seed command prints randomly generated local demo passwords **once**. Do not paste them into chats or repositories.

Start the worker in a second terminal (same environment):

```bash
export V3_LOCAL_DEV=1
python manage.py run_catalog_worker --interval 3
```

Open http://127.0.0.1:8000/login/ .

## End-to-end recurring supplier workflow

1. Sign in as `v3-demo-a` (fictional merchant).
2. Upload baseline CSV and supplier update CSV for its store.
3. The background worker validates file hashes, analyzes changes, stores read-only advice and places exceptions in the operator queue.
4. Sign out and sign in as `v3-demo-operator`. Review previous/proposed values and evidence.
5. Approve/reject with reasons. Held rows can be **excluded without applying them** when their original value should remain unchanged.
6. With no unresolved holds or decisions, prepare the independently QA-verified export.
7. Sign in again as Store A. Download the CSV and evidence-based JSON change report.
8. **Pretend** to import the CSV into an imaginary store (no actual import exists). On the released job page, explicitly click `I confirm this file was imported into my store`.
9. Submit a second supplier update and select `Reuse last customer-confirmed catalog`. Do not upload another baseline.
10. Confirm that this second job compares against the first *verified and customer-confirmed* output, not an assumed remote store state.
11. Sign in as `v3-demo-b` and confirm that Store A's jobs and files are inaccessible.

Example baseline:

```csv
sku,title,price,stock
A,Sample,10,5
B,Another,15,8
```

Example supplier update:

```csv
sku,stock
A,0
B,
```

A zero-stock update is valid and still requires explicit approval. The blank value is held and does not erase B's stock. The operator can exclude that held row after verifying the source, then export the unaffected approved changes.

## Supplier profiles

Suppliers may call fields `Item Code`, `Qty Available` or similar. A local administrator can create a `SupplierProfile` for the right store in Django admin with a JSON mapping such as:

```json
{"sku":"Item Code","stock":"Qty Available"}
```

The customer may select only active profiles for **their own store**. V3 saves a frozen copy of the mapping for that specific job. No heuristic guesses are made about price or stock. Creating or changing profiles through a live production UI is not yet available.

## Operator reliability commands

```bash
python manage.py reconcile_stale_jobs --dry-run
python manage.py reconcile_notices
python manage.py emergency_stop --enable
python manage.py emergency_stop --disable
python manage.py purge_demo_uploads --days 30
```

The emergency stop prevents new processing and customer downloads until explicitly cleared. The purge command **does not delete anything by default**; `--confirm` is required and is limited to old terminal synthetic source uploads.

Separate offline tools are available for synthetic workspace backup/verification in `workspace_archive.py` and SQLite backup/restore in `backup.py`. These archives are **not encrypted**, and neither constitutes complete production disaster recovery.

## Tests

```bash
python -m unittest discover -v -p 'test_*.py'
python manage.py test catalog_portal
python manage.py check
python manage.py makemigrations --check --dry-run
python repo_guard.py
```

GitHub Actions runs both test suites and the repository guard. The local developer server is not a hosted service. External AI, emails, payment subscriptions, real e-commerce API actions and actual customer-data processing remain disabled.
