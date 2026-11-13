import json,tempfile,unittest,zipfile
from pathlib import Path
from workspace_archive import create,restore,verify_archive

class WorkspaceArchiveTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.workspace=self.root/"work"
        (self.workspace/"exports").mkdir(parents=True)
        self.database=self.workspace/"engine.sqlite3"
        self.database.write_bytes(b"synthetic database fixture")
        (self.workspace/"exports"/"approved.csv").write_text("sku,stock\nA,0\n")
        self.archive=self.root/"backup.zip"
        self.restored=self.root/"restored"
    def test_round_trip_includes_export_and_data(self):
        made=create(self.workspace,self.archive)
        self.assertEqual(made["file_count"],2)
        self.assertTrue(verify_archive(self.archive)["verified"])
        result=restore(self.archive,self.restored)
        self.assertEqual(result["file_count"],2)
        self.assertEqual((self.restored/"engine.sqlite3").read_bytes(),
                         self.database.read_bytes())
        self.assertIn("A,0",(self.restored/"exports"/"approved.csv").read_text())
    def test_no_overwrite(self):
        create(self.workspace,self.archive)
        with self.assertRaises(ValueError):create(self.workspace,self.archive)
        self.restored.mkdir()
        with self.assertRaises(ValueError):restore(self.archive,self.restored)
    def test_reject_symlink(self):
        link=self.workspace/"leak.csv"
        try:link.symlink_to(self.database)
        except (OSError,NotImplementedError):self.skipTest("symlink unavailable")
        with self.assertRaises(ValueError):create(self.workspace,self.archive)
    def test_reject_extra_file_in_archive(self):
        create(self.workspace,self.archive)
        with zipfile.ZipFile(self.archive,"a") as zf:
            zf.writestr("../outside.txt","do not extract")
        with self.assertRaises(ValueError):restore(self.archive,self.restored)
        self.assertFalse(self.restored.exists())
    def test_content_tampering_fails_verification(self):
        create(self.workspace,self.archive)
        with zipfile.ZipFile(self.archive,"a") as zf:
            zf.writestr("new.csv","unlisted")
        with self.assertRaises(ValueError):verify_archive(self.archive)
    def test_archive_inside_workspace_forbidden(self):
        with self.assertRaises(ValueError):
            create(self.workspace,self.workspace/"archive.zip")
if __name__=="__main__":unittest.main()
