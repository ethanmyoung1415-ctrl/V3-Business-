"""Portal preparation displays read-only advice but never authorizes a change."""
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import CatalogJob,Membership,Store
from . import services
import advice_jobs

class PortalAdvisoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.customer=User.objects.create_user("advice-customer",password="Strong-Test-Passphrase123")
        cls.operator=User.objects.create_user("advice-operator",password="Strong-Test-Passphrase456")
        cls.store=Store.objects.create(name="Advisory Test Store")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        settings=override_settings(MEDIA_ROOT=root/"uploads",V3_WORKSPACE_ROOT=root/"work")
        settings.enable();self.addCleanup(settings.disable)
        self.client.force_login(self.customer)
        resp=self.client.post(reverse("submit",args=[self.store.pk]),{
            "baseline":SimpleUploadedFile("baseline.csv",
                b"sku,title,price,stock\nA,Original,10,5\n"),
            "supplier_update":SimpleUploadedFile("update.csv",
                b"sku,title\nA,Renamed Item\n"),
        })
        self.assertEqual(resp.status_code,302)
        self.job=CatalogJob.objects.get()
        services.process_received(self.job.pk)
        self.job.refresh_from_db()
    def test_advice_is_persisted_but_remains_pending(self):
        report=advice_jobs.read(
            services.backend_db(self.store.pk),str(self.job.engine_job_id))
        self.assertEqual(len(report),1)
        self.assertEqual(report[0]["source"],"deterministic")
        self.assertEqual(services.review(self.job,self.operator)["changes"][0]["status"],"pending")
        self.client.force_login(self.operator)
        view=self.client.get(reverse("job_detail",args=[self.job.pk]))
        self.assertContains(view,"Review suggestion")
        self.assertContains(view,"Verification step")
    def test_customer_cannot_access_operator_review_advisory(self):
        view=self.client.get(reverse("job_detail",args=[self.job.pk]))
        self.assertNotContains(view,"Review suggestion")
