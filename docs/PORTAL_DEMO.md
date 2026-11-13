# V3 Preproduction Web Portal Demo

**This is an engineering demonstration, not a production deployment. No real customers, paid subscriptions, credentials, or live-store integrations.**

## Requirements
- Python 3.10+ with the latest supported security patch
- Local development machine; no public tunnel or internet exposure

## Setup (macOS/Linux)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-portal.txt
export V3_LOCAL_DEV=1
python manage.py migrate
python manage.py seed_portal_demo --synthetic-only
python manage.py runserver 127.0.0.1:8000
```
Save the randomly generated demo credentials shown **once** in the local terminal. Do not paste them into GitHub or a chat.

In a second terminal in the same environment:

```bash
export V3_LOCAL_DEV=1
python manage.py run_catalog_worker --interval 3
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` and set the environment flag with `$env:V3_LOCAL_DEV="1"`.

## Demo sequence
1. Visit http://127.0.0.1:8000/login/ and sign in as `v3-demo-a`.
2. Upload two fictional CSV files. A baseline must contain `sku,title,price,stock` headers. Supplier updates need `sku` and any subset of the other supported fields.
3. The local worker should process the file into its store-specific workspace. Refresh the job page to see status `review`.
4. Log out and sign in as `v3-demo-operator`. Approve or reject changes, providing reasons.
5. Once all decisions are resolved and there are no holds, prepare an export.
6. Sign in again as the correct store customer. Download the independently verified CSV.
7. Log in as `v3-demo-b`: that account must not see or download Store A's job.

Example baseline:

```csv
sku,title,price,stock
A,Sample,10,5
```

Example update:

```csv
sku,stock
A,0
```

## What is implemented
- Django's built-in login, session and CSRF protections
- Store membership checks for every view
- Validated CSV uploads into private local disk storage
- Tenant-specific processing databases and staged snapshots
- Operator-only review and audited decisions
- Independent QA before export and verification on download
- Synthetic user seeding and a local polling command
- Automated tests of cross-customer isolation and denied actions

## Not implemented / not approved
- Hardened production hosting, accounts and network access
- Encrypted file storage, data-retention and deletion policy, malware scanning
- Production queue, task retry strategy, backups of all file artifacts and incidents
- Email delivery, automated customer support, Shopify API changes
- Customer pricing, payment checkout, subscriptions or contractual acceptance
- Live AI vendor integration, AI auto-approval or autonomous customer-impacting actions
- Independent penetration testing, load testing and actual pilot acceptance

The current SQLite and development server are not meant for internet-facing use. Production requires a reviewed infrastructure design, authorized account holders, TLS, database/storage permissions and incident response.

Run both test suites after any changes:
```bash
python -m unittest discover -v -p 'test_*.py'
python manage.py test catalog_portal
```
