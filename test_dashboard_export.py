import tempfile,unittest
from pathlib import Path
import engine,operator_dashboard as ui
class BrowserExportTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.db=self.root/"db.sqlite3"
        baseline=self.root/"b.csv";update=self.root/"u.csv"
        baseline.write_text("sku,title,price,stock\nA,Item,10,4\n",encoding="utf-8")
        update.write_text("sku,stock\nA,0\n",encoding="utf-8")
        self.job=engine.ingest(self.db,baseline,update)["job_id"]
        self.change=engine.review(self.db,self.job)["changes"][0]
    def test_export_is_hidden_until_decided(self):
        html=ui.job_page(self.db,self.job,"csrf")
        self.assertNotIn("Prepare independently verified CSV",html)
        engine.decide(self.db,self.change["id"],"approved","operator","verified")
        html=ui.job_page(self.db,self.job,"csrf")
        self.assertIn("Prepare independently verified CSV",html)
        engine.export(self.db,self.job,ui.output_path(self.db,self.job))
        html=ui.job_page(self.db,self.job,"csrf")
        self.assertIn("Download independently verified CSV",html)
    def test_output_path_rejects_traversal(self):
        with self.assertRaises(ValueError):
            ui.output_path(self.db,"../../secret")
if __name__=="__main__":unittest.main()
