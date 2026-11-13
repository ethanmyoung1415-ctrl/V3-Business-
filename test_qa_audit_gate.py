"""Tampered decision event cannot pass independent CSV release QA."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
import engine
import qa

class AuditGatedQATests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        self.db=root/"engine.sqlite3";self.out=root/"approved.csv"
        base=root/"baseline.csv";up=root/"supplier.csv"
        base.write_text("sku,title,price,stock\nA,Sample,10,5\n")
        up.write_text("sku,stock\nA,0\n")
        self.job=engine.ingest(self.db,base,up)["job_id"]
        self.change=engine.review(self.db,self.job)["changes"][0]
    def test_proper_human_event_passes_QA(self):
        engine.decide(self.db,self.change["id"],"approved","human","source checked")
        engine.export(self.db,self.job,self.out)
        evidence=qa.verify(self.db,self.job,self.out)
        self.assertTrue(evidence["passed"])
        self.assertTrue(evidence["audit_reconciled"])
    def test_forged_approval_status_fails_before_export(self):
        with sqlite3.connect(self.db) as c:
            c.execute("UPDATE changes SET status='approved' WHERE id=?",(
                self.change["id"],))
        with self.assertRaisesRegex(ValueError,"audit reconciliation"):
            engine.export(self.db,self.job,self.out)
        self.assertFalse(self.out.exists())
    def test_deleted_decision_event_blocks_download(self):
        engine.decide(self.db,self.change["id"],"approved","human","source checked")
        engine.export(self.db,self.job,self.out)
        with sqlite3.connect(self.db) as c:
            c.execute("DELETE FROM events WHERE job=? AND kind='decision'",(
                self.job,))
        with self.assertRaisesRegex(ValueError,"audit reconciliation"):
            qa.verify(self.db,self.job,self.out)
if __name__=="__main__":unittest.main()
