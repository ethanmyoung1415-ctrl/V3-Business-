"""A recurring supplier cycle starts only from a customer-confirmed verified catalog."""
import csv,tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import CatalogJob,CatalogConfirmation,Membership,Store
from . import services

class ConfirmedCatalogCycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.customer=User.objects.create_user("cycle-customer",password="Long-Cycle-Password123")
        cls.operator=User.objects.create_user("cycle-operator",password="Long-Cycle-Password456")
        cls.outsider=User.objects.create_user("cycle-other",password="Long-Cycle-Password789")
        cls.store=Store.objects.create(name="Recurring Catalog Demo")
        cls.other_store=Store.objects.create(name="Unrelated Catalog Demo")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
        Membership.objects.create(user=cls.outsider,store=cls.other_store,role="customer")
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        ctx=override_settings(MEDIA_ROOT=root/"uploads",V3_WORKSPACE_ROOT=root/"worker")
        ctx.enable();self.addCleanup(ctx.disable)
        self.client.force_login(self.customer)
    def submit_first(self):
        response=self.client.post(reverse("submit",args=[self.store.pk]),{
            "baseline":SimpleUploadedFile("baseline.csv",
                b"sku,title,price,stock\nA,Sample,10,8\n"),
            "supplier_update":SimpleUploadedFile("supplier.csv",
                b"sku,stock\nA,0\n"),
        })
        self.assertEqual(response.status_code,302)
        job=CatalogJob.objects.order_by("created_at").first()
        services.process_received(job.pk)
        job.refresh_from_db()
        change=services.review(job,self.operator)["changes"][0]
        services.decide(job,self.operator,change["id"],"approved","Authoritative supplier check")
        services.prepare_export(job,self.operator)
        return job
    def submit_next(self):
        return self.client.post(reverse("submit",args=[self.store.pk]),{
            "use_confirmed_baseline":"on",
            "supplier_update":SimpleUploadedFile("next.csv",
                b"sku,stock\nA,3\n"),
        })
    def test_customer_confirms_then_reuses_exact_verified_version(self):
        original=self.submit_first()
        response=self.client.post(reverse("confirm_import",args=[original.pk]),{
            "import_confirmed":"yes"})
        self.assertEqual(response.status_code,302)
        confirmed=CatalogConfirmation.objects.get(job=original)
        self.assertEqual(confirmed.confirmed_by,self.customer)
        response=self.submit_next()
        self.assertEqual(response.status_code,302)
        subsequent=CatalogJob.objects.exclude(pk=original.pk).get()
        self.assertEqual(subsequent.baseline_source_job_id,original.pk)
        with open(subsequent.baseline.path,newline="",encoding="utf-8") as f:
            source=list(csv.DictReader(f))[0]
        self.assertEqual(source["stock"],"0")
        self.assertEqual(subsequent.baseline_sha256,original.export_sha256)
        processed=services.process_received(subsequent.pk)
        self.assertTrue(processed["processed"])
        subsequent.refresh_from_db()
        proposed=services.review(subsequent,self.operator)["changes"][0]
        self.assertEqual((proposed["old"],proposed["new"]),("0","3"))
    def test_reuse_is_not_available_without_customer_confirmation(self):
        self.submit_first()
        response=self.submit_next()
        self.assertEqual(response.status_code,200)
        self.assertEqual(CatalogJob.objects.count(),1)
    def test_operator_cannot_claim_the_customer_imported(self):
        original=self.submit_first()
        self.client.force_login(self.operator)
        resp=self.client.post(reverse("confirm_import",args=[original.pk]),{
            "import_confirmed":"yes"})
        self.assertEqual(resp.status_code,404)
        self.assertFalse(CatalogConfirmation.objects.exists())
    def test_out_of_order_manual_baseline_confirmation_is_denied(self):
        first=self.submit_first()
        self.client.force_login(self.customer)
        second_response=self.client.post(reverse("submit",args=[self.store.pk]),{
            "baseline":SimpleUploadedFile("another.csv",
                b"sku,title,price,stock\nA,Sample,10,8\n"),
            "supplier_update":SimpleUploadedFile("second.csv",
                b"sku,stock\nA,3\n"),
        })
        self.assertEqual(second_response.status_code,302)
        second=CatalogJob.objects.exclude(pk=first.pk).get()
        services.process_received(second.pk)
        second.refresh_from_db()
        change=services.review(second,self.operator)["changes"][0]
        services.decide(second,self.operator,change["id"],"approved","Verifiable supplier source")
        services.prepare_export(second,self.operator)
        self.client.post(reverse("confirm_import",args=[first.pk]),{"import_confirmed":"yes"})
        bad=self.client.post(reverse("confirm_import",args=[second.pk]),{"import_confirmed":"yes"})
        self.assertEqual(bad.status_code,404)
    def test_other_store_cannot_confirm(self):
        first=self.submit_first()
        self.client.force_login(self.outsider)
        resp=self.client.post(reverse("confirm_import",args=[first.pk]),{
            "import_confirmed":"yes"})
        self.assertEqual(resp.status_code,404)
    def test_tampered_verified_file_cannot_be_confirmed(self):
        first=self.submit_first()
        services.output_path(first).write_text("sku,title,price,stock\nA,Sample,10,99\n")
        resp=self.client.post(reverse("confirm_import",args=[first.pk]),{
            "import_confirmed":"yes"})
        self.assertEqual(resp.status_code,404)
        self.assertFalse(CatalogConfirmation.objects.exists())
