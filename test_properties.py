"""Deterministic randomized invariants for catalog processing and approval rules."""
import random
import tempfile
import unittest
from pathlib import Path
import engine
import qa

class CatalogPropertyTests(unittest.TestCase):
    def test_randomized_stock_changes_preserve_only_approved_values(self):
        randomizer=random.Random(20261112)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            db=root/"checks.db"
            for case in range(40):
                baseline=root/f"baseline-{case}.csv"
                supplier=root/f"supplier-{case}.csv"
                target=randomizer.randint(0,1000)
                baseline.write_text("sku,title,price,stock\nA,Item,10,100\n",
                                    encoding="utf-8")
                supplier.write_text(f"sku,stock\nA,{target}\n",encoding="utf-8")
                job=engine.ingest(db,baseline,supplier)["job_id"]
                changes=engine.review(db,job)["changes"]
                if target!=100:
                    self.assertEqual(len(changes),1)
                    self.assertEqual(changes[0]["status"],"pending")
                    with self.assertRaises(ValueError):
                        engine.export(db,job,root/f"premature-{case}.csv")
                    approved=case%2==0
                    engine.decide(db,changes[0]["id"],
                                  "approved" if approved else "rejected",
                                  "test-operator","randomized invariant test")
                    expected=target if approved else 100
                else:
                    expected=100
                output=root/f"verified-{case}.csv"
                engine.export(db,job,output)
                self.assertTrue(qa.verify(db,job,output)["passed"])
                self.assertIn(f",10,{expected}\n",output.read_text())
    def test_duplicate_records_always_block_export(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for case in range(10):
                b=root/f"b-{case}.csv";u=root/f"u-{case}.csv"
                b.write_text("sku,title,price,stock\nA,Item,10,4\n")
                u.write_text(f"sku,stock\nA,{case}\nA,{case+1}\n")
                db=root/"dupes.db"
                job=engine.ingest(db,b,u)["job_id"]
                self.assertTrue(engine.review(db,job)["holds"])
                with self.assertRaises(ValueError):
                    engine.export(db,job,root/f"unsafe-{case}.csv")
if __name__=="__main__":unittest.main()
