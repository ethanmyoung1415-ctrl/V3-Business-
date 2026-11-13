"""Portal audit and operator queue regression tests."""
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import Store,Membership,CatalogJob,CatalogEvent
from . import services

class PortalAuditingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.owner=User.objects.create_user("ops-owner",password="Very-Long-Test-Password123")
        cls.customer=User.objects.create_user("ops-customer",password="Very-Long-Test-Password456")
        cls.other=User.objects.create_user("ops-other",password="Very-Long-Test-Password789")
        cls.store=Store.objects.create(name="Test Store One")
        cls.other_store=Store.objects.create(name="Test Store Two")
        Membership.objects.create(user=cls.owner,store=cls.store,role="operator")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
        Membership.objects.create(user=cls.other,store=cls.other_store,role="customer")
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        ctx=override_settings(MEDIA_ROOT=root/"uploads",V3_WORKSPACE_ROOT=root/"workspaces")
        ctx.enable()
        self.addCleanup(ctx.disable)
    def submit(self):
        self.client.force_login(self.customer)
        response=self.client.post(reverse("submit",args=[self.store.pk]),{
            "baseline":SimpleUploadedFile("base.csv",b"sku,title,price,stock\nA,Sample,10,4\n"),
            "supplier_update":SimpleUploadedFile("update.csv",b"sku,stock\nA,0\n"),
        })
        self.assertEqual(response.status_code,302)
        return CatalogJob.objects.get()
    def test_full_lifecycle_is_audited(self):
        job=self.submit()
        self.assertEqual(list(job.portal_events.values_list("kind",flat=True)),["submitted"])
        services.process_received(job.pk)
        job.refresh_from_db()
        change=services.review(job,self.owner)["changes"][0]
        self.client.force_login(self.owner)
        response=self.client.post(reverse("decision",args=[job.pk]),{
            "change_id":change["id"],"decision":"approved","reason":"synthetic verification"})
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.client.post(reverse("export_job",args=[job.pk])).status_code,302)
        self.client.force_login(self.customer)
        response=self.client.get(reverse("download",args=[job.pk]))
        self.assertEqual(response.status_code,200)
        b"".join(response.streaming_content)
        self.assertEqual(
            list(job.portal_events.order_by("created_at","pk").values_list("kind",flat=True)),
            ["submitted","processed","approved","exported","downloaded"]
        )
        self.assertNotIn("Sample",str(list(job.portal_events.values_list("detail",flat=True))))
    def test_attention_only_for_operator_membership(self):
        job=self.submit()
        services.process_received(job.pk)
        self.client.force_login(self.customer)
        response=self.client.get(reverse("dashboard"))
        self.assertNotContains(response,"Needs your attention")
        self.client.force_login(self.owner)
        response=self.client.get(reverse("dashboard"))
        self.assertContains(response,"Needs your attention")
    def test_revoked_membership_blocks_details_and_download(self):
        job=self.submit()
        Membership.objects.filter(user=self.customer,store=self.store).delete()
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("job_detail",args=[job.pk])).status_code,404)
    def test_unrelated_store_cannot_see_history(self):
        job=self.submit()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("job_detail",args=[job.pk])).status_code,404)
