import tempfile,unittest
from pathlib import Path
import operations,supervisor
class SupervisorTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.db=self.root/"s.db"
        b=self.root/"b.csv";u=self.root/"u.csv"
        b.write_text("sku,title,price,stock\nA,Item,10,5\nB,Second,10,3\n")
        u.write_text("sku,stock,price\nA,0,20\nB,3,10\n")
        operations.enqueue(self.db,b,u)
        operations.work_once(self.db)
    def test_priority_brief(self):
        brief=supervisor.briefing(self.db)
        self.assertEqual(brief["needs_attention"],2)
        self.assertEqual([i["severity"] for i in brief["items"]],["high","high"])
        self.assertEqual(brief["automated_approvals"],0)
    def test_limit(self):
        brief=supervisor.briefing(self.db,1)
        self.assertTrue(brief["truncated"])
        self.assertEqual(brief["returned"],1)
if __name__=="__main__":unittest.main()
