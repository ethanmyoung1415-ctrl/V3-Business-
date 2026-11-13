"""Single-command V3 preproduction smoke preflight.

A green outcome means specific fictional-data checks passed. It NEVER
authorizes a public launch, account creation, payments, real files, or
customer-store actions.
"""
import argparse
import json
import tempfile
from pathlib import Path

import benchmark
import demo
import synthetic_evaluation

REQUIRED_DOCUMENTS=(
    "docs/PRODUCTION_GATE.md",
    "docs/THREAT_MODEL.md",
    "docs/HOSTING_PLAN.md",
    "docs/PILOT_PLAN.md",
    "docs/ADULT_HANDOFF.md",
)
BLOCKERS=(
    "authorized adult/business signatory and approved accounts",
    "production MFA, secrets, encryption and tenant isolation",
    "durable hosted queue, monitoring, full backups and recovery",
    "independent security review and documented release acceptance",
    "customer permission, legal terms, payment setup and validated pilot",
)

def run(root=None):
    folder=Path(root) if root is not None else Path(__file__).resolve().parent
    documents={name:(folder/name).is_file() for name in REQUIRED_DOCUMENTS}
    evaluation=synthetic_evaluation.evaluate(300)
    with tempfile.TemporaryDirectory(prefix="v3-preflight-") as path:
        path=Path(path)
        bench=benchmark.run(path/"benchmark",1000)
        outcome=demo.simulate(path/"demo")
    checks={
        "required_release_docs_present":all(documents.values()),
        "known_synthetic_anomalies_detected":evaluation["passed"],
        "synthetic_1000_row_benchmark_passed":bench["passed"],
        "separate_mock_customers_and_verification":outcome["passed"],
        "cross_customer_read_blocked":outcome["cross_customer_read_blocked"],
        "synthetic_only":not outcome["real_customer_data_used"],
    }
    return {
        "schema_version":1,
        "development_checks_passed":all(checks.values()),
        "checks":checks,
        "production_decision":"NO_GO",
        "public_deployment_allowed":False,
        "real_customer_data_allowed":False,
        "billing_allowed":False,
        "live_store_writes_allowed":False,
        "approval_blockers":list(BLOCKERS),
        "note":"Smoke tests are useful but cannot substitute for a security review or real pilot.",
    }

def main():
    parser=argparse.ArgumentParser(description="V3 synthetic development preflight")
    parser.add_argument("--strict",action="store_true",
        help="Exit nonzero if development smoke checks fail; NO_GO remains normal.")
    args=parser.parse_args()
    result=run()
    print(json.dumps(result,indent=2,sort_keys=True))
    if args.strict and not result["development_checks_passed"]:
        raise SystemExit(1)

if __name__=="__main__":main()
