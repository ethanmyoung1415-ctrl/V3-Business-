import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path
from engine import decide, review, export
from operations import enqueue, claim, work_once, dashboard, mark_stale

class WorkQueueTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.db=self.root/"db.sqlite3"
        self.baseline=self.make("base.csv",["sku","title","price","stock"],[["A","Item","10","4"]])
        self.update=self.make("update.csv",["sku","stock"],[["A","0"]])
    def make(self,name,header,rows):
        p=self.root/name
        with p.open("w",newline="") as f:
            w=csv.writer(f);w.writerow(header);w.writerows(rows)
        return p
    def test_review_and_explicit_approval(self):
        enqueue(self.db,self.baseline,self.update)
        result=work_once(self.db)
        self.assertEqual(result["status"],"review")
        change=review(self.db,result["job_id"])["changes"][0]
        with self.assertRaises(ValueError):export(self.db,result["job_id"],self.root/"out.csv")
        decide(self.db,change["id"],"approved","operator","validated")
        out=self.root/"out.csv";export(self.db,result["job_id"],out)
        with out.open() as f:self.assertEqual(list(csv.DictReader(f))[0]["stock"],"0")
    def test_duplicate_submission_reused(self):
        a=enqueue(self.db,self.baseline,self.update)
        b=enqueue(self.db,self.baseline,self.update)
        self.assertEqual(a["work_id"],b["work_id"])
        self.assertTrue(b["already_exists"])
    def test_changed_input_fails_closed(self):
        enqueue(self.db,self.baseline,self.update)
        self.update.write_text("sku,stock\\nA,8\\n")
        result=work_once(self.db)
        self.assertEqual(result["status"],"retry_or_failed")
        self.assertEqual(dashboard(self.db)["counts"]["failed"],1)
    def test_only_one_worker_can_claim(self):
        enqueue(self.db,self.baseline,self.update)
        self.assertIsNotNone(claim(self.db))
        self.assertIsNone(claim(self.db))
    def test_expired_lease_requires_manual_review(self):
        enqueue(self.db,self.baseline,self.update)
        item=claim(self.db)
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE work_queue SET lease_until=? WHERE id=?",
                         ("2000-01-01T00:00:00+00:00",item["id"]))
        self.assertIsNone(claim(self.db))
        self.assertEqual(mark_stale(self.db),[item["id"]])
        self.assertEqual(dashboard(self.db)["counts"]["failed"],1)

if __name__=="__main__":unittest.main()
