import csv,tempfile,unittest
from pathlib import Path
import engine,qa
class QATests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.db=self.root/"test.db"
        b=self.root/"base.csv";u=self.root/"update.csv"
        b.write_text("sku,title,price,stock\nA,Item,10,5\n",encoding="utf-8")
        u.write_text("sku,stock\nA,0\n",encoding="utf-8")
        self.job=engine.ingest(self.db,b,u)["job_id"]
        self.change=engine.review(self.db,self.job)["changes"][0]
        self.output=self.root/"out.csv"
    def test_pending_is_blocked(self):
        with self.assertRaises(ValueError):qa.verify(self.db,self.job,self.output)
    def test_approved_export_passes(self):
        engine.decide(self.db,self.change["id"],"approved","operator","confirmed")
        engine.export(self.db,self.job,self.output)
        self.assertTrue(qa.verify(self.db,self.job,self.output)["passed"])
    def test_tampered_export_fails(self):
        engine.decide(self.db,self.change["id"],"approved","operator","confirmed")
        engine.export(self.db,self.job,self.output)
        self.output.write_text("sku,title,price,stock\nA,Item,10,99\n",encoding="utf-8")
        result=qa.verify(self.db,self.job,self.output)
        self.assertFalse(result["passed"])
        self.assertEqual(result["mismatches"][0]["fields"],["stock"])
    def test_extra_sku_fails(self):
        engine.decide(self.db,self.change["id"],"rejected","operator","not approved")
        engine.export(self.db,self.job,self.output)
        with self.output.open("a",encoding="utf-8") as stream:stream.write("B,Injected,1,1\n")
        self.assertFalse(qa.verify(self.db,self.job,self.output)["passed"])
if __name__=="__main__":unittest.main()
