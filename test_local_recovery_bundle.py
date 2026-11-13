"""No-cloud synthetic recovery rehearsal tests."""
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
import local_recovery_bundle as recovery

class SyntheticFullRecoveryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.root=root
        self.portal=root/"original-portal.sqlite3"
        with sqlite3.connect(self.portal) as c:
            c.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, status TEXT)")
            c.execute("INSERT INTO demo(status) VALUES('review')")
        self.uploads=root/"uploads";self.uploads.mkdir()
        self.work=root/"workspaces";self.work.mkdir()
        (self.uploads/"store-a").mkdir()
        (self.uploads/"store-a"/"original.csv").write_text("sku,stock\n001,0\n")
        (self.work/"store-a").mkdir()
        with sqlite3.connect(self.work/"store-a"/"engine.sqlite3") as c:
            c.execute("CREATE TABLE processing (job TEXT)")
            c.execute("INSERT INTO processing VALUES('synthetic')")
        (self.work/"store-a"/"export.csv").write_text("sku,title,price,stock\n001,Test,10,0\n")
        self.archive=root/"bundle.zip"
        self.target=root/"restored"
    def backup(self):
        return recovery.create(self.portal,self.uploads,self.work,self.archive,
                               synthetic_only=True)
    def test_full_synthetic_recovery(self):
        result=self.backup()
        self.assertEqual(result["verified_files"],4)
        self.assertTrue(recovery.inspect(self.archive)["verified"])
        restored=recovery.restore(self.archive,self.target,synthetic_only=True)
        self.assertEqual(restored["files"],4)
        with sqlite3.connect(self.target/"portal.sqlite3") as c:
            self.assertEqual(c.execute("SELECT status FROM demo").fetchone()[0],"review")
        with sqlite3.connect(self.target/"workspaces"/"store-a"/"engine.sqlite3") as c:
            self.assertEqual(c.execute("SELECT job FROM processing").fetchone()[0],"synthetic")
        self.assertEqual((self.target/"uploads"/"store-a"/"original.csv").read_text(),
                         "sku,stock\n001,0\n")
        self.assertEqual((self.target/"workspaces"/"store-a"/"export.csv").read_text(),
                         "sku,title,price,stock\n001,Test,10,0\n")
    def test_missing_acknowledgement_blocks_both(self):
        with self.assertRaises(PermissionError):
            recovery.create(self.portal,self.uploads,self.work,self.archive)
        self.backup()
        with self.assertRaises(PermissionError):
            recovery.restore(self.archive,self.target)
    def test_does_not_overwrite(self):
        self.backup()
        with self.assertRaises(ValueError):self.backup()
        self.target.mkdir()
        with self.assertRaises(ValueError):
            recovery.restore(self.archive,self.target,synthetic_only=True)
    def test_rejects_symlink_source(self):
        link=self.uploads/"linked.csv"
        try:link.symlink_to(self.portal)
        except (NotImplementedError,OSError):self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(ValueError,"symlink"):
            self.backup()
    def test_archive_mutation_detected(self):
        self.backup()
        altered=self.root/"altered.zip"
        with zipfile.ZipFile(self.archive) as source,zipfile.ZipFile(
                altered,"w",compression=zipfile.ZIP_DEFLATED) as out:
            for name in source.namelist():
                content=source.read(name)
                if name=="uploads/store-a/original.csv":
                    content=b"sku,stock\n001,999\n"
                out.writestr(name,content)
        with self.assertRaisesRegex(ValueError,"digest"):
            recovery.inspect(altered)
        self.assertFalse(self.target.exists())
    def test_zip_slip_rejected(self):
        self.backup()
        altered=self.root/"bad.zip"
        with zipfile.ZipFile(self.archive) as source,zipfile.ZipFile(
                altered,"w") as out:
            for name in source.namelist():
                if name!="manifest.json":out.writestr(name,source.read(name))
            manifest=json.loads(source.read("manifest.json"))
            manifest["files"][0]["path"]="../../secret"
            out.writestr("manifest.json",json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,"unsafe archive"):
            recovery.inspect(altered)
    def test_recovery_does_not_restore_into_existing_data(self):
        self.backup()
        self.target.mkdir()
        (self.target/"other.txt").write_text("existing")
        with self.assertRaisesRegex(ValueError,"already exists"):
            recovery.restore(self.archive,self.target,synthetic_only=True)
        self.assertEqual((self.target/"other.txt").read_text(),"existing")
if __name__=="__main__":unittest.main()
