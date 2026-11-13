"""Fail-closed excluded-row review tests."""
import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path
import engine
import qa

class HoldExclusionTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        self.db=root/"engine.sqlite3"
        self.out=root/"approved.csv"
        b=root/"baseline.csv"
        u=root/"supplier.csv"
        b.write_text("sku,title,price,stock\nA,Original,10,9\nB,Other,5,8\n",encoding="utf-8")
        u.write_text("sku,stock\nA,0\nB,\nC,3\n",encoding="utf-8")
        self.job=engine.ingest(self.db,b,u)["job_id"]
    def test_partial_export_requires_explicit_exclusion(self):
        hold_rows=engine.listed_holds(self.db,self.job)
        self.assertEqual(len(hold_rows),2)
        change=engine.review(self.db,self.job)["changes"][0]
        engine.decide(self.db,change["id"],"approved","operator","Stock confirmed")
        with self.assertRaises(ValueError):
            engine.export(self.db,self.job,self.out)
        for hold in hold_rows:
            engine.exclude_hold(self.db,self.job,hold["token"],"operator",
                                "Skip malformed source and retain original")
        engine.export(self.db,self.job,self.out)
        self.assertTrue(qa.verify(self.db,self.job,self.out)["passed"])
        with self.out.open(newline="",encoding="utf-8") as f:
            data={row["sku"]:row for row in csv.DictReader(f)}
        self.assertEqual(data["A"]["stock"],"0")
        self.assertEqual(data["B"]["stock"],"8")
        self.assertNotIn("C",data)
        with sqlite3.connect(self.db) as db:
            events=db.execute(
                "SELECT details FROM events WHERE job=? AND kind='hold_excluded'",
                (self.job,)).fetchall()
        self.assertEqual(len(events),2)
        self.assertTrue(all("held_source_data_never_applied" in x[0] for x in events))
    def test_no_exclusion_with_short_reason(self):
        hold=engine.listed_holds(self.db,self.job)[0]
        with self.assertRaises(ValueError):
            engine.exclude_hold(self.db,self.job,hold["token"],"operator","ok")
        self.assertEqual(len(engine.listed_holds(self.db,self.job)),2)
    def test_replay_rejected(self):
        hold=engine.listed_holds(self.db,self.job)[0]
        engine.exclude_hold(self.db,self.job,hold["token"],"operator",
                            "Source row excluded after verification")
        with self.assertRaises(ValueError):
            engine.exclude_hold(self.db,self.job,hold["token"],"operator",
                                "Try to ignore same row twice")
    def test_cannot_exclude_after_export(self):
        hold=engine.listed_holds(self.db,self.job)[0]
        for entry in engine.listed_holds(self.db,self.job):
            engine.exclude_hold(self.db,self.job,entry["token"],"operator",
                                "Verified row intentionally excluded")
        change=engine.review(self.db,self.job)["changes"][0]
        engine.decide(self.db,change["id"],"rejected","operator","Not confirmed")
        engine.export(self.db,self.job,self.out)
        with self.assertRaises(ValueError):
            engine.exclude_hold(self.db,self.job,hold["token"],"operator",
                                "Too late to change export decision")
if __name__=="__main__":
    unittest.main()
