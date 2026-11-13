"""Synthetic release receipt tests; no real credentials or network calls."""
import json
import tempfile
import unittest
from pathlib import Path
import engine
import reporting
import release_receipt

KEY=bytes(range(32))
OTHER_KEY=bytes(reversed(range(32)))

class ReleaseReceiptTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.db=self.root/"db.sqlite3"
        b=self.root/"base.csv";u=self.root/"u.csv"
        b.write_text("sku,title,price,stock\nA,Product,10,7\n")
        u.write_text("sku,stock\nA,0\n")
        self.job=engine.ingest(self.db,b,u)["job_id"]
        change=engine.review(self.db,self.job)["changes"][0]
        engine.decide(self.db,change["id"],"approved","human","verified test")
        self.export=self.root/"released.csv"
        engine.export(self.db,self.job,self.export)
        self.report=self.root/"report.json"
        self.report.write_text(reporting.serialize(
            reporting.generate(self.db,self.job,self.export)))
        self.receipt=self.root/"receipt.json"
    def test_release_receipt_round_trip(self):
        release_receipt.issue(self.export,self.report,self.receipt,KEY)
        outcome=release_receipt.verify(self.export,self.report,self.receipt,KEY)
        self.assertTrue(outcome["passed"])
        self.assertFalse(outcome["live_store_verified"])
    def test_wrong_key_rejected(self):
        release_receipt.issue(self.export,self.report,self.receipt,KEY)
        with self.assertRaisesRegex(ValueError,"authentication failed"):
            release_receipt.verify(self.export,self.report,self.receipt,OTHER_KEY)
    def test_report_tampering_detected(self):
        release_receipt.issue(self.export,self.report,self.receipt,KEY)
        report=json.loads(self.report.read_text())
        report["notes"].append("modified after signing")
        self.report.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,"does not match"):
            release_receipt.verify(self.export,self.report,self.receipt,KEY)
    def test_csv_tampering_detected(self):
        release_receipt.issue(self.export,self.report,self.receipt,KEY)
        self.export.write_text("sku,title,price,stock\nA,Product,10,999\n")
        with self.assertRaises(ValueError):
            release_receipt.verify(self.export,self.report,self.receipt,KEY)
    def test_no_overwrite(self):
        release_receipt.issue(self.export,self.report,self.receipt,KEY)
        with self.assertRaisesRegex(ValueError,"already exists"):
            release_receipt.issue(self.export,self.report,self.receipt,KEY)
    def test_missing_verified_report_rejected(self):
        report=json.loads(self.report.read_text())
        report["verification"]["passed"]=False
        self.report.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,"verified-export evidence"):
            release_receipt.issue(self.export,self.report,self.receipt,KEY)
if __name__=="__main__":unittest.main()
