"""Independent, read-only reconciliation of a V3 export.

Compares exported records against the preserved baseline plus *approved* changes
in the audit DB. Does not trust the engine's export success status.
"""
import argparse,csv,hashlib,json,sqlite3,sys
from pathlib import Path

FIELDS=("sku","title","price","stock")

def verify(db,job,output):
    import audit_integrity
    audit_result=audit_integrity.verify_job(db,job)
    if not audit_result["passed"]:
        raise ValueError("independent audit reconciliation failed")
    path=Path(output)
    if not path.is_file():raise ValueError("export file not found")
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        record=conn.execute("SELECT holds,status FROM jobs WHERE id=?",(job,)).fetchone()
        if not record:raise ValueError("unknown job")
        if json.loads(record["holds"]):raise ValueError("job has unresolved holds")
        # After release, the independently recorded export digest must still
        # match the bytes being downloaded, not merely mutable row state.
        release_events=[r["details"] for r in conn.execute(
            "SELECT details FROM events WHERE job=? AND kind='export'",(job,))]

        changes=[dict(r) for r in conn.execute(
            "SELECT sku,field,old,new,status FROM changes WHERE job=?",(job,))]
        if any(r["status"]=="pending" for r in changes):
            raise ValueError("job has pending decisions")
        expected={r["sku"]:dict(r) for r in conn.execute(
            "SELECT sku,title,price,stock FROM base WHERE job=?",(job,))}
    for change in changes:
        if change["sku"] not in expected or change["field"] not in FIELDS:
            raise ValueError("change references invalid SKU or field")
        # Reject corrupted audit information rather than silently trusting it.
        if change["status"] not in ("approved","rejected"):
            raise ValueError("invalid audit status")
        if change["status"]=="approved":
            expected[change["sku"]][change["field"]]=change["new"]
    mismatches=[]
    seen=set()
    with path.open(encoding="utf-8-sig",newline="") as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=list(FIELDS):raise ValueError("unexpected export columns")
        for line,row in enumerate(reader,2):
            if None in row or any(x is None for x in row.values()):
                raise ValueError("malformed export row")
            sku=row["sku"]
            if sku in seen:
                mismatches.append({"sku":sku,"reason":"duplicate export SKU"});continue
            seen.add(sku)
            if sku not in expected:
                mismatches.append({"sku":sku,"reason":"unexpected export SKU"});continue
            differences=[field for field in FIELDS if row[field]!=expected[sku][field]]
            if differences:
                mismatches.append({"sku":sku,"reason":"value mismatch","fields":differences})
    for missing in sorted(set(expected)-seen):
        mismatches.append({"sku":missing,"reason":"missing export SKU"})
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    if record["status"]=="exported":
        if len(release_events)!=1:
            raise ValueError("missing or duplicate export release record")
        try:released=json.loads(release_events[0])
        except (ValueError,TypeError):raise ValueError("invalid export release record")
        if (not isinstance(released,dict) or
                released.get("independent_qa")!="passed" or
                released.get("sha256")!=sha):
            raise ValueError("released export hash does not match current file")
    elif release_events:
        raise ValueError("export release exists for non-exported job")

    return {"passed":not mismatches,"job_id":job,"expected_rows":len(expected),
            "actual_rows":len(seen),"sha256":sha,"mismatches":mismatches[:100],
            "truncated":len(mismatches)>100,
            "audit_reconciled":True}

def main():
    p=argparse.ArgumentParser(description="Independent audit of approved V3 CSV output")
    p.add_argument("--db",default="v3.sqlite3")
    p.add_argument("job");p.add_argument("csv")
    args=p.parse_args()
    try:
        result=verify(args.db,args.job,args.csv)
        print(json.dumps(result,indent=2))
        if not result["passed"]:sys.exit(2)
    except (ValueError,OSError,sqlite3.Error) as ex:
        print(json.dumps({"error":str(ex)}),file=sys.stderr);sys.exit(1)
if __name__=="__main__":main()
