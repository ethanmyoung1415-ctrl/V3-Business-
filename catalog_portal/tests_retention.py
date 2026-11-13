"""Dry-run and explicit synthetic-upload deletion checks."""
import tempfile
from datetime import timedelta
from pathlib import Path
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command,CommandError
from django.test import TestCase,override_settings
from django.utils import timezone
from catalog_portal.models import CatalogJob,Store,CatalogEvent

class LocalRetentionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=get_user_model().objects.create_user("retention-user",password="Long-Dev-Password123")
        cls.store=Store.objects.create(name="Synthetic retention shop")
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ctx=override_settings(MEDIA_ROOT=Path(tmp.name),LOCAL_DEV=True)
        ctx.enable()
        self.addCleanup(ctx.disable)
    def make_job(self,status):
        job=CatalogJob(store=self.store,submitted_by=self.user,status=status)
        job.baseline.save("baseline.csv",ContentFile(b"sku,title,price,stock\nA,Test,10,2\n"),save=False)
        job.supplier_update.save("update.csv",ContentFile(b"sku,stock\nA,0\n"),save=False)
        job.save()
        CatalogJob.objects.filter(pk=job.pk).update(updated_at=timezone.now()-timedelta(days=60))
        job.refresh_from_db()
        return job
    def test_dry_run_does_not_delete(self):
        job=self.make_job("ready")
        output=StringIO()
        call_command("purge_demo_uploads","--days","30",stdout=output)
        self.assertIn("Eligible demo source files: 2",output.getvalue())
        self.assertTrue(Path(job.baseline.path).exists())
        self.assertFalse(job.portal_events.filter(kind="source_purged").exists())
    def test_confirm_deletes_only_old_terminal_sources(self):
        old=self.make_job("ready")
        live=self.make_job("review")
        call_command("purge_demo_uploads","--days","30","--confirm",stdout=StringIO())
        self.assertFalse(Path(old.baseline.path).exists())
        self.assertFalse(Path(old.supplier_update.path).exists())
        self.assertTrue(Path(live.baseline.path).exists())
        self.assertEqual(CatalogEvent.objects.filter(job=old,kind="source_purged").count(),2)
    @override_settings(LOCAL_DEV=False)
    def test_non_local_delete_denied(self):
        with self.assertRaises(CommandError):
            call_command("purge_demo_uploads","--confirm",stdout=StringIO())
    def test_delete_today_rejected(self):
        with self.assertRaises(CommandError):
            call_command("purge_demo_uploads","--days","0","--confirm",stdout=StringIO())
