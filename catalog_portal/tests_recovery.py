import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from catalog_portal.models import CatalogJob,Store,CatalogEvent

class StaleWorkerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=get_user_model().objects.create_user("stale-operator",password="Strong-Test-Password123")
        cls.store=Store.objects.create(name="Stalled Demo")
    def job(self,status,age_minutes):
        job=CatalogJob.objects.create(store=self.store,submitted_by=self.user,
            status=status,baseline="synthetic/a.csv",supplier_update="synthetic/b.csv")
        CatalogJob.objects.filter(pk=job.pk).update(
            updated_at=timezone.now()-timedelta(minutes=age_minutes))
        job.refresh_from_db()
        return job
    def test_dry_run_changes_nothing(self):
        old=self.job("processing",120)
        call_command("reconcile_stale_jobs","--minutes","30","--dry-run",stdout=StringIO())
        old.refresh_from_db()
        self.assertEqual(old.status,"processing")
        self.assertFalse(CatalogEvent.objects.filter(job=old).exists())
    def test_stale_fails_closed_and_is_audited(self):
        stale=self.job("processing",120)
        recent=self.job("processing",3)
        done=self.job("ready",120)
        call_command("reconcile_stale_jobs","--minutes","30",stdout=StringIO())
        stale.refresh_from_db();recent.refresh_from_db();done.refresh_from_db()
        self.assertEqual(stale.status,"failed")
        self.assertEqual(stale.error_code,"worker_stalled")
        self.assertEqual(recent.status,"processing")
        self.assertEqual(done.status,"ready")
        self.assertEqual(CatalogEvent.objects.filter(job=stale,detail="worker_stalled_requires_review").count(),1)
        call_command("reconcile_stale_jobs","--minutes","30",stdout=StringIO())
        self.assertEqual(CatalogEvent.objects.filter(job=stale).count(),1)
