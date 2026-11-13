import tempfile,uuid
from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import TestCase,override_settings
from catalog_portal.models import Store,Membership,CatalogJob
from catalog_portal import services
import engine

class ExportRecoveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operator=get_user_model().objects.create_user(
            "recovery-operator",password="VeryLong-Test-Password123")
        cls.store=Store.objects.create(name="Recovery Synthetic")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        context=override_settings(MEDIA_ROOT=root/"uploads",
                                  V3_WORKSPACE_ROOT=root/"work")
        context.enable();self.addCleanup(context.disable)
        b=root/"base.csv";u=root/"update.csv"
        b.write_text("sku,title,price,stock\nA,Test,10,12\n")
        u.write_text("sku,stock\nA,11\n")
        db=services.backend_db(self.store.pk)
        result=engine.ingest(db,b,u)
        change=engine.review(db,result["job_id"])["changes"][0]
        engine.decide(db,change["id"],"approved","operator","verified source")
        self.job=CatalogJob.objects.create(
            store=self.store,submitted_by=self.operator,status="review",
            baseline="synthetic/base.csv",supplier_update="synthetic/update.csv",
            engine_job_id=uuid.UUID(result["job_id"]))
        self.db=db
    def test_recover_verified_export_after_status_crash(self):
        path=services.output_path(self.job)
        engine.export(self.db,str(self.job.engine_job_id),path)
        self.assertEqual(self.job.status,"review")
        result=services.prepare_export(self.job,self.operator)
        self.assertTrue(result["recovered"])
        self.job.refresh_from_db()
        self.assertEqual(self.job.status,"ready")
        self.assertEqual(len(self.job.export_sha256),64)
    def test_tampered_partial_state_cannot_be_recovered(self):
        path=services.output_path(self.job)
        engine.export(self.db,str(self.job.engine_job_id),path)
        path.write_text("sku,title,price,stock\nA,Test,10,999\n")
        with self.assertRaisesRegex(ValueError,"independent verification"):
            services.prepare_export(self.job,self.operator)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status,"review")
    def test_uncommitted_file_never_counts_as_export(self):
        path=services.output_path(self.job)
        path.write_text("sku,title,price,stock\nA,Test,10,11\n")
        with self.assertRaisesRegex(ValueError,"without committed engine audit"):
            services.prepare_export(self.job,self.operator)
