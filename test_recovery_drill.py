import unittest
import recovery_drill

class RepeatableRecoveryDrillTests(unittest.TestCase):
    def test_all_fictional_data_recovered(self):
        result=recovery_drill.run()
        self.assertTrue(result["passed"],result)
        self.assertTrue(result["portal_db_restored"])
        self.assertTrue(result["engine_db_restored"])
        self.assertTrue(result["supplier_and_export_bytes_preserved"])
        self.assertEqual(result["files_verified"],4)
    def test_recovery_drill_does_not_grant_production_permission(self):
        result=recovery_drill.run()
        self.assertFalse(result["production_backups_approved"])
        self.assertTrue(result["unencrypted_backup"])
        self.assertEqual(result["source"],"synthetic_data_only")
if __name__=="__main__":unittest.main()
