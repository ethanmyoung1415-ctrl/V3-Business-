import tempfile,unittest
from pathlib import Path
import worker,metrics,operations
class InboxWorkerIntegrationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name);self.db=root/"db.sqlite3"
        self.inbox=root/"incoming";self.inbox.mkdir()
        d=self.inbox/"batch-one";d.mkdir()
        (d/"baseline.csv").write_text("sku,title,price,stock\nA,Item,10,2\n",encoding="utf-8")
        (d/"update.csv").write_text("sku,stock\nA,0\n",encoding="utf-8")
        (d/"READY").write_text("",encoding="utf-8")
        self.folder=d
    def test_unattended_intake_to_review(self):
        self.assertEqual(worker.run(self.db,interval=0.1,max_cycles=1,inbox_dir=self.inbox),1)
        report=metrics.snapshot(self.db)
        self.assertEqual(report["totals"]["pending_decisions"],1)
        self.assertEqual(report["queue_counts"].get("review"),1)
        self.assertTrue((self.folder/"QUEUED").exists())
        self.assertEqual(worker.run(self.db,interval=0.1,max_cycles=1,inbox_dir=self.inbox),1)
        self.assertEqual(metrics.snapshot(self.db)["totals"]["jobs"],1)
if __name__=="__main__":unittest.main()
