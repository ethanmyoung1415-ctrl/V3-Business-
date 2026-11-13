from django.contrib.auth import get_user_model
from django.test import TestCase
from catalog_portal.metrics import operator_scorecard
from catalog_portal.models import Store,Membership,CatalogJob,CatalogEvent

class ManagementScorecardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.operator=User.objects.create_user("scorecard-operator",password="VeryStrongTestPassword123")
        cls.customer=User.objects.create_user("scorecard-customer",password="VeryStrongTestPassword456")
        cls.foreign=User.objects.create_user("scorecard-foreign",password="VeryStrongTestPassword789")
        cls.a=Store.objects.create(name="Authorized")
        cls.b=Store.objects.create(name="Not authorized")
        Membership.objects.create(user=cls.operator,store=cls.a,role="operator")
        Membership.objects.create(user=cls.customer,store=cls.a,role="customer")
        Membership.objects.create(user=cls.foreign,store=cls.b,role="operator")
    def create_job(self,store,status):
        user=self.operator if store==self.a else self.foreign
        job=CatalogJob.objects.create(
            store=store,submitted_by=user,status=status,
            baseline="mock/base.csv",supplier_update="mock/update.csv")
        CatalogEvent.objects.create(job=job,actor=user,kind="submitted")
        return job
    def test_operator_only_sees_authorized_store(self):
        self.create_job(self.a,"review")
        self.create_job(self.a,"ready")
        self.create_job(self.b,"failed")
        score=operator_scorecard(self.operator)
        self.assertEqual(score["jobs_total"],2)
        self.assertEqual(score["jobs_awaiting_review"],1)
        self.assertEqual(score["jobs_failed"],0)
        self.assertEqual(score["verified_exports_ready"],1)
        self.assertIsNone(score["monthly_revenue"])
        self.assertEqual(score["event_counts"]["submitted"],2)
    def test_customer_cannot_receive_operator_counts(self):
        self.create_job(self.a,"ready")
        self.assertEqual(operator_scorecard(self.customer)["jobs_total"],0)
