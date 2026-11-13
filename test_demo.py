import tempfile,unittest
from demo import simulate
class SyntheticDemoTests(unittest.TestCase):
    def test_end_to_end_two_mock_customers(self):
        with tempfile.TemporaryDirectory() as folder:
            result=simulate(folder)
        self.assertTrue(result["passed"])
        self.assertTrue(result["cross_customer_read_blocked"])
        self.assertTrue(all(x["qa_passed"] for x in result["customer_results"]))
        self.assertEqual({x["updated_stock"] for x in result["customer_results"]},{"0","5"})
if __name__=="__main__":unittest.main()
