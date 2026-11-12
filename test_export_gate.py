import sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import engine
class ExportGateTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.db=self.root/"v3.db"
        b=self.root/"baseline.csv";u=self.root/"update.csv"
        b.write_text("sku,title,price,stock\nA,Item,10,5\n",encoding="utf-8")
        u.write_text("sku,stock\nA,0\n",encoding="utf-8")
        self.job=engine.ingest(self.db,b,u)["job_id"]
        change=engine.review(self.db,self.job)["changes"][0]
        engine.decide(self.db,change["id"],"approved","operator","verified")
    def test_verification_failure_blocks_export(self):
        output=self.root/"export.csv"
        with patch("qa.verify",return_value={"passed":False}):
            with self.assertRaisesRegex(ValueError,"independent QA"):
                engine.export(self.db,self.job,output)
        self.assertFalse(output.exists())
        self.assertEqual(engine.review(self.db,self.job)["job"]["status"],"review")
    def test_successful_export_has_qa_audit(self):
        output=self.root/"export.csv"
        engine.export(self.db,self.job,output)
        with sqlite3.connect(self.db) as conn:
            rows=conn.execute("SELECT details FROM events WHERE job=? AND kind='export'",(self.job,)).fetchall()
        self.assertEqual(len(rows),1)
        self.assertIn('"independent_qa": "passed"',rows[0][0])
    def test_verifier_exception_removes_partial_file(self):
        output=self.root/"interrupted.csv"
        with patch("qa.verify",side_effect=RuntimeError("verification unavailable")):
            with self.assertRaisesRegex(RuntimeError,"verification unavailable"):
                engine.export(self.db,self.job,output)
        self.assertFalse(output.exists())
        self.assertEqual(engine.review(self.db,self.job)["job"]["status"],"review")
    def test_export_only_once_per_job(self):
        engine.export(self.db,self.job,self.root/"first.csv")
        with self.assertRaisesRegex(ValueError,"already exported"):
            engine.export(self.db,self.job,self.root/"second.csv")
        self.assertFalse((self.root/"second.csv").exists())
if __name__=="__main__":unittest.main()
