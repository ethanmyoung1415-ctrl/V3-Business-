import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import audit_integrity
import engine

class IndependentAuditTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.db=self.root/"audit.sqlite3"
        base=self.root/"baseline.csv"
        update=self.root/"supplier.csv"
        base.write_text("sku,title,price,stock\nA,Item,10,12\nB,Other,5,4\n",encoding="utf-8")
        update.write_text("sku,stock\nA,11\nB,0\n",encoding="utf-8")
        self.job=engine.ingest(self.db,base,update)["job_id"]
    def test_initial_job_passes(self):
        result=audit_integrity.verify_job(self.db,self.job)
        self.assertTrue(result["passed"],result)
        self.assertEqual(result["verified_decisions"],0)
    def test_decisions_reconcile(self):
        for item in engine.review(self.db,self.job)["changes"]:
            engine.decide(self.db,item["id"],"approved","operator","source confirmed")
        self.assertTrue(audit_integrity.verify_job(self.db,self.job)["passed"])
        engine.export(self.db,self.job,self.root/"out.csv")
        self.assertTrue(audit_integrity.verify_job(self.db,self.job)["passed"])
    def test_mismatched_change_status_detected(self):
        change=engine.review(self.db,self.job)["changes"][0]
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE changes SET status='approved' WHERE id=?",(change["id"],))
        failures=audit_integrity.verify_job(self.db,self.job)["failures"]
        self.assertIn("decision_event_missing_or_mismatched",failures)
    def test_modified_baseline_detected(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE base SET stock='100' WHERE job=? AND sku='A'",(self.job,))
        self.assertIn("change_old_value_differs_from_baseline",
                      audit_integrity.verify_job(self.db,self.job)["failures"])
    def test_hold_exclusions_reconcile(self):
        base=self.root/"another-base.csv"
        update=self.root/"another-supplier.csv"
        base.write_text("sku,title,price,stock\nA,Item,10,12\n")
        update.write_text("sku,stock\nA,\n")
        job=engine.ingest(self.db,base,update)["job_id"]
        holds=engine.listed_holds(self.db,job)
        self.assertEqual(len(holds),1)
        self.assertTrue(audit_integrity.verify_job(self.db,job)["passed"])
        engine.exclude_hold(self.db,job,holds[0]["token"],
                            "operator","confirmed exclusion of invalid supplier row")
        result=audit_integrity.verify_job(self.db,job)
        self.assertTrue(result["passed"],result)
        self.assertEqual(result["excluded_holds"],1)
    def test_missing_exclusion_event_detected(self):
        base=self.root/"hold-base.csv"
        update=self.root/"hold-supplier.csv"
        base.write_text("sku,title,price,stock\nA,Item,10,12\n")
        update.write_text("sku,stock\nA,\n")
        job=engine.ingest(self.db,base,update)["job_id"]
        token=engine.listed_holds(self.db,job)[0]["token"]
        engine.exclude_hold(self.db,job,token,"operator",
                            "source record confirmed invalid")
        with sqlite3.connect(self.db) as conn:
            conn.execute("DELETE FROM events WHERE job=? AND kind='hold_excluded'",(job,))
        self.assertIn("hold_state_does_not_match_exclusions",
                      audit_integrity.verify_job(self.db,job)["failures"])
if __name__=="__main__":unittest.main()
