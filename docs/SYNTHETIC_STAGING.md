# V3 reproducible synthetic staging rehearsal

**Not a public staging deployment.** This environment packages and tests the
preproduction application without enabling external access, accounts or billing.

## What this rehearsal verifies
1. The repository installs a declared Django version in a clean Python 3.13 image.
2. The test container runs as a non-root user.
3. No network port is published and the test runner does not start a web server.
4. The container has no configured external AI provider, store API or payment processor.
5. The Django portal's full synthetic test suite passes.
6. A separate synthetic portal/database/upload/workspace recovery drill passes.

The GitHub workflow `Synthetic container rehearsal` runs the image with
`--network none` so code cannot accidentally call external services during
this test.

## Commands (if Docker is installed)
From the repository root:

```bash
docker build -f deploy/Dockerfile.test -t v3-synthetic-tests:local .
docker run --rm --network none v3-synthetic-tests:local
docker run --rm --network none v3-synthetic-tests:local python recovery_drill.py
```

No secret, login, bank account, or cloud subscription is required.

## Why this isn't hosting
This image intentionally starts a test command, **not** a web process.
There is no exposed port, domain, customer enrollment, managed database,
HTTPS ingress, encrypted object storage, production queue, infrastructure
identity, billing or incident alerting.

Do not change the container to host a public service before authorization
and security review. Production will require an approved architecture,
PostgreSQL/managed database migrations, object store, durable workers,
MFA, rate limits, multi-tenant authorization tests and recovery drills.

## Local recovery check
Run `python recovery_drill.py` to create a fictitious job, snapshot the portal
SQLite database and source/output files, restore to a new temporary location
and verify content hashes, SQL integrity and exact synthetic records.

The underlying `local_recovery_bundle.py` is deliberately
**unencrypted and synthetic-data-only**. It refuses to overwrite backups,
rejects symlinks and unsafe archives, and requires an explicit synthetic-only
acknowledgment. Do not use it with real customer information.

## Next real staging requirements
Authorized account owner, documented budget, hosting region/provider,
encrypted database and object store, secure identity management, worker
permissions, monitoring, approved data-retention and legal obligations.
An independent technical review remains mandatory.
