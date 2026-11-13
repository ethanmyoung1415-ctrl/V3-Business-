"""Release-digest tests: QA rejects a changed output even if DB is manipulated."""
import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path
import engine
import qa

class ReleasedDigestTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.db=self.root/"engine.sqlite3"
        b=self.root/"base.csv";u=self.root/"update.csv"
        b.write_text("sku,title,price,stock\nA,Item,10,8\n",encoding="utf-8")
        u.write_text("sku,stock\nA,0\n",encoding="utf-8")
        self.job=engine.ingest(self.db,b,u)["job_id"]
        change=engine.review(self.db,self.job)["changes"][0]
        engine.decide(self.db,change["id"],"approved","operator","verified example")
        self.output=self.root/"released.csv"
        engine.export(self.db,self.job,self.output)
    def test_released_file_reconciles(self):
        self.assertTrue(qa.verify(self.db,self.job,self.output)["passed"])
    def test_deleted_release_event_blocks_download(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("DELETE FROM events WHERE job=? AND kind='export'",(self.job,))
        with self.assertRaisesRegex(ValueError,"audit reconciliation|release record"):
            qa.verify(self.db,self.job,self.output)
    def test_manipulated_release_sha_blocks_download(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE events SET details=? WHERE job=? AND kind='export'",
                ('{"sha256":"forged","independent_qa":"passed"}',self.job))
        with self.assertRaisesRegex(ValueError,"released export hash"):
            qa.verify(self.db,self.job,self.output)
    def test_changed_file_even_if_db_edited_cannot_pass(self):
        # Editing both output and an approved DB value used to fool a naive
        # row-to-file QA, but cannot reproduce the original release digest.
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE changes SET new='10' WHERE job=? AND field='stock'",
                         (self.job,))
        self.output.write_text("sku,title,price,stock\nA,Item,10,10\n")
        with self.assertRaisesRegex(ValueError,"released export hash"):
            qa.verify(self.db,self.job,self.output)
if __name__=="__main__":unittest.main()
