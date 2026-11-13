from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management import call_command,CommandError
from django.test import TestCase
from django.utils import timezone
from io import StringIO
from .models import Store,CatalogJob
from . import health

class HealthCheckTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=get_user_model().objects.create_user("health-op",password="Strong-Demo-Passphrase123")
        cls.store=Store.objects.create(name="Health Mock Store")
    def make_job(self,status,minutes=0,error=""):
        job=CatalogJob.objects.create(
            store=self.store,submitted_by=self.user,status=status,
            baseline="sample/base.csv",supplier_update="sample/update.csv",
            error_code=error)
        if minutes:
            CatalogJob.objects.filter(pk=job.pk).update(
                updated_at=timezone.now()-timedelta(minutes=minutes),
                created_at=timezone.now()-timedelta(minutes=minutes))
        return job
    def test_healthy_empty(self):
        report=health.snapshot()
        self.assertEqual(report["status"],"healthy")
        self.assertEqual(report["checks"]["active_stores"],1)
        self.assertEqual(report["checks"]["failed_jobs"],0)
    def test_stale_processing_reports_critical_without_supplier_values(self):
        self.make_job("processing",minutes=90)
        report=health.snapshot()
        self.assertEqual(report["status"],"critical")
        self.assertEqual(report["checks"]["stale_processing"],1)
        self.assertNotIn("sample/base.csv",str(report))
    def test_pending_review_reports_attention(self):
        self.make_job("review",minutes=1500)
        self.assertEqual(health.snapshot()["status"],"attention")
    def test_cli_can_fail_monitoring_if_critical(self):
        self.make_job("failed",error="storage_failure")
        with self.assertRaises(CommandError):
            call_command("v3_health","--fail-on-critical",stdout=StringIO())
    def test_ready_not_mistaken_for_remote_import(self):
        self.make_job("ready")
        report=health.snapshot()
        self.assertEqual(report["checks"]["ready_outputs"],1)
        self.assertIn("Ready status alone does not certify remote-store import",
                      report["limitations"])
