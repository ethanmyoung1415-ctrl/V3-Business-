"""Verify customers receive only their own reconciled change reports."""
import json
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import CatalogJob,Membership,Store
from . import services
import engine

class DownloadableChangeReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.operator=User.objects.create_user("report-operator",password="Long-Demo-TestPassword123")
        cls.customer=User.objects.create_user("report-customer",password="Long-Demo-TestPassword456")
        cls.foreign=User.objects.create_user("report-foreign",password="Long-Demo-TestPassword789")
        cls.store=Store.objects.create(name="Report Store")
        cls.foreign_store=Store.objects.create(name="Other Store")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
        Membership.objects.create(user=cls.foreign,store=cls.foreign_store,role="customer")
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        settings=override_settings(MEDIA_ROOT=root/"uploads",V3_WORKSPACE_ROOT=root/"worker")
        settings.enable();self.addCleanup(settings.disable)
        self.client.force_login(self.customer)
        response=self.client.post(reverse("submit",args=[self.store.pk]),{
            "baseline":SimpleUploadedFile("baseline.csv",
                b"sku,title,price,stock\nA,One,10,8\nB,Two,20,7\n"),
            "supplier_update":SimpleUploadedFile("update.csv",
                b"sku,stock\nA,0\nB,\n"),
        })
        self.assertEqual(response.status_code,302)
        self.job=CatalogJob.objects.get()
        services.process_received(self.job.pk)
        self.job.refresh_from_db()
    def test_report_requires_complete_verified_export(self):
        self.assertEqual(self.client.get(reverse("download_report",args=[self.job.pk])).status_code,404)
        hold=engine.listed_holds(services.backend_db(self.store.pk),
                                 str(self.job.engine_job_id))[0]
        services.exclude_held_record(self.job,self.operator,hold["token"],
                                     "Skip blank supplier stock, retain baseline")
        change=services.review(self.job,self.operator)["changes"][0]
        services.decide(self.job,self.operator,change["id"],"approved",
                        "Zero-stock source verified")
        services.prepare_export(self.job,self.operator)
        self.client.force_login(self.customer)
        response=self.client.get(reverse("download_report",args=[self.job.pk]))
        self.assertEqual(response.status_code,200)
        report=json.loads(response.content)
        self.assertTrue(report["verification"]["passed"])
        self.assertEqual(report["summary"]["excluded_holds"],1)
        self.assertEqual(report["summary"]["approved_changes"],1)
        self.assertEqual(report["changes"][0]["sku"],"A")
    def test_other_tenant_report_access_blocked(self):
        self.client.force_login(self.foreign)
        self.assertEqual(
            self.client.get(reverse("download_report",args=[self.job.pk])).status_code,404)
