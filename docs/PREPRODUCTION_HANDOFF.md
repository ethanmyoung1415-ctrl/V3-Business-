# V3 engineering handoff — preproduction

**Release state: LOCAL SYNTHETIC DEMONSTRATION ONLY.** The software now includes substantially more than the original CSV checker, but is not a publicly hosted, externally connected, or income-generating service.

## Implemented workflows

**Merchant intake:** A synthetic store customer signs into a local Django account and submits a baseline plus supplier CSV or strictly supported single-sheet XLSX. The system validates schema/limits, hashes original uploads and stages immutable local copies. Alternatively, a merchant may select an exact store-scoped supplier header profile. That mapping is frozen on the job.

**Managed analysis:** A local worker uses a stable job ID, compares catalogs, holds ambiguous or unsafe data and stores deterministic evidence/risk advice. An optional model adapter is coded but disabled without explicit local-only flags, provider credentials and permitted synthetic scope.

**Operator decisions:** Role-limited operators see pending jobs, risk and recommendations. They explicitly approve/reject changes with reasons, optionally batch-approve only small nonzero inventory adjustments, and may explicitly exclude malformed source records **without applying those values**. Audit events record actions.

**Customer delivery:** Only after all holds and decisions are resolved does an independent verifier release a CSV. An accompanying JSON report shows change decisions, excluded rows, source SHA hashes and verification status. Tenant members may download only their own verified files.

**Recurring service:** A store customer may assert they imported that verified result externally. This requires their explicit confirmation; V3 cannot see a real storefront. The *latest confirmed* version may be reused as the next baseline; unconfirmed or tampered versions are blocked.

**Reliability:** Stable job IDs prevent duplicate processing after an interrupted portal update; reasoned retries only for recoverable failures. In-app notices, stale-job review, local emergency stop, synthetic archive/restore and minimal retention controls are present.

**Additional safety and operator-workflow components:** Independent decision/hold audit reconciliation blocks forged approvals or inconsistent exclusions. Released-file hashes are checked at download; an optional separately keyed HMAC receipt can verify matching release CSV/report bytes. A manual recovery tool prepares a prior catalog snapshot without touching a live store. A read-only, disabled-by-default autonomy simulator shows which narrowly bounded stock updates might be eligible under a *future* authorized policy; it never approves anything. A synthetic-only single-use invitation flow allows scoped mock customer enrollment without open public registration.

**Excel restrictions:** XLSX intake is strictly limited to canonical, simple sheets. Workbooks with formulas, macros, linked data, hidden or merged rows, styled numeric/date cells, ambiguous multiple sheets or numeric SKU identifiers are rejected. Existing supplier header profiles still require CSV. See [XLSX Intake](XLSX_INTAKE.md).

**Confidence:** GitHub Actions runs standard-library engine tests, Django portal tests and a repository guard. It also runs the synthetic preflight, which deliberately reports commercial NO-GO. A green run confirms only tested scenarios; the latest run is at [GitHub Actions](https://github.com/ethanmyoung1415-ctrl/V3-Business-/actions).

## Demo and review resources
- [Portal walkthrough](PORTAL_DEMO.md)
- [Threat model](THREAT_MODEL.md)
- [Hosting design proposal](HOSTING_PLAN.md)
- [AI model evaluation plan](AI_EVALUATION_PLAN.md)
- [Operator playbook](OPERATOR_PLAYBOOK.md)
- [Proposed controlled pilot](PILOT_PLAN.md)
- [Adult/business account briefing](ADULT_HANDOFF.md)
- [Commercial release checklist](PRODUCTION_GATE.md)
- [XLSX support and unsupported workbook features](XLSX_INTAKE.md)
- [Local synthetic invitations](LOCAL_INVITATIONS.md)
- [Future automation simulation](AUTOMATION_SIMULATION.md)
- [Manual recovery procedure](MANUAL_RECOVERY.md)
- [Optional release receipts](RELEASE_RECEIPTS.md)

## Not yet operational
- Public web hosting, domain, TLS ingress, production object storage/PostgreSQL and queue
- Commercial account provisioning, independent professional security audit and incident/backup operations
- Real external AI model invocations, approved data-transfer terms or provider usage budget
- Shopify/other store connectors, actual store data reads/writes or automatic remote import confirmation
- **Production** customer onboarding, verified email/identity, service agreements, billing, payments, taxes or bookkeeping (local mock invitations exist only for testing)
- Real customer interviews, paid pilots, contractual renewals, measured margins and validated pricing

## Dependencies that genuinely require help
1. **User/parent or legally appropriate signatory:** authorizing provider, hosting, financial and customer-contract accounts and budget; professional legal/tax arrangements.
2. **Technical reviewer:** independent security and deployment architecture signoff before any real customer data.
3. **Prospective customers:** permissioned examples, real-world workflow confirmation, pilot acceptance and contract approval.

Further offline coding and documentation are possible; this document does not claim that every conceivable feature is implemented. But commercial progress is no longer just a matter of writing more code; the outstanding release gates require external parties and authorization.

**Safety rule:** Do not bypass tests, expose localhost to the public internet, add provider keys to GitHub, process private customer files, or accept money before approval.
