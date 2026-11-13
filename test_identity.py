import tempfile,unittest,uuid
from pathlib import Path
import identity
class IdentityTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.db=Path(t.name)/"identity.sqlite3"
        self.customer_a=str(uuid.uuid4());self.customer_b=str(uuid.uuid4())
        identity.create_user(self.db,"owner","Long-Test-Passphrase-123",
                             "operator")
        identity.create_user(self.db,"customer_a","Another-Long-Passphrase-456",
                             "customer",self.customer_a)
    def test_login_logout(self):
        token=identity.login(self.db,"owner","Long-Test-Passphrase-123")
        self.assertEqual(identity.authenticate(self.db,token)["role"],"operator")
        identity.logout(self.db,token)
        with self.assertRaises(ValueError):identity.authenticate(self.db,token)
    def test_wrong_password(self):
        with self.assertRaisesRegex(ValueError,"invalid credentials"):
            identity.login(self.db,"owner","wrong password here")
    def test_customer_isolation(self):
        token=identity.login(self.db,"customer_a","Another-Long-Passphrase-456")
        user=identity.authenticate(self.db,token)
        self.assertTrue(identity.authorize(user,self.customer_a,"submit_update"))
        with self.assertRaises(PermissionError):
            identity.authorize(user,self.customer_b,"read_catalog")
        with self.assertRaises(PermissionError):
            identity.authorize(user,self.customer_a,"approve_change")
    def test_unknown_operation_denied_even_for_operator(self):
        user=identity.authenticate(self.db,identity.login(self.db,"owner","Long-Test-Passphrase-123"))
        with self.assertRaises(PermissionError):identity.authorize(user,self.customer_a,"delete_all")
    def test_weak_password_rejected(self):
        with self.assertRaises(ValueError):
            identity.create_user(self.db,"weak","123","operator")
if __name__=="__main__":unittest.main()
