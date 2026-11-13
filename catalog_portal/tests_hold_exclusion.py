"""Operator-only held-source exclusion through the authenticated portal."""
import csv
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import Store,Membership,CatalogJob
from . import services
import engine

class PortalHoldExclusionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.operator=User.objects.create_user("hold-op",password="Long-Demo-Password123")
        cls.customer=User.objects.create_user("hold-customer",password="Long-Demo-Password456")
        cls.store=Store.objects.create(name="Synthetic Holds")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        ctx=override_settings(MEDIA_ROOT=self.root/"uploads",
                              V3_WORKSPACE_ROOT=self.root/"workspaces")
        ctx.enable();self.addCleanup(ctx.disable)
        self.client.force_login(self.customer)
        response=self.client.post(reverse("submit",args=[self.store.id]),{
            "baseline":SimpleUploadedFile("base.csv",
                b"sku,title,price,stock\nA,Original,10,9\nB,Other,5,8\n"),
            "supplier_update":SimpleUploadedFile("update.csv",
                b"sku,stock\nA,0\nB,\n"),
        })
        self.assertEqual(response.status_code,302)
        self.job=CatalogJob.objects.get()
        services.process_received(self.job.pk)
        self.job.refresh_from_db()
        self.token=engine.listed_holds(
            services.backend_db(self.store.id),str(self.job.engine_job_id))[0]["token"]
    def test_customer_cannot_exclude_hold(self):
        response=self.client.post(reverse("exclude_hold",args=[self.job.pk]),{
            "token":self.token,"reason":"This data is not authorized"})
        self.assertEqual(response.status_code,404)
        self.assertEqual(len(services.review(self.job,self.operator)["holds"]),1)
    def test_excluded_row_remains_original_after_approved_export(self):
        self.client.force_login(self.operator)
        response=self.client.post(reverse("exclude_hold",args=[self.job.pk]),{
            "token":self.token,"reason":"Supplier value missing; retain original"})
        self.assertEqual(response.status_code,302)
        self.assertFalse(services.review(self.job,self.operator)["holds"])
        change=services.review(self.job,self.operator)["changes"][0]
        services.decide(self.job,self.operator,change["id"],"approved",
                        "Source verified for zero stock")
        services.prepare_export(self.job,self.operator)
        with services.output_path(self.job).open(newline="") as f:
            rows={row["sku"]:row for row in csv.DictReader(f)}
        self.assertEqual(rows["A"]["stock"],"0")
        self.assertEqual(rows["B"]["stock"],"8")
        self.assertEqual(self.job.portal_events.filter(kind="hold_excluded").count(),1)
    def test_invalid_hold_token_fails_closed(self):
        self.client.force_login(self.operator)
        resp=self.client.post(reverse("exclude_hold",args=[self.job.pk]),{
            "token":"a"*64,"reason":"This is an incorrect token"})
        self.assertEqual(resp.status_code,404)
        self.assertEqual(len(services.review(self.job,self.operator)["holds"]),1)
