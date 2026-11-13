import csv,tempfile,unittest,uuid
from pathlib import Path
import engine
class StableJobIdTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name);self.db=root/"test.db"
        self.base=root/"base.csv";self.update=root/"up.csv"
        self.base.write_text("sku,title,price,stock\nA,Test,10,5\n")
        self.update.write_text("sku,stock\nA,0\n")
        self.id=str(uuid.uuid4())
    def test_retry_reuses_same_work_without_duplicate_change_records(self):
        original=engine.ingest(self.db,self.base,self.update,job_id=self.id)
        duplicate=engine.ingest(self.db,self.base,self.update,job_id=self.id)
        self.assertFalse(original["reused"])
        self.assertTrue(duplicate["reused"])
        self.assertEqual(original["job_id"],duplicate["job_id"])
        self.assertEqual(len(engine.review(self.db,self.id)["changes"]),1)
    def test_changed_input_cannot_reuse_existing_job_id(self):
        engine.ingest(self.db,self.base,self.update,job_id=self.id)
        self.update.write_text("sku,stock\nA,9\n")
        with self.assertRaisesRegex(ValueError,"different source"):
            engine.ingest(self.db,self.base,self.update,job_id=self.id)
    def test_completed_job_cannot_be_reprocessed(self):
        job=engine.ingest(self.db,self.base,self.update,job_id=self.id)["job_id"]
        change=engine.review(self.db,job)["changes"][0]
        engine.decide(self.db,change["id"],"approved","operator","verified")
        engine.export(self.db,job,self.db.parent/"approved.csv")
        with self.assertRaisesRegex(ValueError,"not reviewable"):
            engine.ingest(self.db,self.base,self.update,job_id=self.id)
if __name__=="__main__":unittest.main()
