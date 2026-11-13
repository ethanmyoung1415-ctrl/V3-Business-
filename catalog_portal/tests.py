import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings,Client
from django.urls import reverse
from .models import Store,Membership,CatalogJob

class PortalSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_a=get_user_model().objects.create_user(username="store-a",password="LongLocalTestPassword123")
        cls.user_b=get_user_model().objects.create_user(username="store-b",password="LongLocalTestPassword456")
        cls.store_a=Store.objects.create(name="Example A")
        cls.store_b=Store.objects.create(name="Example B")
        Membership.objects.create(user=cls.user_a,store=cls.store_a,role="customer")
        Membership.objects.create(user=cls.user_b,store=cls.store_b,role="customer")
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.override=override_settings(MEDIA_ROOT=self.temp.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
    def upload(self,store,baseline=None,update=None):
        baseline=baseline or b"sku,title,price,stock\nA,Sample,10,5\n"
        update=update or b"sku,stock\nA,0\n"
        return self.client.post(reverse("submit",args=[store.id]),{
            "baseline":SimpleUploadedFile("baseline.csv",baseline,content_type="text/csv"),
            "supplier_update":SimpleUploadedFile("update.csv",update,content_type="text/csv"),
        })
    def test_login_is_required(self):
        result=self.client.get(reverse("dashboard"))
        self.assertEqual(result.status_code,302)
        self.assertIn("/login/",result["Location"])
    def test_customer_sees_only_their_store(self):
        self.client.force_login(self.user_a)
        response=self.client.get(reverse("dashboard"))
        self.assertContains(response,"Example A")
        self.assertNotContains(response,"Example B")
    def test_customer_cannot_submit_to_other_store(self):
        self.client.force_login(self.user_a)
        response=self.upload(self.store_b)
        self.assertEqual(response.status_code,404)
        self.assertEqual(CatalogJob.objects.count(),0)
    def test_customer_cannot_read_other_store_job(self):
        self.client.force_login(self.user_b)
        self.upload(self.store_b)
        job=CatalogJob.objects.get()
        self.client.force_login(self.user_a)
        response=self.client.get(reverse("job_detail",args=[job.id]))
        self.assertEqual(response.status_code,404)
    def test_valid_upload_stored_with_private_name(self):
        self.client.force_login(self.user_a)
        response=self.upload(self.store_a)
        self.assertEqual(response.status_code,302)
        job=CatalogJob.objects.get()
        self.assertEqual(job.status,"received")
        self.assertIn(str(self.store_a.id),job.baseline.name)
        self.assertIn(str(self.store_a.id),job.supplier_update.name)
        self.assertTrue(Path(job.baseline.path).is_file())
    def test_invalid_csv_is_rejected(self):
        self.client.force_login(self.user_a)
        response=self.upload(self.store_a,baseline=b"sku,stock\nA,0\n")
        self.assertEqual(response.status_code,200)
        self.assertContains(response,"baseline requires")
        self.assertFalse(CatalogJob.objects.exists())
    def test_csrf_required_for_upload(self):
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.user_a)
        response=client.post(reverse("submit",args=[self.store_a.id]),{})
        self.assertEqual(response.status_code,403)
if __name__=="__main__":
    import unittest;unittest.main()
