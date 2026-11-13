"""Operator-controlled retry must reuse stable engine work, not duplicate it."""
import sqlite3,tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import Store,Membership,CatalogJob,CatalogEvent
from . import services
import engine

class PortalRetryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.operator=User.objects.create_user("retry-operator",password="Long-Test-Passphrase123")
        cls.customer=User.objects.create_user("retry-customer",password="Long-Test-Passphrase456")
        cls.store=Store.objects.create(name="Retry Demo")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        settings=override_settings(MEDIA_ROOT=root/"uploads",V3_WORKSPACE_ROOT=root/"work")
        settings.enable();self.addCleanup(settings.disable)
        self.client.force_login(self.customer)
        response=self.client.post(reverse("submit",args=[self.store.pk]),{
            "baseline":SimpleUploadedFile("base.csv",
                b"sku,title,price,stock\nA,Item,10,5\n"),
            "supplier_update":SimpleUploadedFile("update.csv",
                b"sku,stock\nA,0\n"),
        })
        self.assertEqual(response.status_code,302)
        self.job=CatalogJob.objects.get()
    def fail_job(self,code):
        CatalogJob.objects.filter(pk=self.job.pk).update(
            status=CatalogJob.STATUS_FAILED,error_code=code)
        self.job.refresh_from_db()
    def test_operator_retry_reuses_orphaned_engine_job(self):
        database=services.backend_db(self.store.pk)
        engine.ingest(database,self.job.baseline.path,self.job.supplier_update.path,
                      job_id=str(self.job.pk))
        self.fail_job("processing_error")
        self.client.force_login(self.customer)
        self.assertEqual(self.client.post(reverse("retry_failed",args=[self.job.pk]),{
            "reason":"Worker crashed after ingest finished"}).status_code,404)
        self.client.force_login(self.operator)
        self.assertEqual(self.client.post(reverse("retry_failed",args=[self.job.pk]),{
            "reason":"Worker crashed after ingest finished"}).status_code,302)
        outcome=services.process_received(self.job.pk)
        self.assertTrue(outcome["processed"])
        self.assertEqual(outcome["engine_job_id"],str(self.job.pk))
        with sqlite3.connect(database) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0],1)
        self.assertEqual(self.job.portal_events.filter(kind="retry_requested").count(),1)
    def test_tampered_original_cannot_be_retried(self):
        self.fail_job("storage_failure")
        Path(self.job.supplier_update.path).write_text("sku,stock\nA,88\n")
        self.client.force_login(self.operator)
        response=self.client.post(reverse("retry_failed",args=[self.job.pk]),{
            "reason":"Storage problem was investigated"})
        self.assertEqual(response.status_code,404)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status,"failed")
    def test_invalid_supplier_requires_new_submission(self):
        self.fail_job("invalid_input")
        self.client.force_login(self.operator)
        response=self.client.post(reverse("retry_failed",args=[self.job.pk]),{
            "reason":"Attempted unauthorized invalid input retry"})
        self.assertEqual(response.status_code,404)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status,"failed")
    def test_reason_is_required(self):
        self.fail_job("processing_error")
        self.client.force_login(self.operator)
        response=self.client.post(reverse("retry_failed",args=[self.job.pk]),{
            "reason":"short"})
        self.assertEqual(response.status_code,404)
