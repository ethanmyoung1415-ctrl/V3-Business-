"""Uploaded source bytes must match the hashes recorded at submission."""
import hashlib,tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import CatalogJob,Membership,Store,CatalogEvent
from . import services

class SubmittedFingerprintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=get_user_model().objects.create_user(
            "hash-customer",password="Long-Local-Test-Password123")
        cls.store=Store.objects.create(name="Synthetic Hash Shop")
        Membership.objects.create(user=cls.user,store=cls.store,role="customer")
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        config=override_settings(MEDIA_ROOT=root/"uploads",V3_WORKSPACE_ROOT=root/"work")
        config.enable();self.addCleanup(config.disable)
        self.client.force_login(self.user)
        self.baseline=b"sku,title,price,stock\nA,Item,10,5\n"
        self.supplier=b"sku,stock\nA,0\n"
        response=self.client.post(reverse("submit",args=[self.store.pk]),{
            "baseline":SimpleUploadedFile("base.csv",self.baseline),
            "supplier_update":SimpleUploadedFile("update.csv",self.supplier),
        })
        self.assertEqual(response.status_code,302)
        self.job=CatalogJob.objects.get()
    def test_original_hashes_are_persisted(self):
        self.assertEqual(self.job.baseline_sha256,hashlib.sha256(self.baseline).hexdigest())
        self.assertEqual(self.job.supplier_sha256,hashlib.sha256(self.supplier).hexdigest())
        outcome=services.process_received(self.job.pk)
        self.assertTrue(outcome["processed"])
    def test_changed_supplier_file_fails_before_processing(self):
        Path(self.job.supplier_update.path).write_text("sku,stock\nA,99\n")
        with self.assertRaisesRegex(ValueError,"changed since submission"):
            services.process_received(self.job.pk)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status,"failed")
        self.assertIsNone(self.job.engine_job_id)
        self.assertTrue(CatalogEvent.objects.filter(job=self.job,kind="failed").exists())
    def test_missing_hash_fails_closed(self):
        CatalogJob.objects.filter(pk=self.job.pk).update(supplier_sha256="")
        with self.assertRaisesRegex(ValueError,"lacks required hashes"):
            services.process_received(self.job.pk)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status,"failed")
