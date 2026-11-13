"""Read-only V3 operator briefing; local deterministic fallback to future AI manager."""
import operations
import triage

RANK={"critical":0,"high":1,"medium":2,"low":3}

def briefing(db,max_items=25):
    if max_items<1 or max_items>500:raise ValueError("invalid report limit")
    state=operations.dashboard(db)
    queue=[]
    total=0
    for item in state["jobs"]:
        if item["status"]=="failed":
            queue.append({"kind":"failed_job","severity":"critical",
                "work_id":item["id"],"job_id":item.get("engine_job_id"),
                "summary":"Processing failure needs diagnosis",
                "evidence":{"error":item.get("last_error") or "unknown error"},
                "recommended_next_step":"Inspect audit and worker logs; do not blindly reprocess."})
            total+=1
        if item.get("engine_job_id"):
            report=triage.report(db,item["engine_job_id"])
            for hold in report["holds"]:
                queue.append({"kind":"held_record","severity":hold["risk"],
                    "work_id":item["id"],"job_id":item["engine_job_id"],
                    "summary":"Supplier record held",
                    "evidence":hold,
                    "recommended_next_step":"Request corrected source record."})
                total+=1
            for change in report["changes"]:
                if change["status"]!="pending":continue
                queue.append({"kind":"pending_decision","severity":change["risk"],
                    "work_id":item["id"],"job_id":item["engine_job_id"],
                    "change_id":change["change_id"],
                    "summary":change["explanation"],
                    "evidence":change["evidence"],
                    "recommended_next_step":change["recommendation"]})
                total+=1
    queue.sort(key=lambda x:(RANK.get(x["severity"],99),x.get("job_id") or "",
                             x.get("change_id") or ""))
    return {"needs_attention":total,"returned":min(total,max_items),
            "truncated":total>max_items,"items":queue[:max_items],
            "scope":"local synthetic data","automated_approvals":0}
