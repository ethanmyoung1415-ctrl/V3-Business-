# V3 — Real-world operation readiness ledger

**As of November 2026:** synthetic preproduction only. This ledger is evidence
for the next infrastructure decision, **not a release approval**.

## Verified without accounts or customer data

| Control | Implemented evidence | Current limitation |
|---|---|---|
| Catalog validation | `engine.py`, `test_properties.py`, synthetic evaluation | Real supplier format coverage not established |
| Held changes and explicit review | `audit_integrity.py`, QA and batch-approval tests | Operator effort unknown on real accounts |
| Two simulated customers | Portal permission and workflow tests | Not verified with hosted database/object store |
| Original-file integrity | Intake hashing, staging, restricted CSV/XLSX conversion | No production malware-scanning pipeline |
| Delivery QA | Independent export verification, hash pinning, local receipts | No customer delivery SLA |
| Fail-closed processing | Worker failure states, stale-job review, kill switch | Not a durable distributed job queue |
| Local admission controls | `catalog_portal/admission.py` and quota tests | Counts can race across workers; needs shared atomic quotas |
| Demo identity | Django sessions, role checks, local invitations | No production MFA/account recovery |
| Fictional recovery drill | `local_recovery_bundle.py`, `recovery_drill.py` | No encryption/offsite backups, no hosted recovery |
| Repeatable build | `deploy/Dockerfile.test`, non-networked CI | Test container is intentionally not a server |
| Management visibility | Operator scorecard, health CLI, alerts | No real uptime or billing telemetry |
| Commercial validation | Draft pilot protocol and value metrics | No verified paying customers |

## Evidence needed before allowing real-world operation

1. **Authorized account holder and approved budget:** hosting, DNS, database,
   object storage, monitoring and any external model/payment provider. A
   legally appropriate adult or guardian may need to supervise contracts.
2. **Reviewed hosting design:** separate web and worker privileges, encrypted
   storage, deployment secrets, HTTPS, backend permissions, externally durable
   audit logs and tenant isolation.
3. **A real staging environment using fabricated data:** migrations tested on
   the chosen database, object storage lifecycle, concurrent worker recovery,
   email/provider controls, rollback and restore drills.
4. **Independent security testing:** authentication, account recovery, file
   upload abuse, cross-tenant object access, race/concurrency, data deletion,
   log exposure and incident handling.
5. **Commercial/legal foundation:** ownership and tax advice, service terms,
   privacy requirements, signed permissions and an approved data retention
   schedule.
6. **Controlled representative pilot:** written approval to use real supplier
   records only after the security gate, measure correctness/false positives,
   turnaround, operator time, costs and retailer retention.

## Non-negotiable release rules

- Public deployment and real customer data remain blocked in the application.
- The local container/test workflow is not a production deployment.
- An LLM may explain or recommend, but may not approve its own changes, read
  credentials or perform customer-facing actions without independent permission.
- Every delivered output requires independent QA and verified file integrity.
- No subscription charges, real cloud resources or account creation may be
  initiated without explicit authorized approval.
- Green unit tests **do not certify production security**.

## Exact next human decisions

The owner and parent/authorized adult should determine the legal account
signatory, spending cap, choice of security reviewer and permission to establish
a **synthetic-only staging account**. Only then should an engineer choose
provider-specific infrastructure and migrate local SQLite/storage to
production services.

## No-approval developer commands

```bash
python -m unittest discover -v -p 'test_*.py'
python release_preflight.py --strict
python recovery_drill.py
```

With local Docker available:

```bash
docker build -f deploy/Dockerfile.test -t v3-synthetic-tests:local .
docker run --rm --network none v3-synthetic-tests:local
docker run --rm --network none v3-synthetic-tests:local python recovery_drill.py
```

See [SYNTHETIC_STAGING.md](SYNTHETIC_STAGING.md),
[HOSTING_PLAN.md](HOSTING_PLAN.md), [THREAT_MODEL.md](THREAT_MODEL.md)
and [PRODUCTION_GATE.md](PRODUCTION_GATE.md).
