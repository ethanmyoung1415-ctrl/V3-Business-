"""Read-only operational reporting for synthetic V3 development data."""
import json
import sqlite3
from datetime import datetime,timezone

def snapshot(db):
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        queue={r["status"]:r["total"] for r in conn.execute(
            "SELECT status,COUNT(*) total FROM work_queue GROUP BY status")}
        analysis=[]
        for item in conn.execute("""SELECT w.id,w.status,w.created_at,w.updated_at,
                w.attempts,w.engine_job_id,w.last_error,j.holds
                FROM work_queue w LEFT JOIN jobs j ON w.engine_job_id=j.id
                ORDER BY w.created_at,w.id"""):
            d=dict(item)
            d["hold_count"]=len(json.loads(d["holds"])) if d["holds"] else 0
            d.pop("holds")
            d["pending_decisions"]=0
            if d["engine_job_id"]:
                d["pending_decisions"]=conn.execute(
                    "SELECT COUNT(*) FROM changes WHERE job=? AND status='pending'",
                    (d["engine_job_id"],)).fetchone()[0]
            analysis.append(d)
        total_reviews=sum(x["pending_decisions"] for x in analysis)
        total_holds=sum(x["hold_count"] for x in analysis)
        failed=sum(x["status"]=="failed" for x in analysis)
        actionable=[x for x in analysis if x["pending_decisions"] or x["hold_count"] or x["status"]=="failed"]
        status=("attention_required" if failed or total_holds or total_reviews else
                "processing" if queue.get("queued",0) or queue.get("processing",0) else "idle")
        return {
            "generated_at":datetime.now(timezone.utc).isoformat(),
            "operational_status":status,
            "totals":{"jobs":len(analysis),"failed_jobs":failed,
                "pending_decisions":total_reviews,"unresolved_holds":total_holds,
                "requires_operator_attention":len(actionable)},
            "queue_counts":queue,
            "attention":[{"work_id":x["id"],"job_id":x["engine_job_id"],
                "status":x["status"],"pending_decisions":x["pending_decisions"],
                "unresolved_holds":x["hold_count"],"last_error":x["last_error"]}
                for x in actionable[:100]],
            "limits":{"attention_truncated":len(actionable)>100,
                "note":"Local prototype metrics, not uptime, revenue or customer SLA statistics."}
        }
