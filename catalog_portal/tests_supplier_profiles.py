"""Tenant-scoped explicit supplier mapping portal tests."""
import csv
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import CatalogJob,Membership,Store,SupplierProfile
from . import services

class SupplierProfilePortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.customer=User.objects.create_user("mapped-customer",password="Strong-Test-Password123")
        cls.operator=User.objects.create_user("mapped-operator",password="Strong-Test-Password456")
        cls.other=User.objects.create_user("mapped-other",password="Strong-Test-Password789")
        cls.store=Store.objects.create(name="Mapped demo store")
        cls.other_store=Store.objects.create(name="Unrelated demo store")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
        Membership.objects.create(user=cls.other,store=cls.other_store,role="customer")
        cls.profile=SupplierProfile.objects.create(
            store=cls.store,name="Example supplier",
            mapping={"sku":"Supplier Code","stock":"Units Available"})
        cls.foreign=SupplierProfile.objects.create(
            store=cls.other_store,name="Other supplier",
            mapping={"sku":"Foreign Code","stock":"On Hand"})
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        context=override_settings(MEDIA_ROOT=root/"uploads",V3_WORKSPACE_ROOT=root/"work")
        context.enable();self.addCleanup(context.disable)
        self.client.force_login(self.customer)
    def send(self,profile,source=None):
        source=source if source is not None else (
            b"Supplier Code,Units Available,Ignored\n000123,0,extra\n")
        return self.client.post(reverse("submit",args=[self.store.pk]),{
            "supplier_profile":str(profile),
            "baseline":SimpleUploadedFile("baseline.csv",
                b"sku,title,price,stock\n000123,Test Product,10,12\n"),
            "supplier_update":SimpleUploadedFile("supplier.csv",source),
        })
    def test_profiled_upload_processes_to_canonical_csv(self):
        response=self.send(self.profile.pk)
        self.assertEqual(response.status_code,302)
        job=CatalogJob.objects.get()
        self.assertEqual(job.mapping_snapshot,self.profile.mapping)
        result=services.process_received(job.pk)
        self.assertEqual(result["status"],"review")
        job.refresh_from_db()
        proposed=services.review(job,self.operator)["changes"]
        self.assertEqual(len(proposed),1)
        self.assertEqual((proposed[0]["sku"],proposed[0]["field"],proposed[0]["new"]),
                         ("000123","stock","0"))
    def test_foreign_profile_rejected(self):
        response=self.send(self.foreign.pk)
        self.assertEqual(response.status_code,200)
        self.assertFalse(CatalogJob.objects.exists())
    def test_malformed_source_mapping_denied(self):
        response=self.send(self.profile.pk,b"Supplier Code,Something Else\n000123,0\n")
        self.assertEqual(response.status_code,200)
        self.assertFalse(CatalogJob.objects.exists())
    def test_snapshot_unchanged_when_profile_edited(self):
        self.send(self.profile.pk)
        job=CatalogJob.objects.get()
        self.profile.mapping={"sku":"Changed","stock":"Different"}
        self.profile.save(update_fields=["mapping"])
        services.process_received(job.pk)
        job.refresh_from_db()
        changes=services.review(job,self.operator)["changes"]
        self.assertEqual(len(changes),1)
        self.assertEqual(changes[0]["new"],"0")
    def test_mapped_formula_rejected(self):
        self.profile.mapping={"sku":"Supplier Code","title":"Product Name"}
        self.profile.save(update_fields=["mapping"])
        response=self.send(self.profile.pk,
            b"Supplier Code,Product Name\n000123,=HYPERLINK(1)\n")
        self.assertEqual(response.status_code,200)
        self.assertFalse(CatalogJob.objects.exists())
    def test_duplicate_source_column_rejected(self):
        response=self.send(self.profile.pk,
            b"Supplier Code,Units Available,Units Available\n000123,0,1\n")
        self.assertEqual(response.status_code,200)
        self.assertFalse(CatalogJob.objects.exists())
