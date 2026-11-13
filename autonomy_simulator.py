"""Simulation-only bounded automation policy for synthetic V3 catalog changes.

No API, user credentials, data writes, approval calls or customer-facing effects.
An approved policy would require separate commercial/legal/customer authorization,
independent production checks and a *different* execution service.
"""
import argparse
import json
import engine

POLICY_KEYS={
    "version","authorized_simulation","allowed_fields",
    "max_units","max_percent","min_previous_stock",
    "max_candidates_per_job","excluded_skus",
}
DEFAULT={
    "version":1,
    "authorized_simulation":False,
    "allowed_fields":["stock"],
    "max_units":2,
    "max_percent":5,
    "min_previous_stock":20,
    "max_candidates_per_job":100,
    "excluded_skus":[],
}

def validate_policy(value):
    if not isinstance(value,dict) or set(value)!=POLICY_KEYS:
        raise ValueError("policy has missing or unknown keys")
    if type(value["version"]) is not int or value["version"]!=1:
        raise ValueError("unsupported policy version")
    if type(value["authorized_simulation"]) is not bool:
        raise ValueError("authorized_simulation must be boolean")
    if value["allowed_fields"]!=["stock"]:
        raise ValueError("only stock-only simulation is supported")
    for name,low,high in (
        ("max_units",1,5),("max_percent",1,10),
        ("min_previous_stock",10,1000000),
        ("max_candidates_per_job",1,500),
    ):
        if type(value[name]) is not int or not low<=value[name]<=high:
            raise ValueError(f"invalid policy {name}")
    excluded=value["excluded_skus"]
    if (not isinstance(excluded,list) or len(excluded)>1000 or
            any(not isinstance(x,str) or not x or len(x)>64 for x in excluded) or
            len(excluded)!=len(set(excluded))):
        raise ValueError("invalid excluded SKU set")
    return dict(value)

def inspect(db,job,policy):
    policy=validate_policy(policy)
    reviewed=engine.review(db,job)
    candidates=[]
    excluded=[]
    if not policy["authorized_simulation"]:
        return {"job_id":job,"status":"disabled","eligible":[],
                "ineligible":[{"reason":"simulation not explicitly enabled"}],
                "total_proposed":len(reviewed["changes"]),
                "approved":0,"actions_executed":0,
                "note":"Disabled simulation: no approval authority."}
    if reviewed["holds"]:
        return {"job_id":job,"status":"blocked_by_holds","eligible":[],
                "ineligible":[{"reason":"unresolved supplier holds prevent automation"}],
                "total_proposed":len(reviewed["changes"]),
                "approved":0,"actions_executed":0,
                "note":"Nothing is approved, even if rows appear low risk."}
    for change in reviewed["changes"]:
        if change["status"]!="pending":
            excluded.append({"id":change["id"],"reason":"already decided"})
            continue
        if change["field"]!="stock":
            excluded.append({"id":change["id"],"reason":"non-stock changes require a human"})
            continue
        if change["sku"] in policy["excluded_skus"]:
            excluded.append({"id":change["id"],"reason":"SKU excluded by policy"})
            continue
        try:
            previous=int(change["old"])
            proposed=int(change["new"])
        except (ValueError,TypeError):
            excluded.append({"id":change["id"],"reason":"invalid stock value"})
            continue
        if proposed<=0 or previous<policy["min_previous_stock"]:
            excluded.append({"id":change["id"],"reason":"zero/low stock requires human review"})
            continue
        delta=abs(proposed-previous)
        if (delta>policy["max_units"] or
                delta*100>policy["max_percent"]*previous):
            excluded.append({"id":change["id"],"reason":"change exceeds bounded threshold"})
            continue
        candidates.append({"id":change["id"],"sku":change["sku"],
                           "field":"stock","previous":previous,
                           "proposed":proposed,"absolute_change":delta})
    if len(candidates)>policy["max_candidates_per_job"]:
        excluded.extend({"id":x["id"],"reason":"per-job cap exceeded"}
                        for x in candidates)
        candidates=[]
    return {
        "job_id":job,"status":"simulation_only",
        "eligible":candidates,
        "ineligible":excluded,
        "total_proposed":len(reviewed["changes"]),
        "potentially_reduced_decisions":len(candidates),
        "approved":0,"actions_executed":0,
        "note":"Eligibility simulation only; all actual approvals remain with humans.",
    }

def main():
    parser=argparse.ArgumentParser(description="Read-only synthetic policy evaluation")
    parser.add_argument("--db",default="v3.sqlite3")
    parser.add_argument("--policy",help="JSON policy file; otherwise simulation disabled")
    parser.add_argument("job")
    args=parser.parse_args()
    policy=json.loads(open(args.policy,encoding="utf-8").read()) if args.policy else DEFAULT
    print(json.dumps(inspect(args.db,args.job,policy),indent=2))

if __name__=="__main__":main()
