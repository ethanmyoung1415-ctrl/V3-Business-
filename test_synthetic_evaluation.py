import unittest
from synthetic_evaluation import evaluate

class SyntheticEvidenceTests(unittest.TestCase):
    def test_300_known_cases(self):
        report=evaluate(300)
        self.assertTrue(report["passed"],report)
        self.assertEqual(report["hold_false_positives"],0)
        self.assertEqual(report["hold_false_negatives"],0)
        self.assertEqual(report["change_false_positives"],0)
        self.assertEqual(report["change_false_negatives"],0)
    def test_1000_known_cases(self):
        report=evaluate(1000)
        self.assertTrue(report["passed"],report)
        self.assertGreater(report["actual_changes"],100)
        self.assertIn("artificial",report["limitation"])
    def test_invalid_data_size_rejected(self):
        with self.assertRaises(ValueError):evaluate(10)
if __name__=="__main__":unittest.main()
