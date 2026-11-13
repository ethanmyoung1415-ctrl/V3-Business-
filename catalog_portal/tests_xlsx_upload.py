"""End-to-end restricted XLSX upload tests for the local Django portal."""
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from catalog_portal.models import Store,Membership,CatalogJob,SupplierProfile
from catalog_portal import services
from test_xlsx_intake import make_xlsx
import engine

class PortalExcelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.customer=User.objects.create_user(
            "xlsx-customer",password="LongSyntheticPass123")
        cls.operator=User.objects.create_user(
            "xlsx-operator",password="LongSyntheticPass456")
        cls.store=Store.objects.create(name="Fictional Excel Shop")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        ctx=override_settings(MEDIA_ROOT=root/"uploads",V3_WORKSPACE_ROOT=root/"work")
        ctx.enable();self.addCleanup(ctx.disable)
        self.root=root
        self.client.force_login(self.customer)
    def workbook(self,name,headers,rows,**kwargs):
        path=self.root/name
        make_xlsx(path,headers,rows,**kwargs)
        return SimpleUploadedFile(name,path.read_bytes(),
                                  content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    def submit(self,baseline,supplier,profile=None):
        data={"baseline":baseline,"supplier_update":supplier}
        if profile is not None:data["supplier_profile"]=str(profile.pk)
        return self.client.post(reverse("submit",args=[self.store.pk]),data)
    def test_excel_baseline_and_supplier_to_verified_export(self):
        baseline=self.workbook("base.xlsx",["sku","title","price","stock"],
                               [["A","Product",10,5]])
        supplier=self.workbook("supplier.xlsx",["sku","stock"],[["A",0]])
        response=self.submit(baseline,supplier)
        self.assertEqual(response.status_code,302)
        job=CatalogJob.objects.get()
        self.assertEqual(Path(job.baseline.path).suffix,".xlsx")
        self.assertEqual(Path(job.supplier_update.path).suffix,".xlsx")
        self.assertEqual(job.baseline_sha256,engine.digest(job.baseline.path))
        self.assertEqual(job.supplier_sha256,engine.digest(job.supplier_update.path))
        result=services.process_received(job.pk)
        self.assertTrue(result["processed"])
        job.refresh_from_db()
        self.assertEqual(job.status,"review")
        change=services.review(job,self.operator)["changes"][0]
        self.assertEqual(change["new"],"0")
        services.decide(job,self.operator,change["id"],"approved","supplier confirmed")
        services.prepare_export(job,self.operator)
        job.refresh_from_db()
        self.assertEqual(job.status,"ready")
        path=services.verified_download_path(job)
        self.assertIn("A,Product,10,0",path.read_text())
    def test_mixed_csv_and_excel_upload(self):
        baseline=SimpleUploadedFile(
            "base.csv",b"sku,title,price,stock\nA,Product,10,5\n")
        supplier=self.workbook("supplier.xlsx",["sku","stock"],[["A",0]])
        self.assertEqual(self.submit(baseline,supplier).status_code,302)
        job=CatalogJob.objects.get()
        self.assertTrue(services.process_received(job.pk)["processed"])
    def test_formula_workbook_is_rejected_before_submission(self):
        baseline=SimpleUploadedFile(
            "base.csv",b"sku,title,price,stock\nA,Product,10,5\n")
        supplier=self.workbook("formula.xlsx",["sku","stock"],
                               [["A",0]],formula=True)
        response=self.submit(baseline,supplier)
        self.assertEqual(response.status_code,200)
        self.assertFalse(CatalogJob.objects.exists())
    def test_multisheet_workbook_rejected_until_explicit_sheet_support(self):
        baseline=SimpleUploadedFile(
            "base.csv",b"sku,title,price,stock\nA,Product,10,5\n")
        supplier=self.workbook("multiple.xlsx",["sku","stock"],
                               [["A",0]],sheets=2)
        response=self.submit(baseline,supplier)
        self.assertEqual(response.status_code,200)
        self.assertFalse(CatalogJob.objects.exists())
    def test_custom_mapping_with_xlsx_rejected_safely(self):
        profile=SupplierProfile.objects.create(
            store=self.store,name="Custom Mapping",
            mapping={"sku":"ITEM_ID","stock":"QTY"})
        baseline=SimpleUploadedFile(
            "base.csv",b"sku,title,price,stock\nA,Product,10,5\n")
        supplier=self.workbook("supplier.xlsx",["sku","stock"],[["A",0]])
        response=self.submit(baseline,supplier,profile=profile)
        self.assertEqual(response.status_code,200)
        self.assertFalse(CatalogJob.objects.exists())
