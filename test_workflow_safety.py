import csv
import tempfile
import unittest
from pathlib import Path
import engine,operations,triage,worker

class WorkflowSafetyTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.db=self.root/"v3.db"
        self.base=self.root/"base.csv";self.update=self.root/"update.csv"
        self.base.write_text("sku,title,price,stock\nA,Item,10,5\n",encoding="utf-8")
        self.update.write_text("sku,price,stock\nA,15,0\n",encoding="utf-8")
    def test_triage_end_to_end(self):
        operations.enqueue(self.db,self.base,self.update)
        self.assertEqual(worker.run(self.db,interval=0.1,max_cycles=1),1)
        summary=operations.dashboard(self.db)
        job=summary["jobs"][0]["engine_job_id"]
        result=triage.report(self.db,job)
        self.assertEqual(result["summary"]["pending_decisions"],2)
        self.assertEqual(result["summary"]["risk_counts"]["high"],2)
        self.assertTrue(result["summary"]["requires_human"])
        with self.assertRaises(ValueError):
            engine.export(self.db,job,self.root/"export.csv")
    def test_csv_formula_is_rejected(self):
        self.base.write_text("sku,title,price,stock\nA,=HYPERLINK(1),10,5\n",encoding="utf-8")
        with self.assertRaises(ValueError):engine.load(self.base)
    def test_formula_in_updated_title_is_rejected(self):
        self.update.write_text("sku,title\nA,@SUM(1)\n",encoding="utf-8")
        with self.assertRaises(ValueError):engine.load(self.update)
    def test_control_character_in_title_is_rejected(self):
        self.update.write_text('sku,title\nA,"bad\nname"\n',encoding="utf-8")
        with self.assertRaises(ValueError):engine.load(self.update)
if __name__=="__main__":unittest.main()
