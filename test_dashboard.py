"""Smoke tests for the GitHub browser console against the repository engine."""
import tempfile,unittest
from pathlib import Path
import engine,operations,operator_dashboard as dash
class DashboardTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.db=self.root/'test.sqlite3'
        b=self.root/'baseline.csv';u=self.root/'supplier.csv'
        b.write_text('sku,title,price,stock\nA,Test,10,5\n',encoding='utf-8')
        u.write_text('sku,title,stock\nA,<script>alert(1)</script>,0\n',encoding='utf-8')
        operations.enqueue(self.db,b,u)
        result=operations.work_once(self.db)
        self.job=result['job_id']
    def test_dashboard(self):
        page=dash.overview(self.db)
        self.assertIn('Review changes',page)
        self.assertIn('Pending',page)
    def test_escapes_user_data_and_has_csrf(self):
        page=dash.job_page(self.db,self.job,'TESTTOKEN')
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',page)
        self.assertNotIn('<script>alert(1)</script>',page)
        self.assertIn('value="TESTTOKEN"',page)
        self.assertIn('name="reason"',page)
    def test_handler_creation(self):
        self.assertTrue(dash.make_handler(self.db,'TOKEN','operator'))
if __name__=='__main__':unittest.main()
