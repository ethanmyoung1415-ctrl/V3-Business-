import tempfile,unittest
from pathlib import Path
import identity,workspaces,secure_operations as ops
class SecureOperationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.accounts=self.root/"accounts.db"
        self.customers=self.root/"customers"
        self.a=workspaces.create_customer(self.customers,"One")["customer_id"]
        self.b=workspaces.create_customer(self.customers,"Two")["customer_id"]
        identity.create_user(self.accounts,"storeone","Long-Local-Test-Pass-123","customer",self.a)
        identity.create_user(self.accounts,"operator","Long-Local-Test-Pass-456","operator")
        self.customer_token=identity.login(self.accounts,"storeone","Long-Local-Test-Pass-123")
        self.operator_token=identity.login(self.accounts,"operator","Long-Local-Test-Pass-456")
        self.baseline=self.root/"baseline.csv"
        self.update=self.root/"update.csv"
        self.baseline.write_text("sku,title,price,stock\nA,Item,10,7\n")
        self.update.write_text("sku,stock\nA,0\n")
    def test_customer_cannot_submit_to_other_account(self):
        with self.assertRaises(PermissionError):
            ops.submit(self.accounts,self.customer_token,self.customers,self.b,
                       self.baseline,self.update)
    def test_customer_can_submit_but_cannot_approve(self):
        ops.submit(self.accounts,self.customer_token,self.customers,self.a,
                   self.baseline,self.update)
        job=workspaces.work_once(self.customers,self.a)["job_id"]
        change=ops.read_job(self.accounts,self.customer_token,self.customers,self.a,job)["changes"][0]
        with self.assertRaises(PermissionError):
            ops.decide(self.accounts,self.customer_token,self.customers,self.a,
                       job,change["id"],"approved","not authorized")
        ops.decide(self.accounts,self.operator_token,self.customers,self.a,
                   job,change["id"],"approved","operator verified")
    def test_cross_tenant_read_blocked(self):
        ops.submit(self.accounts,self.operator_token,self.customers,self.b,
                   self.baseline,self.update)
        job=workspaces.work_once(self.customers,self.b)["job_id"]
        with self.assertRaises(PermissionError):
            ops.read_job(self.accounts,self.customer_token,self.customers,self.b,job)
    def test_invalid_session_denied(self):
        with self.assertRaises(ValueError):
            ops.read_status(self.accounts,"not-valid",self.customers,self.a)
if __name__=="__main__":unittest.main()
