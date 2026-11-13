"""Tenant-isolated local quality support workflow."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Store,Membership,CatalogJob,CustomerIssue,CatalogEvent

class QualityIssueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.customer=User.objects.create_user("issue-customer",password="Long-Demo-Password123")
        cls.operator=User.objects.create_user("issue-operator",password="Long-Demo-Password456")
        cls.foreign=User.objects.create_user("issue-foreign",password="Long-Demo-Password789")
        cls.a=Store.objects.create(name="Issue Test Store")
        cls.b=Store.objects.create(name="Separate Store")
        Membership.objects.create(user=cls.customer,store=cls.a,role="customer")
        Membership.objects.create(user=cls.operator,store=cls.a,role="operator")
        Membership.objects.create(user=cls.foreign,store=cls.b,role="customer")
    def setUp(self):
        self.job=CatalogJob.objects.create(
            store=self.a,submitted_by=self.customer,status="ready",
            baseline="sample/base.csv",supplier_update="sample/update.csv")
    def open_case(self):
        self.client.force_login(self.customer)
        result=self.client.post(reverse("open_quality_issue",args=[self.job.pk]),{
            "subject":"Suspected incorrect stock",
            "message":"A sample inventory number does not match the supplier source."})
        self.assertEqual(result.status_code,302)
        return CustomerIssue.objects.get()
    def test_customer_case_and_operator_resolution_are_audited(self):
        issue=self.open_case()
        self.assertEqual(issue.store_id,self.a.pk)
        self.assertEqual(issue.job_id,self.job.pk)
        self.assertTrue(CatalogEvent.objects.filter(
            job=self.job,kind="issue_opened").exists())
        self.client.force_login(self.operator)
        response=self.client.post(reverse("resolve_quality_issue",args=[issue.pk]),{
            "resolution":"Verified the fictional supplier data; corrected procedure."})
        self.assertEqual(response.status_code,302)
        issue.refresh_from_db()
        self.assertEqual(issue.status,"resolved")
        self.assertEqual(issue.resolved_by,self.operator)
        self.assertTrue(CatalogEvent.objects.filter(
            job=self.job,kind="issue_resolved").exists())
    def test_customer_cannot_resolve_own_case(self):
        issue=self.open_case()
        response=self.client.post(reverse("resolve_quality_issue",args=[issue.pk]),{
            "resolution":"I should not be able to approve this resolution"})
        self.assertEqual(response.status_code,404)
        issue.refresh_from_db()
        self.assertEqual(issue.status,"open")
    def test_cross_store_actions_denied(self):
        issue=self.open_case()
        self.client.force_login(self.foreign)
        self.assertEqual(self.client.post(reverse("open_quality_issue",args=[self.job.pk]),{
            "subject":"Unrelated request","message":"This must never be accepted."
        }).status_code,404)
        self.assertEqual(self.client.post(reverse("resolve_quality_issue",args=[issue.pk]),{
            "resolution":"I have no permission on this customer store"
        }).status_code,404)
    def test_resolution_cannot_be_replayed(self):
        issue=self.open_case()
        self.client.force_login(self.operator)
        path=reverse("resolve_quality_issue",args=[issue.pk])
        data={"resolution":"Reviewed synthetic quality complaint and closed."}
        self.assertEqual(self.client.post(path,data).status_code,302)
        self.assertEqual(self.client.post(path,data).status_code,404)
        self.assertEqual(CatalogEvent.objects.filter(job=self.job,kind="issue_resolved").count(),1)
    def test_malformed_message_not_accepted(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.post(reverse("open_quality_issue",args=[self.job.pk]),{
            "subject":"short","message":"bad"}).status_code,404)
        self.assertFalse(CustomerIssue.objects.exists())
    def test_operator_template_displays_resolution_controls(self):
        issue=self.open_case()
        self.client.force_login(self.operator)
        response=self.client.get(reverse("job_detail",args=[self.job.pk]))
        self.assertContains(response,"Record resolution")
        self.client.force_login(self.customer)
        response=self.client.get(reverse("job_detail",args=[self.job.pk]))
        self.assertNotContains(response,"Record resolution")
        self.assertContains(response,"Suspected incorrect stock")
