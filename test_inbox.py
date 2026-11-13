import tempfile,unittest
from pathlib import Path
import inbox,operations
class InboxTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        self.db=root/"db.sqlite3";self.inbox=root/"inbox";self.inbox.mkdir()
        job=self.inbox/"job-1";job.mkdir()
        (job/"baseline.csv").write_text("sku,title,price,stock\nA,Item,10,5\n")
        (job/"update.csv").write_text("sku,stock\nA,0\n")
        (job/"READY").write_text("")
        self.job=job
    def test_process_once_with_marker(self):
        first=inbox.scan(self.db,self.inbox)
        second=inbox.scan(self.db,self.inbox)
        self.assertEqual(len(first["enqueued"]),1)
        self.assertEqual(len(second["enqueued"]),0)
        self.assertTrue((self.job/"QUEUED").exists())
        self.assertEqual(operations.work_once(self.db)["status"],"review")
    def test_unready_not_processed(self):
        (self.job/"READY").unlink()
        self.assertEqual(inbox.scan(self.db,self.inbox)["enqueued"],[])
    def test_missing_file_does_not_enqueue(self):
        (self.job/"update.csv").unlink()
        result=inbox.scan(self.db,self.inbox)
        self.assertTrue(result["errors"])
        self.assertEqual(result["enqueued"],[])
    def test_symlink_job_ignored(self):
        link=self.inbox/"link"
        try:link.symlink_to(self.job,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest("symlinks unavailable")
        self.assertEqual(len(inbox.scan(self.db,self.inbox)["enqueued"]),1)
if __name__=="__main__":unittest.main()
