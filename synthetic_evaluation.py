"""Deterministic synthetic catalog evaluation with known injected anomalies.

Measures rule behavior on artificial data, not customer error rates or
operational impact. No accounts, external services or actual merchant data.
"""
import csv
import json
import tempfile
from collections import Counter
from pathlib import Path
import engine
import triage

def generate(path,count=300):
    if count<100 or count>20000:
        raise ValueError("evaluation count must be 100–20000")
    root=Path(path)
    root.mkdir(parents=True,exist_ok=True)
    baseline=root/"reference.csv"
    supplier=root/"supplier.csv"
    baseline_rows=[]
    update_rows=[]
    expected_holds=set()
    expected_changes={}
    for i in range(count):
        sku=f"TEST-{i:06d}"
        baseline_rows.append({"sku":sku,"title":f"Synthetic Product {i}",
                              "price":"20","stock":"100"})
        # Each branch deliberately creates one known data outcome.
        case=i%10
        if case==0: # valid zero-stock, high risk
            update_rows.append({"sku":sku,"price":"20","stock":"0"})
            expected_changes[(sku,"stock")]="0"
        elif case==1: # valid small stock change, low risk
            update_rows.append({"sku":sku,"price":"20","stock":"102"})
            expected_changes[(sku,"stock")]="102"
        elif case==2: # large price change, high risk
            update_rows.append({"sku":sku,"price":"30","stock":"100"})
            expected_changes[(sku,"price")]="30"
        elif case==3: # blank update held
            update_rows.append({"sku":sku,"price":"20","stock":""})
            expected_holds.add((sku,"blank update; old value preserved"))
        elif case==4: # duplicate held (all rows for SKU)
            update_rows.extend([
                {"sku":sku,"price":"20","stock":"96"},
                {"sku":sku,"price":"20","stock":"94"},
            ])
            expected_holds.add((sku,"duplicate SKU; all rows held"))
        elif case==5: # unchanged price differing only in decimal representation
            update_rows.append({"sku":sku,"price":"20.00","stock":"100"})
        else: # unaffected
            update_rows.append({"sku":sku,"price":"20","stock":"100"})
    # Unknown SKU must be rejected, not created as a product.
    update_rows.append({"sku":"UNLISTED-999","price":"1","stock":"20"})
    expected_holds.add(("UNLISTED-999","unknown SKU; cannot create products"))
    with baseline.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=engine.FIELDS)
        writer.writeheader();writer.writerows(baseline_rows)
    with supplier.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=("sku","price","stock"))
        writer.writeheader();writer.writerows(update_rows)
    return baseline,supplier,expected_holds,expected_changes

def evaluate(count=300):
    with tempfile.TemporaryDirectory() as folder:
        baseline,supplier,expected_holds,expected_changes=generate(folder,count)
        db=Path(folder)/"evaluation.sqlite3"
        job=engine.ingest(db,baseline,supplier)["job_id"]
        reviewed=engine.review(db,job)
        actual_holds={(entry.get("sku"),entry["reason"]) for entry in reviewed["holds"]}
        actual_changes={(entry["sku"],entry["field"]):entry["new"]
                        for entry in reviewed["changes"]}
        hold_false_negatives=len(expected_holds-actual_holds)
        hold_false_positives=len(actual_holds-expected_holds)
        change_false_negatives=len(set(expected_changes)-set(actual_changes))
        change_false_positives=len(set(actual_changes)-set(expected_changes))
        value_mismatches=sum(actual_changes.get(k)!=v
                             for k,v in expected_changes.items() if k in actual_changes)
        triage_risks=Counter(triage.assess_change(change)["risk"]
                            for change in reviewed["changes"])
        success=not any((
            hold_false_negatives,hold_false_positives,change_false_negatives,
            change_false_positives,value_mismatches
        ))
        return {
            "passed":success,
            "synthetic_rows":count,
            "expected_holds":len(expected_holds),
            "actual_holds":len(actual_holds),
            "expected_changes":len(expected_changes),
            "actual_changes":len(actual_changes),
            "hold_false_negatives":hold_false_negatives,
            "hold_false_positives":hold_false_positives,
            "change_false_negatives":change_false_negatives,
            "change_false_positives":change_false_positives,
            "value_mismatches":value_mismatches,
            "triage_risk_counts":dict(triage_risks),
            "limitation":"These are artificial ground-truth cases, not real-world accuracy measurements.",
        }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2))
