import csv,tempfile,unittest
from pathlib import Path
from engine import ingest,review,decide,export

class EngineTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.db=self.root/"test.db"
    def csvfile(self,name,fields,rows):
        p=self.root/name
        with p.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        return p
    def baseline(self):
        return self.csvfile("baseline.csv",["sku","title","price","stock"],[{"sku":"A","title":"Item","price":"10","stock":"4"}])
    def test_zero_stock(self):
        b=self.baseline();u=self.csvfile("up.csv",["sku","stock"],[{"sku":"A","stock":"0"}])
        job=ingest(self.db,b,u)["job_id"];ch=review(self.db,job)["changes"][0]
        self.assertEqual(ch["new"],"0")
        decide(self.db,ch["id"],"approved","operator","verified")
        p=self.root/"out.csv";export(self.db,job,p)
        with p.open() as f:self.assertEqual(list(csv.DictReader(f))[0]["stock"],"0")
    def test_duplicate_held(self):
        b=self.baseline();u=self.csvfile("up.csv",["sku","stock"],[{"sku":"A","stock":"3"},{"sku":"A","stock":"5"}])
        job=ingest(self.db,b,u)["job_id"]
        self.assertTrue(review(self.db,job)["holds"])
        with self.assertRaises(ValueError):export(self.db,job,self.root/"out.csv")
    def test_blank_held(self):
        b=self.baseline();u=self.csvfile("up.csv",["sku","title"],[{"sku":"A","title":""}])
        self.assertTrue(ingest(self.db,b,u)["holds"])
    def test_unknown_held(self):
        b=self.baseline();u=self.csvfile("up.csv",["sku","stock"],[{"sku":"B","stock":"2"}])
        self.assertTrue(ingest(self.db,b,u)["holds"])
    def test_pending_blocks_export(self):
        b=self.baseline();u=self.csvfile("up.csv",["sku","price"],[{"sku":"A","price":"12"}])
        job=ingest(self.db,b,u)["job_id"]
        with self.assertRaises(ValueError):export(self.db,job,self.root/"out.csv")
    def test_rejection_preserves_baseline(self):
        b=self.baseline();u=self.csvfile("up.csv",["sku","price"],[{"sku":"A","price":"12"}])
        job=ingest(self.db,b,u)["job_id"];ch=review(self.db,job)["changes"][0]
        decide(self.db,ch["id"],"rejected","operator","not approved")
        p=self.root/"out.csv";export(self.db,job,p)
        with p.open() as f:self.assertEqual(list(csv.DictReader(f))[0]["price"],"10")
    def test_invalid_stock_held(self):
        b=self.baseline();u=self.csvfile("up.csv",["sku","stock"],[{"sku":"A","stock":"-1"}])
        self.assertTrue(ingest(self.db,b,u)["holds"])
if __name__=="__main__":unittest.main()
