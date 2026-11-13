import os,tempfile,unittest
from pathlib import Path
from intake import stage_pair,stage_csv
class IntakeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.b=self.root/"baseline.csv";self.u=self.root/"update.csv"
        self.b.write_text("sku,title,price,stock\nA,Test,1,2\n")
        self.u.write_text("sku,stock\nA,0\n")
    def test_snapshot_remains_stable_after_source_changes(self):
        staged=stage_pair(self.b,self.u,self.root/"db.sqlite3")
        self.b.write_text("sku,title,price,stock\nA,Changed,1,2\n")
        self.assertIn("Test",staged[0][0].read_text())
        self.assertNotIn("Changed",staged[0][0].read_text())
    def test_requires_csv_extension(self):
        bad=self.root/"bad.txt";bad.write_text("hello")
        with self.assertRaises(ValueError):stage_csv(bad,self.root/"snapshots")
    def test_reject_symlink(self):
        link=self.root/"link.csv"
        try:link.symlink_to(self.b)
        except (OSError,NotImplementedError):self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):stage_csv(link,self.root/"snapshots")
    def test_reject_directory(self):
        folder=self.root/"dir.csv";folder.mkdir()
        with self.assertRaises(ValueError):stage_csv(folder,self.root/"snapshots")
    def test_reject_symlink_staging(self):
        actual=self.root/"storage";actual.mkdir()
        link=self.root/"link"
        try:link.symlink_to(actual,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):stage_csv(self.b,link)
if __name__=="__main__":unittest.main()
