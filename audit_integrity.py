"""Independent, read-only audit reconciliation for synthetic catalog jobs.

Verifies each decided change has a matching human-decision event, hold state
is derived from the original intake plus explicit exclusions, and baseline
values still match the original comparison. Does NOT prove external tamper
resistance: a privileged DB editor could rewrite both data and audit events.
"""
import argparse
from collections import Counter
import hashlib
import json
import sqlite3
import sys
import engine

FIELDS={"title","price","stock"}

def _json(data):
    try:
        value=json.loads(data)
    except (TypeError,ValueError):
        return None
    return value if isinstance(value,dict) else None

def verify_job(db,job):
    failures=[]
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        record=conn.execute("SELECT * FROM jobs WHERE id=?",(job,)).fetchone()
        if record is None:raise ValueError("unknown job")
        baseline={r["sku"]:dict(r) for r in conn.execute(
            "SELECT sku,title,price,stock FROM base WHERE job=?",(job,))}
        changes=[dict(x) for x in conn.execute(
            "SELECT * FROM changes WHERE job=?",(job,))]
        events=[dict(x) for x in conn.execute(
            "SELECT id,kind,details FROM events WHERE job=? ORDER BY id",(job,))]
    ingests=[_json(x["details"]) for x in events if x["kind"]=="ingest"]
    if len(ingests)!=1 or ingests[0] is None or not isinstance(ingests[0].get("holds"),list):
        failures.append("missing_or_invalid_ingest_event")
        original_holds=[]
    else:
        original_holds=ingests[0]["holds"]
        if ingests[0].get("changes")!=len(changes):
            failures.append("ingest_change_count_mismatch")
    try:
        current_holds=json.loads(record["holds"])
        if not isinstance(current_holds,list):
            raise ValueError()
    except (TypeError,ValueError):
        current_holds=[]
        failures.append("invalid_held_record_state")
    expected=Counter(engine.hold_token(x) for x in original_holds if isinstance(x,dict))
    exclusions=0
    for event in events:
        if event["kind"]!="hold_excluded":continue
        data=_json(event["details"])
        exclusions+=1
        if (not data or not isinstance(data.get("original_hold"),dict)
                or not isinstance(data.get("reason"),str)
                or len(data["reason"].strip())<12
                or not isinstance(data.get("actor"),str)
                or not data["actor"].strip()
                or data.get("policy")!="held_source_data_never_applied"):
            failures.append("invalid_hold_exclusion_event")
            continue
        token=engine.hold_token(data["original_hold"])
        if token!=data.get("token") or expected[token]<1:
            failures.append("unmatched_hold_exclusion")
        else:
            expected[token]-=1
    if any(not isinstance(x,dict) for x in current_holds):
        failures.append("invalid_current_hold")
    elif +(Counter(engine.hold_token(x) for x in current_holds)) != +expected:
        failures.append("hold_state_does_not_match_exclusions")

    decisions={}
    for event in events:
        if event["kind"]!="decision":continue
        data=_json(event["details"])
        if (not data or data.get("decision") not in ("approved","rejected")
                or not isinstance(data.get("actor"),str) or not data["actor"].strip()
                or not isinstance(data.get("reason"),str) or not data["reason"].strip()
                or not isinstance(data.get("change"),str)):
            failures.append("invalid_decision_event")
            continue
        decisions.setdefault(data["change"],[]).append(data["decision"])
    observed=set()
    for change in changes:
        key=(change["sku"],change["field"])
        if key in observed:
            failures.append("duplicate_change_target")
        observed.add(key)
        sku=change["sku"]
        field=change["field"]
        if sku not in baseline or field not in FIELDS:
            failures.append("change_target_not_in_baseline")
            continue
        if change["old"]!=baseline[sku][field]:
            failures.append("change_old_value_differs_from_baseline")
        if field=="price":
            try:engine.price(change["new"])
            except ValueError:failures.append("invalid_change_price")
        elif field=="stock":
            try:engine.stock(change["new"])
            except ValueError:failures.append("invalid_change_stock")
        status=change["status"]
        recorded=decisions.pop(change["id"],[])
        if status=="pending":
            if recorded:failures.append("pending_change_with_decision_event")
        elif status in ("approved","rejected"):
            if len(recorded)!=1 or recorded[0]!=status:
                failures.append("decision_event_missing_or_mismatched")
        else:
            failures.append("invalid_change_status")
    if decisions:
        failures.append("orphan_decision_event")
    for sku,row in baseline.items():
        try:
            if not sku or row["sku"]!=sku:raise ValueError()
            engine.price(row["price"])
            engine.stock(row["stock"])
        except ValueError:
            failures.append("invalid_baseline_row")
    exports=[_json(x["details"]) for x in events if x["kind"]=="export"]
    if record["status"]=="exported":
        if len(exports)!=1 or not exports[0] or exports[0].get("independent_qa")!="passed":
            failures.append("missing_or_invalid_export_event")
        if current_holds or any(x["status"]=="pending" for x in changes):
            failures.append("exported_job_with_unresolved_decisions")
    elif exports:
        failures.append("export_event_for_unexported_job")
    return {
        "job_id":job,"passed":not failures,
        "failures":sorted(set(failures)),
        "verified_decisions":sum(x["status"] in ("approved","rejected") for x in changes),
        "excluded_holds":exclusions,
        "limitation":"DB-internal audit consistency only; not externally anchored tamper evidence.",
    }

def main():
    parser=argparse.ArgumentParser(description="Read-only V3 audit consistency inspection")
    parser.add_argument("--db",default="v3.sqlite3")
    parser.add_argument("job")
    args=parser.parse_args()
    result=verify_job(args.db,args.job)
    print(json.dumps(result,indent=2))
    if not result["passed"]:sys.exit(2)

if __name__=="__main__":main()
