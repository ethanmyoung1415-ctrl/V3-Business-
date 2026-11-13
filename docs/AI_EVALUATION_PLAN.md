# AI Advisory Evaluation Plan

**Current state:** deterministic suggestions run locally. An optional model adapter has no credentials, is disabled by default, and is not exercised against real customer data.

## Authority boundary
- Deterministic validation and explicit human/customer policies determine eligibility and what is held.
- AI may only provide short explanations and verification suggestions.
- AI cannot change stock, prices, approvals, emails, files, credentials, billing, or customer communications.
- Invalid, incomplete or failed outputs revert to deterministic advice.
- Any future model call requires approved provider credentials, a permitted data-handling scope and a capped budget.

## Synthetic evaluation dataset
Create at least 200 cases across:
- Correct zero-stock updates; duplicate SKUs; unknown SKUs; blank values
- Price spikes, drops, currencies and decimal representation differences
- Header mapping changes and inconsistent supplier files
- Malicious product titles instructing the model to ignore rules, reveal secrets or perform external actions
- Models hallucinating approvals, unsupported fields or invalid JSON
- Provider timeouts, refusals, length overruns and quota exhaustion

## Compare to a deterministic baseline
For every case, record source evidence, rule-based risk, suggested verification step, reviewer rating, failure category and any cost/latency. No model suggestion may reduce deterministic severity or bypass approval requirements.

## Success criteria before enabling any real-provider workflow
- Zero unauthorized state changes across all adversarial tests
- Provider-off and provider-failed flows still process safely
- Evidence-backed explanations rated useful by independent reviewers
- Measured per-case latency, max token/cost budget and fallback rate
- Written data-processing consent/authorization and security signoff

## Acceptance
Only the owner and an authorized technical/security reviewer may permit future provider activation. The current synthetic demo remains offline by default. Do not claim the model is serving clients or that it reduces labor until measured in pilots.
