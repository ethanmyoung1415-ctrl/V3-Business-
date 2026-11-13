import tempfile,unittest
from pathlib import Path
import engine

class LowRiskBatchTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name);self.db=root/"test.db"
        b=root/"base.csv";u=root/"update.csv"
        b.write_text("sku,title,price,stock\nA,One,10,100\nB,Two,10,100\nC,Three,10,100\nD,Four,10,20\n")
        u.write_text("sku,stock,price\nA,102,10\nB,0,10\nC,120,10\nD,21,13\n")
        self.job=engine.ingest(self.db,b,u)["job_id"]
    def test_only_small_nonzero_stock_adjustments_are_eligible(self):
        changes=engine.review(self.db,self.job)["changes"]
        eligible=[c for c in changes if engine.eligible_low_risk_stock(c)]
        self.assertEqual({c["sku"] for c in eligible},{"A","D"})
        self.assertEqual({c["field"] for c in eligible},{"stock"})
    def test_batch_approval_preserves_risky_items(self):
        result=engine.approve_low_risk_stock_batch(
            self.db,self.job,"operator","Validated supplier source")
        self.assertEqual(result["approved_count"],2)
        changed=engine.review(self.db,self.job)["changes"]
        approved={(x["sku"],x["field"]) for x in changed if x["status"]=="approved"}
        pending={(x["sku"],x["field"]) for x in changed if x["status"]=="pending"}
        self.assertEqual(approved,{("A","stock"),("D","stock")})
        self.assertIn(("B","stock"),pending)
        self.assertIn(("D","price"),pending)
    def test_short_reason_rejected(self):
        with self.assertRaises(ValueError):
            engine.approve_low_risk_stock_batch(self.db,self.job,"operator","ok")
    def test_repeated_batch_cannot_approve_risky_changes(self):
        engine.approve_low_risk_stock_batch(self.db,self.job,"operator","Verified test data")
        with self.assertRaises(ValueError):
            engine.approve_low_risk_stock_batch(self.db,self.job,"operator","Verified test data")
    def test_hold_blocks_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);b=root/"base.csv";u=root/"up.csv"
            b.write_text("sku,title,price,stock\nA,One,10,100\n")
            u.write_text("sku,stock\nA,102\nA,105\n")
            job=engine.ingest(self.db,b,u)["job_id"]
        with self.assertRaises(ValueError):
            engine.approve_low_risk_stock_batch(self.db,job,"operator","Verified test data")
if __name__=="__main__":unittest.main()
