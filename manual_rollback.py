"""Prepare a *manual-use* prior catalog snapshot for a reviewed synthetic job.

This does not modify or connect to a customer's live store. The output is the
job's stored baseline, NOT proof of the current external store state. Never
automatically import it: intervening changes could make rollback unsafe.
"""
import argparse
import csv
import json
import sqlite3
from pathlib import Path
import audit_integrity
import engine
import qa

def verify_baseline(db,job,path):
    """Independent strict row/column comparison against stored baseline."""
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        baseline={r["sku"]:dict(r) for r in conn.execute(
            "SELECT sku,title,price,stock FROM base WHERE job=?",(job,))}
    if not baseline:raise ValueError("baseline unavailable")
    actual={}
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f,strict=True)
        if reader.fieldnames!=list(engine.FIELDS):
            raise ValueError("unexpected rollback columns")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("malformed rollback row")
            sku=row["sku"]
            if not sku or sku in actual:raise ValueError("duplicate or blank rollback SKU")
            actual[sku]=row
    if actual!=baseline:
        raise ValueError("manual rollback snapshot differs from preserved baseline")
    return {"passed":True,"rows":len(actual),"sha256":engine.digest(path)}

def prepare(db,job,released_file,output,actor,reason):
    if (not isinstance(actor,str) or not actor.strip()
            or not isinstance(reason,str) or len(reason.strip())<12):
        raise ValueError("operator and detailed reason required")
    output=Path(output)
    if output.exists():raise ValueError("rollback file already exists")
    # Re-evaluate both independent quality and audit evidence first.
    audit=audit_integrity.verify_job(db,job)
    if not audit["passed"]:raise ValueError("job audit does not reconcile")
    state=engine.review(db,job)["job"]["status"]
    if state!="exported":raise ValueError("only released jobs can prepare rollback")
    evidence=qa.verify(db,job,released_file)
    if not evidence["passed"]:raise ValueError("released file failed independent QA")
    wrote=False
    with sqlite3.connect(db,timeout=30) as conn:
        conn.row_factory=sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        # Another operator cannot modify a completed job normally; nevertheless
        # capture a consistent copy while writing and recording the artifact.
        rows=[dict(r) for r in conn.execute(
            "SELECT sku,title,price,stock FROM base WHERE job=? ORDER BY sku",(job,))]
        if not rows:raise ValueError("baseline unavailable")
        try:
            output.parent.mkdir(parents=True,exist_ok=True)
            with output.open("x",encoding="utf-8",newline="") as out:
                wrote=True
                writer=csv.DictWriter(out,fieldnames=engine.FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            verified=verify_baseline(db,job,output)
            engine.log(conn,job,"manual_rollback_prepared",{
                "actor":actor.strip(),"reason":reason.strip(),
                "sha256":verified["sha256"],"rows":verified["rows"],
                "external_store_modified":False,
            })
        except BaseException:
            if wrote:output.unlink(missing_ok=True)
            raise
    return {
        "path":str(output),"sha256":verified["sha256"],
        "rows":verified["rows"],
        "external_store_modified":False,
        "warning":"Manual previous snapshot only; verify current store state before importing.",
    }

def main():
    p=argparse.ArgumentParser(description="Synthetic manual rollback CSV generator")
    p.add_argument("--db",default="v3.sqlite3")
    p.add_argument("--actor",required=True)
    p.add_argument("--reason",required=True)
    p.add_argument("job")
    p.add_argument("released_file")
    p.add_argument("rollback_output")
    args=p.parse_args()
    print(json.dumps(prepare(args.db,args.job,args.released_file,args.rollback_output,
                             args.actor,args.reason),indent=2))

if __name__=="__main__":main()
