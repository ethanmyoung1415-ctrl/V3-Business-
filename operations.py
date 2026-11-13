"""Offline V3 work queue: automated analysis, never automatic approval or export.
Not suitable for customer data or production deployment.
"""
import argparse
import hashlib
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import engine
import intake

MAX_ATTEMPTS = 3
LEASE_SECONDS = 120

def now():
    return datetime.now(timezone.utc)

def setup(db):
    engine.setup(db)
    with sqlite3.connect(db) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS work_queue(
            id TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL UNIQUE,
            baseline_path TEXT NOT NULL,
            update_path TEXT NOT NULL,
            baseline_sha256 TEXT NOT NULL,
            update_sha256 TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('queued','processing','review','failed')),
            attempts INTEGER NOT NULL DEFAULT 0,
            lease_until TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            engine_job_id TEXT,
            last_error TEXT);
        CREATE INDEX IF NOT EXISTS idx_work_queue_status ON work_queue(status,created_at);
        CREATE TABLE IF NOT EXISTS queue_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            kind TEXT NOT NULL,
            details TEXT NOT NULL);
        """)

def record(conn, work_id, kind, details):
    conn.execute("INSERT INTO queue_events(work_id,occurred_at,kind,details) VALUES(?,?,?,?)",
                 (work_id,now().isoformat(),kind,json.dumps(details,sort_keys=True)))

def enqueue(db, baseline, update):
    """Copy source CSVs into local staging before queuing; never trust mutable originals."""
    setup(db)
    staged=intake.stage_pair(baseline,update,db)
    (b,bh),(u,uh)=staged
    fingerprint=hashlib.sha256((bh+":"+uh).encode()).hexdigest()
    work_id=str(uuid.uuid4())
    ts=now().isoformat()
    try:
        with sqlite3.connect(db) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing=conn.execute(
                "SELECT id FROM work_queue WHERE fingerprint=?",(fingerprint,)).fetchone()
            if existing:
                work_id=existing[0]
                reused=True
            else:
                conn.execute("""INSERT INTO work_queue
                    (id,fingerprint,baseline_path,update_path,baseline_sha256,update_sha256,status,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,'queued',?,?)""",
                    (work_id,fingerprint,str(b),str(u),bh,uh,ts,ts))
                record(conn,work_id,"enqueued",{"fingerprint":fingerprint})
                reused=False
        if reused:
            intake.cleanup_staged([b,u])
        return {"work_id":work_id,"already_exists":reused}
    except BaseException:
        intake.cleanup_staged([b,u])
        raise

def claim(db):
    setup(db)
    ts=now()
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        item=conn.execute("""SELECT * FROM work_queue
            WHERE status='queued' AND attempts<? ORDER BY created_at,id LIMIT 1""",
            (MAX_ATTEMPTS,)).fetchone()
        if not item:return None
        attempts=item["attempts"]+1
        conn.execute("""UPDATE work_queue
            SET status='processing',attempts=?,lease_until=?,updated_at=? WHERE id=?""",
            (attempts,(ts+timedelta(seconds=LEASE_SECONDS)).isoformat(),ts.isoformat(),item["id"]))
        record(conn,item["id"],"claimed",{"attempt":attempts})
        return dict(item)|{"attempts":attempts}

def finish(db,work_id,job_id=None,error=None,terminal=False):
    ts=now().isoformat()
    with sqlite3.connect(db) as conn:
        conn.execute("BEGIN IMMEDIATE")
        found=conn.execute("SELECT status,attempts FROM work_queue WHERE id=?",(work_id,)).fetchone()
        if not found or found[0]!="processing":
            raise ValueError("work item not processing")
        if error is not None:
            status="failed" if terminal or found[1]>=MAX_ATTEMPTS else "queued"
            conn.execute("""UPDATE work_queue SET status=?,lease_until=NULL,updated_at=?,last_error=?
                WHERE id=?""",(status,ts,error[:300],work_id))
            record(conn,work_id,"processing_error",{"status":status,"error":error[:300]})
        else:
            if not job_id:raise ValueError("job id required")
            conn.execute("""UPDATE work_queue SET status='review',engine_job_id=?,
                lease_until=NULL,updated_at=?,last_error=NULL WHERE id=?""",
                (job_id,ts,work_id))
            record(conn,work_id,"ready_for_review",{"engine_job_id":job_id})

def mark_stale(db):
    """Expired processing leases fail closed; do not risk duplicate processing."""
    setup(db)
    ts=now().isoformat()
    with sqlite3.connect(db) as conn:
        conn.execute("BEGIN IMMEDIATE")
        expired=[x[0] for x in conn.execute(
            "SELECT id FROM work_queue WHERE status='processing' AND lease_until < ?",(ts,))]
        for work_id in expired:
            conn.execute("""UPDATE work_queue SET status='failed',lease_until=NULL,
                updated_at=?,last_error='stale worker; manual investigation required' WHERE id=?""",
                (ts,work_id))
            record(conn,work_id,"stale_worker",{"action":"manual investigation"})
    return expired

def work_once(db):
    mark_stale(db)
    item=claim(db)
    if item is None:return {"status":"idle"}
    try:
        b,u=Path(item["baseline_path"]),Path(item["update_path"])
        if engine.digest(b)!=item["baseline_sha256"] or engine.digest(u)!=item["update_sha256"]:
            raise ValueError("source file changed after enqueue; submit a new job")
        result=engine.ingest(db,b,u)
        finish(db,item["id"],job_id=result["job_id"])
        return {"status":"review","work_id":item["id"],**result}
    except (ValueError,OSError,sqlite3.Error) as ex:
        finish(db,item["id"],error=str(ex),terminal=isinstance(ex,(ValueError,FileNotFoundError)))
        return {"status":"retry_or_failed","work_id":item["id"],"error":str(ex)}

def dashboard(db):
    mark_stale(db)
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        counts={r["status"]:r["total"] for r in conn.execute(
            "SELECT status,COUNT(*) total FROM work_queue GROUP BY status")}
        jobs=[]
        for item in conn.execute("SELECT * FROM work_queue ORDER BY created_at DESC LIMIT 100"):
            info=dict(item)
            info.pop("baseline_path");info.pop("update_path")
            if info["engine_job_id"]:
                review=engine.review(db,info["engine_job_id"])
                info["holds"]=len(review["holds"])
                info["pending_decisions"]=sum(x["status"]=="pending" for x in review["changes"])
            jobs.append(info)
    return {"counts":counts,"jobs":jobs,"generated_at":now().isoformat()}

def main():
    p=argparse.ArgumentParser(description="V3 local queue (no live actions)")
    p.add_argument("--db",default="v3.sqlite3")
    sub=p.add_subparsers(dest="command",required=True)
    e=sub.add_parser("enqueue");e.add_argument("baseline");e.add_argument("update")
    sub.add_parser("work-once");sub.add_parser("dashboard")
    a=p.parse_args()
    try:
        if a.command=="enqueue":out=enqueue(a.db,a.baseline,a.update)
        elif a.command=="work-once":out=work_once(a.db)
        else:out=dashboard(a.db)
        print(json.dumps(out,indent=2))
    except (ValueError,OSError,sqlite3.Error) as ex:
        print(json.dumps({"error":str(ex)}),file=sys.stderr);sys.exit(1)
if __name__=="__main__":main()
