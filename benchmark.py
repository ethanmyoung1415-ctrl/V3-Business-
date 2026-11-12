"""Synthetic V3 benchmark generator. Never uses or requests real store data."""
import argparse,csv,json,tempfile,time
from pathlib import Path
import engine,triage

def fixtures(directory,count):
    if count<5 or count>100000:raise ValueError("count must be between 5 and 100000")
    folder=Path(directory)
    folder.mkdir(parents=True,exist_ok=True)
    baseline=folder/"baseline.csv"
    update=folder/"supplier_update.csv"
    with baseline.open("w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f);writer.writerow(("sku","title","price","stock"))
        for i in range(count):writer.writerow((f"SKU-{i:06d}",f"Example product {i}","10.00","12"))
    # Known errors: 1 duplicate SKU, 1 unknown SKU, 1 blank value.
    # Known valid cases: 1 zero-stock update, 1 large price increase.
    with update.open("w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f);writer.writerow(("sku","price","stock"))
        writer.writerow(("SKU-000000","15.00","0"))
        writer.writerow(("SKU-000001","10.00",""))
        writer.writerow(("SKU-000002","10.00","4"))
        writer.writerow(("SKU-000002","10.00","6"))
        writer.writerow(("SKU-UNKNOWN","11.00","1"))
        for i in range(3,count):writer.writerow((f"SKU-{i:06d}","10.00","12"))
    return baseline,update

def run(directory,count):
    baseline,update=fixtures(directory,count)
    db=Path(directory)/"benchmark.sqlite3"
    if db.exists():raise ValueError("benchmark database already exists; use a fresh directory")
    start=time.perf_counter()
    result=engine.ingest(db,baseline,update)
    seconds=time.perf_counter()-start
    report=triage.report(db,result["job_id"])
    holds=report["holds"]
    expected={"blank update; old value preserved","duplicate SKU; all rows held","unknown SKU; cannot create products"}
    actual={h["source_reason"] for h in holds}
    good=(len(holds)==3 and actual==expected and report["summary"]["pending_decisions"]==2
          and report["summary"]["risk_counts"]["high"]>=2)
    return {"passed":good,"count":count,"processing_seconds":round(seconds,4),
            "holds":len(holds),"proposed_changes":report["summary"]["changes"],
            "pending_decisions":report["summary"]["pending_decisions"],
            "job_id":result["job_id"],
            "note":"Synthetic correctness smoke benchmark, not measured production accuracy."}

def main():
    p=argparse.ArgumentParser(description="Reproducible synthetic catalog benchmark")
    p.add_argument("--rows",type=int,default=1000)
    a=p.parse_args()
    with tempfile.TemporaryDirectory() as folder:
        result=run(folder,a.rows)
    print(json.dumps(result,indent=2))
    if not result["passed"]:raise SystemExit(1)
if __name__=="__main__":main()
