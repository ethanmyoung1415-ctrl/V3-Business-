"""Persistent read-only exception advice for V3 synthetic catalog jobs.

Provider functions are injected by a caller, never discovered automatically.
No network, credentials, customer communication or catalog modification exists
in this module. A provider failure always falls back to deterministic advice.
"""
import argparse
import hashlib
import json
import sqlite3
from datetime import datetime,timezone
import advisor
import engine

def setup(db):
    engine.setup(db)
    with sqlite3.connect(db) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS exception_advice(
            change_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            evidence_hash TEXT NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('deterministic','provider','fallback')),
            risk TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            explanation TEXT NOT NULL,
            verification_step TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(change_id) REFERENCES changes(id))""")
        conn.execute("CREATE INDEX IF NOT EXISTS advice_by_job ON exception_advice(job_id)")

def fingerprint(change):
    fields={key:change[key] for key in ("id","sku","field","old","new")}
    payload=json.dumps(fields,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()

def prepare(db,job,provider=None,max_items=100):
    if not isinstance(max_items,int) or not 1<=max_items<=500:
        raise ValueError("max_items must be between 1 and 500")
    setup(db)
    details=engine.review(db,job)
    selected=[x for x in details["changes"] if x["status"]=="pending"][:max_items]
    created=0
    reused=0
    provider_failures=0
    for change in selected:
        evidence_hash=fingerprint(change)
        with sqlite3.connect(db) as conn:
            present=conn.execute("SELECT evidence_hash FROM exception_advice WHERE change_id=?",
                                 (change["id"],)).fetchone()
        if present and present[0]==evidence_hash:
            reused+=1
            continue
        source="deterministic"
        if provider is None:
            result=advisor.deterministic_advice(change)
        else:
            try:
                raw=provider(advisor.request_payload(change))
                result=advisor.validate_response(change,raw)
                source="provider"
            except (ValueError,TypeError,KeyError,UnicodeError,json.JSONDecodeError,RuntimeError):
                result=advisor.deterministic_advice(change)
                source="fallback"
                provider_failures+=1
        if result["approved"] or result["customer_action_executed"]:
            raise ValueError("advisory attempted a forbidden action")
        advisory=result["advice"]
        with sqlite3.connect(db,timeout=30) as conn:
            conn.execute("BEGIN IMMEDIATE")
            # Never store notes for a change that has since been decided.
            current=conn.execute(
                "SELECT status FROM changes WHERE id=? AND job=?",
                (change["id"],job)).fetchone()
            if not current or current[0]!="pending":
                continue
            conn.execute("""INSERT INTO exception_advice
                (change_id,job_id,evidence_hash,source,risk,recommendation,
                 explanation,verification_step,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(change_id) DO UPDATE SET
                    evidence_hash=excluded.evidence_hash,
                    source=excluded.source,risk=excluded.risk,
                    recommendation=excluded.recommendation,
                    explanation=excluded.explanation,
                    verification_step=excluded.verification_step,
                    created_at=excluded.created_at""",
                (change["id"],job,evidence_hash,source,result["risk"],
                 result["recommendation"],advisory["explanation"],
                 advisory["verification_step"],
                 datetime.now(timezone.utc).isoformat()))
            engine.log(conn,job,"advisory_prepared",
                       {"change":change["id"],"source":source,"approved":False})
            created+=1
    return {"job_id":job,"prepared":created,"reused":reused,
            "provider_failures":provider_failures,"customer_actions":0}

def read(db,job):
    setup(db)
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        return [dict(row) for row in conn.execute(
            "SELECT * FROM exception_advice WHERE job_id=? ORDER BY created_at,change_id",
            (job,))]

def main():
    p=argparse.ArgumentParser(description="Prepare synthetic read-only operator advisories")
    p.add_argument("--db",default="v3.sqlite3")
    p.add_argument("job")
    a=p.parse_args()
    print(json.dumps(prepare(a.db,a.job),indent=2))
if __name__=="__main__":main()
