import json,sqlite3,tempfile,unittest
from pathlib import Path
import backup,operations
class BackupTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.db=root/"source.sqlite3"
        self.target=root/"backup.sqlite3"
        self.restore_db=root/"restore.sqlite3"
        operations.setup(self.db)
    def test_round_trip(self):
        backup.create(self.db,self.target)
        result=backup.restore(self.target,self.restore_db)
        self.assertTrue(result["verified"])
        with sqlite3.connect(self.restore_db) as conn:
            self.assertTrue(conn.execute("SELECT name FROM sqlite_master WHERE name='jobs'").fetchone())
    def test_tampered_backup_blocked(self):
        backup.create(self.db,self.target)
        self.target.write_bytes(self.target.read_bytes()+b"garbage")
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            backup.restore(self.target,self.restore_db)
        self.assertFalse(self.restore_db.exists())
    def test_does_not_overwrite(self):
        backup.create(self.db,self.target)
        with self.assertRaises(ValueError):backup.create(self.db,self.target)
        self.restore_db.write_text("existing")
        with self.assertRaises(ValueError):backup.restore(self.target,self.restore_db)
if __name__=="__main__":unittest.main()
