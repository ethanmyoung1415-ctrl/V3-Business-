# First Revenue Sprint — V3 (2026-11-13)

**Status: PLAN ONLY — NOT AUTHORIZATION TO USE REAL CUSTOMER DATA OR ACCEPT PAYMENT.**

## Goal
Reach a narrowly scoped, legally authorized **paid managed catalog-review pilot** as quickly as possible without weakening release safety. The company sells a done-for-you service, not a dashboard customers must operate. The initial offer is periodic supplier CSV/catalog validation and **operator-managed** correction proposals with an independently verified export. It is **not** live Shopify inventory monitoring, a live catalog update integration, or autonomous purchasing.

## Evidence currently established
- The repository describes a working synthetic-only local engine, Django portal, review queue, independent export QA, and CI checks.
- Live hosting, identity, data safeguards, external store integration, billing, legal agreements and professional security review are **not established**.
- Simulated customer feedback in a ChatGPT role-play is **not commercial validation**.
- Any existing tests should be run and verified in a trustworthy environment before relying on them. Documentation alone does not certify a deployment.

## Fastest safe path, organized by dependency

### A. Can start immediately, without external accounts or customer files
- [ ] Run full local tests and strict release preflight from README and record commit SHA, pass/fail, and reproducible commands.
- [ ] Test a fully fictional first customer end-to-end: baseline CSV, supplier CSV, held blank, duplicate SKU, zero-stock, approved and rejected changes, QA, verified export, repeat update, store isolation.
- [ ] Benchmark **actual human handling time** per file, per exception and per failed job. Don't substitute assumptions.
- [ ] Prepare a truthful one-page offer and discovery script focused on *managed supplier catalog review*. Do not promise live monitoring, autonomous changes, or ordering.
- [ ] Interview prospective shops about frequency of supplier files, existing import workflow, specific pains, willingness to pay and who authorizes catalog access; no real data requested.
- [ ] Define an enforceable trial scope: supported CSV format, maximum SKUs and suppliers, turnaround, review frequency, included exceptions, customer-side external import step, cancellation and support limits.
- [ ] Create a straightforward operator checklist and customer-facing report showing issues detected, actions taken, exceptions held and independently verified export status.

### B. Requires parent/authorized business signatory + specialists
- [ ] Confirm business structure, lawful signer, owner of bank/merchant/provider accounts, spending limit and tax/accounting plan. As founder is a minor, obtain appropriate parent/legal advice; do not infer that parental help automatically grants signing capacity.
- [ ] Have qualified counsel review customer service agreement, processing addendum, scope of delegated authority, privacy and retention policy, liability, cancellation/refunds and authorization revocation. If targeting the EU, evaluate GDPR/international data transfers.
- [ ] Obtain independent technical security review of the deployment plan, authentication, authorization, file handling, tenancy isolation, secrets, backups and incident response.
- [ ] Provision **synthetic-only** staging with approved provider/region and configuration; test isolation, data deletion, recovery, rollback, error handling and security monitoring.
- [ ] Approve the transition to a tightly controlled real-data pilot only when the review and relevant agreements are complete.

### C. First controlled paid pilot — after all relevant approvals
- [ ] Obtain signed pilot/service agreement and explicit permission for actual customer files and permitted corrections.
- [ ] Configure one customer, one agreed supplier input, narrowly limited service; no automated financial transactions or store writes.
- [ ] Perform operator-managed work, independent QA and customer-confirmed outcome; collect processing time, accuracy, turnaround and customer satisfaction.
- [ ] Set up compliant invoicing/payment processing **before collecting funds**; confirm customer accepted scope and recurring billing terms.
- [ ] Decide GO / STOP / FIX from evidence. Do not generalize from one customer to production-scale readiness.

## The three-tier strategy — staged, not currently deliverable in full
| Tier | Proposed price (not validated) | Initial scope / addition | Future authorization |
| --- | --- | --- | --- |
| Essential | €99/month | Done-for-you catalog discrepancy review and verified correction output, subject to volume caps | Written authority for catalog work |
| Managed | €249/month | Essential plus supplier contact/replenishment planning **only after capabilities and service cost proven** | Explicit supplier contact permission |
| Complete | €499/month | Managed plus purchase-order execution and delivery tracking **only after separate testing and safeguards** | Named suppliers, SKU restrictions, quantity and spend ceilings, approval/escalation, revocation and duplicate-order protection |

No subscription tier should imply that V3 has independent knowledge of physical stock. Supplier availability and store on-hand inventory are different facts. Unverified inventory corrections must be held.

## First-revenue acceptance checklist
Do not charge for promised work unless:
1. Customer-facing offer accurately matches capabilities actually deliverable.
2. Signed agreements, identity, data handling and delegated action scope are in place.
3. Secure production/pilot environment and independent technical review are approved for that limited scope.
4. Trial workflow passes documented representative tests and backup/restore and incident drills.
5. Human operator can complete the work and independent QA blocks incorrect output.
6. Billing/invoicing is properly authorized and cancellation is operational.
7. Account-level economics are measured: processing labor, support, infrastructure, returns/rework and contribution margin.
8. Responsible authorized person signs a written go/no-go for the paid pilot.

## Metrics to record from the first 10 prospects and first pilot
Prospects: qualified conversations, exact workflow, file cadence, SKU count, existing tools, decision-maker, price response, next step.
Pilots: processing time, exception rate, false positive/negative rate, rework, verified changes, delivery on-time rate, number of customer interventions, customer time saved, monthly direct cost and retained willingness to pay.

## Escalation rule
AI can classify, draft, compare and propose, but does not invent inventory facts, bypass human authority, commit purchases or waive release gates. Uncertain changes remain pending until verified by an authorized source.

## Related documents
- [Production gate](PRODUCTION_GATE.md)
- [Pilot plan](PILOT_PLAN.md)
- [Adult handoff](ADULT_HANDOFF.md)
- [Portal demo](PORTAL_DEMO.md)
- [Threat model](THREAT_MODEL.md)
- [Hosting plan](HOSTING_PLAN.md)
