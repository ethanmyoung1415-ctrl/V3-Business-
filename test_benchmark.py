import tempfile,unittest
from pathlib import Path
from benchmark import run
class SyntheticBenchmarkTests(unittest.TestCase):
    def test_known_anomalies_are_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run(folder,100)
            self.assertTrue(result["passed"],result)
            self.assertEqual(result["holds"],3)
            self.assertEqual(result["pending_decisions"],2)
    def test_large_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(run(folder,1000)["passed"])
    def test_target_size_catalog(self):
        # Typical target prospect size for V3: approximately 5,000 SKUs.
        with tempfile.TemporaryDirectory() as folder:
            result=run(folder,5000)
            self.assertTrue(result["passed"])
            self.assertEqual(result["count"],5000)
            self.assertEqual(result["holds"],3)
            self.assertEqual(result["pending_decisions"],2)
if __name__=="__main__":unittest.main()
