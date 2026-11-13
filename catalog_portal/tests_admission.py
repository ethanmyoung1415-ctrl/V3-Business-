"""Local quota tests that never touch real customers or remote systems."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from catalog_portal import admission
from catalog_portal.models import Store,Membership,CatalogJob

class LocalSubmissionQuotaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.user=User.objects.create_user(
            "quota-shop-user",password="LongSyntheticPassword123")
        cls.other=User.objects.create_user(
            "quota-other-user",password="LongSyntheticPassword456")
        cls.store=Store.objects.create(name="Synthetic limited store")
        cls.other_store=Store.objects.create(name="Synthetic unrelated store")
        Membership.objects.create(user=cls.user,store=cls.store,role="customer")
        Membership.objects.create(user=cls.other,store=cls.store,role="customer")
        Membership.objects.create(user=cls.other,store=cls.other_store,role="customer")
    def add_job(self,user,status="ready",age_minutes=0,store=None):
        job=CatalogJob.objects.create(
            store=store or self.store,submitted_by=user,
            status=status,baseline="fictional/base.csv",
            supplier_update="fictional/update.csv")
        if age_minutes:
            CatalogJob.objects.filter(pk=job.pk).update(
                created_at=timezone.now()-timedelta(minutes=age_minutes))
        return job
    def test_empty_store_allowed(self):
        result=admission.check(self.store,self.user)
        self.assertTrue(result["allowed"])
    def test_active_job_limit_denies(self):
        for _ in range(admission.MAX_ACTIVE_PER_STORE):
            self.add_job(self.user,"review")
        result=admission.check(self.store,self.user)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"],"active_store_queue_limit")
        self.client.force_login(self.user)
        response=self.client.post(reverse("submit",args=[self.store.id]),{})
        self.assertEqual(response.status_code,429)
        self.assertEqual(response["Retry-After"],"3600")
    def test_hourly_user_limit_denies(self):
        for _ in range(admission.MAX_USER_SUBMISSIONS_PER_HOUR):
            self.add_job(self.user,"ready")
        result=admission.check(self.store,self.user)
        self.assertEqual(result["reason"],"user_hourly_submission_limit")
    def test_hourly_store_limit_denies_distinct_users(self):
        for i in range(admission.MAX_STORE_SUBMISSIONS_PER_HOUR):
            self.add_job(self.user if i%2==0 else self.other,"ready")
        result=admission.check(self.store,self.user)
        self.assertEqual(result["reason"],"store_hourly_submission_limit")
    def test_old_completed_jobs_do_not_count(self):
        for _ in range(60):
            self.add_job(self.user,"ready",age_minutes=120)
        self.assertTrue(admission.check(self.store,self.user)["allowed"])
    def test_other_store_jobs_do_not_consume_quota(self):
        for _ in range(60):
            self.add_job(self.other,"review",store=self.other_store)
        self.assertTrue(admission.check(self.store,self.user)["allowed"])
    def test_allowed_get_does_not_require_capacity(self):
        for _ in range(admission.MAX_ACTIVE_PER_STORE):
            self.add_job(self.user,"review")
        self.client.force_login(self.user)
        response=self.client.get(reverse("submit",args=[self.store.id]))
        self.assertEqual(response.status_code,200)
