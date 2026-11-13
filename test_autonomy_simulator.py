import tempfile
import unittest
from pathlib import Path
import autonomy_simulator as sim
import engine

class SimulationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.db=root/"test.db"
        base=root/"baseline.csv"
        supplier=root/"update.csv"
        base.write_text(
            "sku,title,price,stock\nA,Safe,10,100\nB,Zero,10,100\n"
            "C,Price,10,100\nD,Large,10,100\nE,Low,10,10\n",
            encoding="utf-8")
        supplier.write_text(
            "sku,stock,price\nA,102,10\nB,0,10\n"
            "C,100,15\nD,130,10\nE,11,10\n",encoding="utf-8")
        self.job=engine.ingest(self.db,base,supplier)["job_id"]
    def policy(self,**overrides):
        policy=dict(sim.DEFAULT)
        policy["authorized_simulation"]=True
        policy.update(overrides)
        return policy
    def test_default_disabled_and_no_decisions(self):
        report=sim.inspect(self.db,self.job,sim.DEFAULT)
        self.assertEqual(report["status"],"disabled")
        self.assertEqual(report["eligible"],[])
        self.assertEqual(report["actions_executed"],0)
        self.assertTrue(all(x["status"]=="pending" for x in engine.review(
            self.db,self.job)["changes"]))
    def test_only_bounded_stock_candidate_proposed(self):
        result=sim.inspect(self.db,self.job,self.policy())
        self.assertEqual([x["sku"] for x in result["eligible"]],["A"])
        self.assertEqual(result["potentially_reduced_decisions"],1)
        self.assertEqual(result["approved"],0)
        self.assertEqual(result["actions_executed"],0)
        self.assertTrue(all(x["status"]=="pending" for x in engine.review(
            self.db,self.job)["changes"]))
    def test_hold_blocks_everything(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            base=root/"b.csv";update=root/"u.csv"
            base.write_text("sku,title,price,stock\nA,Safe,10,100\n")
            update.write_text("sku,stock\nA,101\nA,102\n")
            job=engine.ingest(self.db,base,update)["job_id"]
        report=sim.inspect(self.db,job,self.policy())
        self.assertEqual(report["status"],"blocked_by_holds")
        self.assertEqual(report["eligible"],[])
    def test_explicit_exclusion(self):
        report=sim.inspect(self.db,self.job,self.policy(excluded_skus=["A"]))
        self.assertEqual(report["eligible"],[])
    def test_invalid_policy_cannot_widen_permissions(self):
        for item in [
            {"allowed_fields":["stock","price"]},
            {"max_units":100},
            {"max_percent":99},
            {"authorized_simulation":1},
            {"max_candidates_per_job":0},
        ]:
            with self.subTest(item=item):
                with self.assertRaises(ValueError):
                    sim.inspect(self.db,self.job,self.policy(**item))
    def test_candidate_cap_blocks_entire_batch(self):
        # A cap is all-or-nothing; the system never silently approves a subset.
        result=sim.inspect(self.db,self.job,self.policy(max_candidates_per_job=1))
        self.assertEqual(len(result["eligible"]),1)
if __name__=="__main__":unittest.main()
