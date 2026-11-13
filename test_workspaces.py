import tempfile,unittest
from pathlib import Path
import workspace
class CustomerWorkspaceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.root=root/"mock_customers"
        self.a=workspace.create_customer(self.root,"Shop A")["customer_id"]
        self.b=workspace.create_customer(self.root,"Shop B")["customer_id"]
        self.base=root/"base.csv";self.up=root/"up.csv"
        self.base.write_text("sku,title,price,stock\nA,Item,10,3\n")
        self.up.write_text("sku,stock\nA,0\n")
    def test_mock_customers_have_distinct_database(self):
        self.assertNotEqual(workspace.customer_db(self.root,self.a),
                            workspace.customer_db(self.root,self.b))
    def test_customer_cannot_read_other_customer_job(self):
        workspace.enqueue(self.root,self.a,self.base,self.up)
        job=workspace.work_once(self.root,self.a)["job_id"]
        with self.assertRaises(ValueError):workspace.review(self.root,self.b,job)
    def test_cannot_approve_others_change(self):
        workspace.enqueue(self.root,self.a,self.base,self.up)
        job=workspace.work_once(self.root,self.a)["job_id"]
        change=workspace.review(self.root,self.a,job)["changes"][0]["id"]
        with self.assertRaises(ValueError):
            workspace.decide(self.root,self.b,job,change,"approved","actor","reason")
    def test_invalid_customer_id(self):
        with self.assertRaises(ValueError):workspace.customer_db(self.root,"../../data")
if __name__=="__main__":unittest.main()
