import tempfile,unittest
from pathlib import Path
import metrics,operations
class MetricTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.db=root/"local.db"
        b=root/"b.csv";u=root/"u.csv"
        b.write_text("sku,title,price,stock\nA,Item,10,5\n")
        u.write_text("sku,stock\nA,0\n")
        self.b=b;self.u=u
    def test_empty(self):
        operations.setup(self.db)
        report=metrics.snapshot(self.db)
        self.assertEqual(report["operational_status"],"idle")
        self.assertEqual(report["totals"]["jobs"],0)
    def test_pending(self):
        operations.enqueue(self.db,self.b,self.u)
        self.assertEqual(metrics.snapshot(self.db)["operational_status"],"processing")
        operations.work_once(self.db)
        report=metrics.snapshot(self.db)
        self.assertEqual(report["operational_status"],"attention_required")
        self.assertEqual(report["totals"]["pending_decisions"],1)
        self.assertEqual(report["totals"]["requires_operator_attention"],1)
if __name__=="__main__":unittest.main()
