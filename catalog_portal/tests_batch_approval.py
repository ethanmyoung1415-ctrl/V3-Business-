"""Portal batch review never authorizes pricing or nontrivial stock changes."""
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import Store,Membership,CatalogJob
from . import services

class BatchApprovalPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.operator=User.objects.create_user("batch-op",password="Strong-Test-Password123")
        cls.customer=User.objects.create_user("batch-customer",password="Strong-Test-Password456")
        cls.store=Store.objects.create(name="Batch Demo")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        ctx=override_settings(MEDIA_ROOT=root/"uploads",V3_WORKSPACE_ROOT=root/"work")
        ctx.enable();self.addCleanup(ctx.disable)
        self.client.force_login(self.customer)
        response=self.client.post(reverse("submit",args=[self.store.pk]),{
            "baseline":SimpleUploadedFile("base.csv",
                b"sku,title,price,stock\nA,One,10,100\nB,Two,10,100\n"),
            "supplier_update":SimpleUploadedFile("update.csv",
                b"sku,price,stock\nA,10,102\nB,20,0\n"),
        })
        self.assertEqual(response.status_code,302)
        self.job=CatalogJob.objects.get()
        services.process_received(self.job.pk)
        self.job.refresh_from_db()
    def test_customer_cannot_batch_approve(self):
        resp=self.client.post(reverse("batch_approve",args=[self.job.pk]),
                              {"reason":"Verified supplier"})
        self.assertEqual(resp.status_code,404)
        self.assertFalse(any(x["status"]=="approved" for x in
                             services.review(self.job,self.operator)["changes"]))
    def test_operator_batch_only_low_risk(self):
        self.client.force_login(self.operator)
        resp=self.client.post(reverse("batch_approve",args=[self.job.pk]),
                              {"reason":"Confirmed supplier inventory"})
        self.assertEqual(resp.status_code,302)
        changes=services.review(self.job,self.operator)["changes"]
        approved={(x["sku"],x["field"]) for x in changes if x["status"]=="approved"}
        self.assertEqual(approved,{("A","stock")})
        remaining={(x["sku"],x["field"]) for x in changes if x["status"]=="pending"}
        self.assertIn(("B","price"),remaining)
        self.assertIn(("B","stock"),remaining)
        self.assertEqual(self.job.portal_events.filter(
            kind="approved",detail="explicit_small_stock_batch:1").count(),1)
    def test_missing_reason_rejected(self):
        self.client.force_login(self.operator)
        resp=self.client.post(reverse("batch_approve",args=[self.job.pk]),{"reason":"ok"})
        self.assertEqual(resp.status_code,404)
