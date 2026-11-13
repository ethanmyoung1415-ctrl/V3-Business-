"""Exercise local incident stop without losing existing work."""
import tempfile
from io import StringIO
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import CatalogJob,Membership,Store
from . import emergency,services

class EmergencyStopTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=get_user_model().objects.create_user(
            "incident-user",password="Long-Test-Password123")
        cls.store=Store.objects.create(name="Incident Demo Store")
        Membership.objects.create(user=cls.user,store=cls.store,role="customer")
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        ctx=override_settings(
            V3_PAUSE_FILE=root/".v3_paused",
            MEDIA_ROOT=root/"uploads",V3_WORKSPACE_ROOT=root/"work",
            LOCAL_DEV=True)
        ctx.enable();self.addCleanup(ctx.disable)
        self.client.force_login(self.user)
    def upload(self):
        return self.client.post(reverse("submit",args=[self.store.pk]),{
            "baseline":SimpleUploadedFile("b.csv",
                b"sku,title,price,stock\nA,Item,10,5\n"),
            "supplier_update":SimpleUploadedFile("u.csv",
                b"sku,stock\nA,0\n"),
        })
    def test_stop_blocks_uploads_and_worker(self):
        self.assertEqual(self.upload().status_code,302)
        job=CatalogJob.objects.get()
        call_command("emergency_stop","--enable",stdout=StringIO())
        self.assertTrue(emergency.is_paused())
        self.assertEqual(self.upload().status_code,503)
        self.assertEqual(CatalogJob.objects.count(),1)
        self.assertEqual(services.process_received_batch(),[])
        with self.assertRaises(RuntimeError):
            services.process_received(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status,"received")
    def test_gets_stay_visible_but_delivery_paused(self):
        call_command("emergency_stop","--enable",stdout=StringIO())
        self.assertEqual(self.client.get(reverse("dashboard")).status_code,200)
        from uuid import uuid4
        self.assertEqual(self.client.get(reverse("download",args=[uuid4()])).status_code,503)
        self.assertEqual(self.client.get(reverse("download_report",args=[uuid4()])).status_code,503)
    def test_resume_preserves_valid_queued_jobs(self):
        self.upload()
        job=CatalogJob.objects.get()
        call_command("emergency_stop","--enable",stdout=StringIO())
        call_command("emergency_stop","--disable",stdout=StringIO())
        self.assertFalse(emergency.is_paused())
        outcome=services.process_received(job.pk)
        self.assertTrue(outcome["processed"])
        job.refresh_from_db()
        self.assertEqual(job.status,"review")
