"""One-command synthetic two-customer V3 workflow, no credentials or outside access."""
import argparse
import json
import tempfile
from pathlib import Path
import engine
import metrics
import operations
import qa
import workspaces

def sample(folder,customer,stock):
    folder=Path(folder)
    baseline=folder/(customer+"-baseline.csv")
    update=folder/(customer+"-update.csv")
    baseline.write_text("sku,title,price,stock\nA,Sample Item,10,7\n",encoding="utf-8")
    update.write_text(f"sku,stock\nA,{stock}\n",encoding="utf-8")
    return baseline,update

def simulate(root):
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    customer_a=workspaces.create_customer(root/"customers","Example Store A")["customer_id"]
    customer_b=workspaces.create_customer(root/"customers","Example Store B")["customer_id"]
    results=[]
    for index,(customer,target) in enumerate(((customer_a,"0"),(customer_b,"5"))):
        b,u=sample(root,f"store-{index}",target)
        queue=workspaces.enqueue(root/"customers",customer,b,u)
        process=workspaces.work_once(root/"customers",customer)
        if process["status"]!="review":raise RuntimeError("queue failed to process")
        job=process["job_id"]
        current=workspaces.review(root/"customers",customer,job)
        if len(current["changes"])!=1:raise RuntimeError("unexpected changes")
        change=current["changes"][0]
        workspaces.decide(root/"customers",customer,job,change["id"],
                          "approved","demo-operator","synthetic demo authorization")
        db=workspaces.customer_db(root/"customers",customer)
        output=root/(f"store-{index}-approved.csv")
        engine.export(db,job,output)
        verified=qa.verify(db,job,output)
        if not verified["passed"]:raise RuntimeError("independent QA failed")
        report=metrics.snapshot(db)
        results.append({"customer_id":customer,"job_id":job,
                        "updated_stock":target,"qa_passed":True,
                        "monthly_revenue":None,
                        "operator_attention":report["totals"]["requires_operator_attention"]})
    try:
        workspaces.review(root/"customers",customer_b,results[0]["job_id"])
        raise RuntimeError("cross-customer isolation check failed")
    except ValueError:pass
    return {"passed":True,"simulated_customers":2,"customer_results":results,
            "cross_customer_read_blocked":True,"real_customer_data_used":False}

def main():
    p=argparse.ArgumentParser(description="Safe synthetic V3 demo")
    p.add_argument("--output-dir",help="optional directory; must be empty")
    args=p.parse_args()
    if args.output_dir:
        root=Path(args.output_dir)
        if root.exists() and any(root.iterdir()):
            p.error("output directory must be empty")
        result=simulate(root)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            result=simulate(tmp)
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
