import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import CatalogJob,Membership,Store
from . import services
import engine

class TenantPortalWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.customer=User.objects.create_user("storeuser",password="LongLocalTestPassword123")
        cls.operator=User.objects.create_user("storeoperator",password="LongLocalTestPassword456")
        cls.other=User.objects.create_user("otheruser",password="LongLocalTestPassword789")
        cls.store=Store.objects.create(name="Synthetic Store")
        cls.other_store=Store.objects.create(name="Separate Synthetic Store")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
        Membership.objects.create(user=cls.other,store=cls.other_store,role="customer")
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        conf=override_settings(MEDIA_ROOT=root/"uploads",V3_WORKSPACE_ROOT=root/"workers")
        conf.enable();self.addCleanup(conf.disable)
    def submit(self):
        self.client.force_login(self.customer)
        response=self.client.post(reverse("submit",args=[self.store.id]),{
            "baseline":SimpleUploadedFile("baseline.csv",b"sku,title,price,stock\nA,Sample,10,5\n"),
            "supplier_update":SimpleUploadedFile("update.csv",b"sku,stock\nA,0\n"),
        })
        self.assertEqual(response.status_code,302)
        return CatalogJob.objects.get()
    def test_job_lifecycle_and_verified_download(self):
        job=self.submit()
        result=services.process_received(job.pk)
        self.assertTrue(result["processed"])
        job.refresh_from_db()
        self.assertEqual(job.status,"review")
        self.client.force_login(self.customer)
        blocked=self.client.post(reverse("export_job",args=[job.id]))
        self.assertEqual(blocked.status_code,404)
        self.client.force_login(self.operator)
        details=services.review(job,self.operator)
        self.assertEqual(len(details["changes"]),1)
        change=details["changes"][0]
        premature=self.client.post(reverse("export_job",args=[job.id]))
        self.assertEqual(premature.status_code,404)
        decision=self.client.post(reverse("decision",args=[job.id]),{
            "change_id":change["id"],"decision":"approved","reason":"verified sample"})
        self.assertEqual(decision.status_code,302)
        delivered=self.client.post(reverse("export_job",args=[job.id]))
        self.assertEqual(delivered.status_code,302)
        job.refresh_from_db()
        self.assertEqual(job.status,"ready")
        self.client.force_login(self.customer)
        file_response=self.client.get(reverse("download",args=[job.id]))
        self.assertEqual(file_response.status_code,200)
        content=b"".join(file_response.streaming_content).decode("utf-8")
        self.assertIn("A,Sample,10,0",content)
    def test_customer_and_other_store_cannot_approve_or_download(self):
        job=self.submit()
        services.process_received(job.pk)
        job.refresh_from_db()
        change=services.review(job,self.operator)["changes"][0]
        self.client.force_login(self.customer)
        response=self.client.post(reverse("decision",args=[job.id]),{
            "change_id":change["id"],"decision":"approved","reason":"not allowed"})
        self.assertEqual(response.status_code,404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("job_detail",args=[job.id])).status_code,404)
        self.assertEqual(self.client.get(reverse("download",args=[job.id])).status_code,404)
    def test_tampered_export_cannot_be_downloaded(self):
        job=self.submit()
        services.process_received(job.pk)
        job.refresh_from_db()
        change=services.review(job,self.operator)["changes"][0]
        services.decide(job,self.operator,change["id"],"approved","valid test")
        services.prepare_export(job,self.operator)
        path=services.output_path(job)
        path.write_text("sku,title,price,stock\nA,Sample,10,999\n")
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("download",args=[job.id])).status_code,404)
if __name__=="__main__":
    import unittest;unittest.main()
