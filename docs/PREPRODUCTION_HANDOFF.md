# V3 Preproduction Engineering Handoff

**Status:** local-only preproduction demonstration. **Not approved for real customer data, payments, deployment, or live-store changes.**

## Engineering completed in the latest development cycle
- Upload validation now rejects unsafe formulas, malformed/invalid records, duplicate baseline SKUs and invalid numeric values *before* saving a job.
- Portal configuration explicitly refuses non-local deployment; HTTP access is restricted to loopback, with local-only login throttling.
- Structured job audit events record submissions, processing, failure, decisions, exports, verified downloads and demo-upload retention.
- Operator dashboard shows authorized cross-store exception priorities and real job-volume/status KPIs, with revenue intentionally unset.
- Local retention cleanup defaults to dry-run and requires explicit confirmation; only old terminal synthetic source files are eligible.
- Stalled processing jobs are marked failed with audit events and require investigation rather than blind retries.
- Authorized operators can explicitly approve **only** small nonzero stock changes in a batch, limited to at most five units and ten percent. Pricing, titles, zero stock, holds and large updates remain separately reviewed.
- A completed engine export can be reconciled after an interrupted portal status update, but only after the existing file passes independent QA and the engine audit confirms export.
- Added synthetic workload coverage at 5,000 SKUs, more cross-tenant and review tests, and prelaunch website assets that do not collect information.
- Created a controlled-pilot protocol and adult-account handoff document.

## Verification
Two GitHub Actions suites run after changes:
1. Standard-library catalog/worker/QA tests on Python 3.10 and 3.13.
2. Django portal tests, tenant isolation, permission/CSRF tests, migrations and security checks on Python 3.10 and 3.13.

Always verify the latest commit at https://github.com/ethanmyoung1415-ctrl/V3-Business-/actions . Green unit tests validate their defined cases; they are not penetration testing, SOC 2 certification or proof that the product is safe to host.

## What can be demonstrated without additional accounts
Use [PORTAL_DEMO.md](PORTAL_DEMO.md) with fictional CSV data. A simulated customer logs in, submits files, local processing sends the job to review, a scoped operator resolves exceptions, and the customer downloads only their own independently verified CSV.

## Actual blockers before commercial launch
1. **Approval of commercial infrastructure and accounts:** hosting, domain, payment processor, any external AI/provider APIs, and budget. Some account contracts require a legally authorized adult.
2. **Real production environment:** server/database/object storage with encryption, validated tenant isolation, durable queue, secure secrets, monitoring, recovery and deployment pipeline.
3. **Independent technical/security review:** current prototype uses local SQLite and intentionally cannot be exposed publicly.
4. **Customer/legal authorization:** appropriate business signatory, customer contracts, secure data-transfer conditions, privacy/retention terms and compliance review.
5. **Real pilot proof:** customer data only with permission and after infrastructure clearance, then measure accuracy, false alarms, labor, margins, retention and willingness to pay.

## Explicitly NOT yet present
A running cloud product, real AI model integration, payment/subscription processing, live Shopify connections, self-service public onboarding, verified uptime or revenue. These are not hidden behind a button and must not be represented as finished.

## Recommended next release sequence
1. Parent/authorized operator agrees to commercial account and budget approach.
2. Security reviewer selects/approves an architecture with tenant isolation, encryption and retention.
3. Deploy a staging environment on approved accounts using fictional data.
4. Integrate read-only AI assistance behind enforceable deterministic safety rules and evaluate its accuracy.
5. Test hosted failure/recovery, threat scenarios and customer onboarding.
6. Conduct the controlled pilots defined in [PILOT_PLAN.md](PILOT_PLAN.md).
7. Establish contracts/billing only after successful validation.

**Decision rule:** no production deployment or real customer data until the required owners explicitly approve the release and evidence is recorded.
