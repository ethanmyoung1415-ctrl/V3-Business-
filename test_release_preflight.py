import unittest
from pathlib import Path
import release_preflight

class DevelopmentPreflightTests(unittest.TestCase):
    def test_local_checks_pass_without_authorizing_production(self):
        report=release_preflight.run()
        self.assertTrue(report["development_checks_passed"],report)
        self.assertEqual(report["production_decision"],"NO_GO")
        self.assertFalse(report["real_customer_data_allowed"])
        self.assertFalse(report["public_deployment_allowed"])
        self.assertFalse(report["billing_allowed"])
        self.assertFalse(report["live_store_writes_allowed"])
        self.assertGreaterEqual(len(report["approval_blockers"]),4)
        self.assertNotIn("api_key",str(report).lower())
    def test_missing_release_document_is_reported(self):
        with __import__("tempfile").TemporaryDirectory() as folder:
            report=release_preflight.run(Path(folder))
        self.assertFalse(report["checks"]["required_release_docs_present"])
        self.assertFalse(report["development_checks_passed"])
        self.assertEqual(report["production_decision"],"NO_GO")
if __name__=="__main__":unittest.main()
