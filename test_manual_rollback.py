import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path
import engine
import manual_rollback

class ManualRollbackTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.db=self.root/"engine.db"
        base=self.root/"base.csv"
        update=self.root/"update.csv"
        base.write_text("sku,title,price,stock\nA,Product,10,8\n",encoding="utf-8")
        update.write_text("sku,stock\nA,0\n",encoding="utf-8")
        self.job=engine.ingest(self.db,base,update)["job_id"]
        self.release=self.root/"released.csv"
        self.rollback=self.root/"rollback.csv"
    def release_job(self):
        changes=engine.review(self.db,self.job)["changes"]
        for change in changes:
            engine.decide(self.db,change["id"],"approved","operator","verified example")
        engine.export(self.db,self.job,self.release)
    def test_rollback_requires_released_job(self):
        with self.assertRaisesRegex(ValueError,"released jobs"):
            manual_rollback.prepare(self.db,self.job,self.release,self.rollback,
                                    "operator","confirmed required reversal")
    def test_baseline_snapshot_is_reconstructed_and_audited(self):
        self.release_job()
        result=manual_rollback.prepare(self.db,self.job,self.release,self.rollback,
                                       "operator","confirmed required reversal")
        self.assertFalse(result["external_store_modified"])
        with self.rollback.open(newline="") as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(rows[0]["stock"],"8")
        self.assertTrue(manual_rollback.verify_baseline(self.db,self.job,self.rollback)["passed"])
        with sqlite3.connect(self.db) as c:
            events=c.execute(
                "SELECT COUNT(*) FROM events WHERE job=? AND kind='manual_rollback_prepared'",
                (self.job,)).fetchone()[0]
        self.assertEqual(events,1)
    def test_release_tampering_blocks_rollback(self):
        self.release_job()
        self.release.write_text("sku,title,price,stock\nA,Product,10,9\n")
        with self.assertRaises(ValueError):
            manual_rollback.prepare(self.db,self.job,self.release,self.rollback,
                                    "operator","confirmed required reversal")
        self.assertFalse(self.rollback.exists())
    def test_cannot_overwrite(self):
        self.release_job()
        self.rollback.write_text("existing")
        with self.assertRaisesRegex(ValueError,"already exists"):
            manual_rollback.prepare(self.db,self.job,self.release,self.rollback,
                                    "operator","confirmed required reversal")
        self.assertEqual(self.rollback.read_text(),"existing")
    def test_meaningful_reason_required(self):
        self.release_job()
        with self.assertRaises(ValueError):
            manual_rollback.prepare(self.db,self.job,self.release,self.rollback,
                                    "operator","oops")
    def test_tampered_rollback_detected(self):
        self.release_job()
        manual_rollback.prepare(self.db,self.job,self.release,self.rollback,
                                "operator","confirmed required reversal")
        self.rollback.write_text("sku,title,price,stock\nA,Product,10,500\n")
        with self.assertRaisesRegex(ValueError,"differs"):
            manual_rollback.verify_baseline(self.db,self.job,self.rollback)
if __name__=="__main__":unittest.main()
