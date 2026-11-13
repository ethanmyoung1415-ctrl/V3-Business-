"""Deterministic, evidence-based catalog change report for a reviewed V3 job.

No model-generated claims, savings estimates, or untrusted content execution.
A released report must include a successfully reconciled final export.
"""
from collections import Counter
from datetime import datetime,timezone
import json
import sqlite3
from pathlib import Path
import engine
import qa
import triage

def generate(db,job_id,output=None):
    details=engine.review(db,job_id)
    job=details["job"]
    rows=details["changes"]
    holds=details["holds"]
    counts=Counter(change["status"] for change in rows)
    report={
        "schema_version":"1.0",
        "job_id":job_id,
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "created_at":job["created"],
        "source_sha256":{
            "baseline":job["baseline_hash"],
            "supplier_update":job["update_hash"],
        },
        "job_status":job["status"],
        "summary":{
            "total_proposed_changes":len(rows),
            "approved_changes":counts.get("approved",0),
            "rejected_changes":counts.get("rejected",0),
            "pending_changes":counts.get("pending",0),
            "unresolved_holds":len(holds),
            "excluded_holds":0,
        },
        "changes":[
            {
                "sku":row["sku"],"field":row["field"],
                "previous_value":row["old"],"proposed_value":row["new"],
                "decision":row["status"],
                "risk":triage.assess_change(row)["risk"],
            } for row in rows
        ],
        "remaining_holds":holds,
        "excluded_holds":[],
        "verification":{"passed":False,"sha256":None},
        "notes":[
            "Original invalid supplier values are not applied when held rows are excluded.",
            "This report does not certify a live-store import or monetary savings.",
        ],
    }
    with sqlite3.connect(db) as conn:
        for (details_json,) in conn.execute(
            "SELECT details FROM events WHERE job=? AND kind='hold_excluded' ORDER BY id",
            (job_id,)):
            action=json.loads(details_json)
            report["excluded_holds"].append({
                "record":action.get("original_hold",{}),
                "reason":action.get("reason",""),
                "actor":action.get("actor",""),
                "policy":action.get("policy",""),
            })
    report["summary"]["excluded_holds"]=len(report["excluded_holds"])
    if output is not None:
        if job["status"]!="exported":
            raise ValueError("only committed exports may have verified reports")
        verification=qa.verify(db,job_id,output)
        if not verification["passed"]:
            raise ValueError("output does not pass independent QA")
        report["verification"]={
            "passed":True,"sha256":verification["sha256"],
            "row_count":verification["actual_rows"],
        }
    return report

def serialize(report):
    return json.dumps(report,indent=2,sort_keys=True,ensure_ascii=True)+"\n"
