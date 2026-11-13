import json,tempfile,unittest
from pathlib import Path
import engine,reporting
class ReportingTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.db=self.root/"engine.sqlite3"
        b=self.root/"b.csv";u=self.root/"u.csv"
        b.write_text("sku,title,price,stock\nA,Main,10,12\nB,Other,15,8\n")
        u.write_text("sku,stock\nA,0\nB,\n")
        self.job=engine.ingest(self.db,b,u)["job_id"]
    def test_report_explains_exclusions_and_approved_changes(self):
        for held in engine.listed_holds(self.db,self.job):
            engine.exclude_hold(self.db,self.job,held["token"],"operator",
                                "Supplier provided blank record; retain old")
        change=engine.review(self.db,self.job)["changes"][0]
        engine.decide(self.db,change["id"],"approved","operator","Source checked")
        output=self.root/"approved.csv"
        engine.export(self.db,self.job,output)
        report=reporting.generate(self.db,self.job,output)
        self.assertTrue(report["verification"]["passed"])
        self.assertEqual(report["summary"]["approved_changes"],1)
        self.assertEqual(report["summary"]["excluded_holds"],1)
        self.assertEqual(report["summary"]["unresolved_holds"],0)
        self.assertEqual(report["verification"]["row_count"],2)
        serialized=reporting.serialize(report)
        self.assertEqual(json.loads(serialized)["job_id"],self.job)
    def test_unverified_export_is_blocked(self):
        with self.assertRaises(ValueError):
            reporting.generate(self.db,self.job,self.root/"nonexistent.csv")
    def test_preview_does_not_claim_qa_passed(self):
        preview=reporting.generate(self.db,self.job)
        self.assertFalse(preview["verification"]["passed"])
        self.assertEqual(preview["summary"]["unresolved_holds"],1)
if __name__=="__main__":unittest.main()
