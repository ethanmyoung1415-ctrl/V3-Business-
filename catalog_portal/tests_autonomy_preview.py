import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import TestCase,override_settings
from django.urls import reverse
from catalog_portal.models import CatalogJob,Store,Membership
from catalog_portal import services
import engine

class AutomationPreviewPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.operator=User.objects.create_user("preview-operator",password="LongTestPassword111")
        cls.customer=User.objects.create_user("preview-customer",password="LongTestPassword222")
        cls.other=User.objects.create_user("preview-other",password="LongTestPassword333")
        cls.store=Store.objects.create(name="Fictional Preview Store")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        ctx=override_settings(V3_WORKSPACE_ROOT=root/"store-workspaces")
        ctx.enable();self.addCleanup(ctx.disable)
        self.job=CatalogJob.objects.create(
            store=self.store,submitted_by=self.customer,
            baseline="fictional/b.csv",supplier_update="fictional/u.csv",
            status="review")
        b=root/"baseline.csv";u=root/"supplier.csv"
        b.write_text("sku,title,price,stock\nA,Item,10,100\nB,Second,10,20\n")
        u.write_text("sku,stock\nA,102\nB,0\n")
        result=engine.ingest(services.backend_db(self.store.id),b,u,
                             job_id=str(self.job.pk))
        self.job.engine_job_id=result["job_id"]
        self.job.save(update_fields=["engine_job_id"])
    def test_only_operator_can_preview(self):
        path=reverse("automation_preview",args=[self.job.pk])
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(path).status_code,404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(path).status_code,404)
        self.client.force_login(self.operator)
        response=self.client.get(path)
        self.assertEqual(response.status_code,200)
        self.assertContains(response,"Simulation only.")
        self.assertContains(response,"Actions executed")
        self.assertContains(response,"102")
        self.assertNotContains(response,"Approvals made: <strong>1</strong>",html=False)
    def test_preview_keeps_all_change_decisions_pending(self):
        path=reverse("automation_preview",args=[self.job.pk])
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get(path).status_code,200)
        states=[c["status"] for c in engine.review(
            services.backend_db(self.store.pk),str(self.job.pk))["changes"]]
        self.assertEqual(states,["pending","pending"])
    def test_post_is_not_a_decision_endpoint(self):
        self.client.force_login(self.operator)
        self.assertEqual(self.client.post(
            reverse("automation_preview",args=[self.job.pk])).status_code,404)
