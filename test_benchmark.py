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
if __name__=="__main__":unittest.main()
