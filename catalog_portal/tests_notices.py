"""Store-scoped, role-specific local notifications."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Store,Membership,CatalogJob,NoticeRead
from . import notices

class NoticeIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.owner=User.objects.create_user("notices-owner",password="Test-Password-123456")
        cls.customer=User.objects.create_user("notices-customer",password="Test-Password-654321")
        cls.foreign=User.objects.create_user("notices-foreign",password="Test-Password-999999")
        cls.a=Store.objects.create(name="Shop A")
        cls.b=Store.objects.create(name="Shop B")
        Membership.objects.create(user=cls.owner,store=cls.a,role="operator")
        Membership.objects.create(user=cls.customer,store=cls.a,role="customer")
        Membership.objects.create(user=cls.foreign,store=cls.b,role="customer")
    def create_job(self,store,status="ready"):
        return CatalogJob.objects.create(
            store=store,submitted_by=self.owner,status=status,
            baseline="mock/b.csv",supplier_update="mock/u.csv")
    def test_operator_review_notice_is_role_scoped(self):
        job=self.create_job(self.a,"review")
        note=notices.create(job,"needs_review","operator")
        self.assertIn(note,list(notices.visible_to(self.owner)))
        self.assertNotIn(note,list(notices.visible_to(self.customer)))
        self.assertNotIn(note,list(notices.visible_to(self.foreign)))
    def test_export_ready_visible_only_to_store_members(self):
        job=self.create_job(self.a,"ready")
        note=notices.create(job,"export_ready","customer")
        self.assertIn(note,list(notices.visible_to(self.customer)))
        self.assertNotIn(note,list(notices.visible_to(self.foreign)))
        with self.assertRaises(PermissionError):
            notices.mark_read(self.foreign,note.pk)
    def test_mark_read_only_affects_current_user(self):
        job=self.create_job(self.a,"ready")
        note=notices.create(job,"export_ready","customer")
        self.client.force_login(self.customer)
        response=self.client.post(reverse("mark_notice_read",args=[note.pk]))
        self.assertEqual(response.status_code,302)
        self.assertNotIn(note,list(notices.visible_to(self.customer)))
        self.assertEqual(NoticeRead.objects.filter(notice=note,user=self.customer).count(),1)
        self.assertIn(note,list(notices.visible_to(self.owner)))
    def test_replayed_read_or_wrong_tenant_denied(self):
        job=self.create_job(self.a,"ready")
        note=notices.create(job,"export_ready","customer")
        self.client.force_login(self.foreign)
        self.assertEqual(self.client.post(reverse("mark_notice_read",args=[note.pk])).status_code,404)
        self.assertFalse(NoticeRead.objects.exists())
    def test_no_fake_ready_notice(self):
        job=self.create_job(self.a,"review")
        with self.assertRaises(ValueError):
            notices.create(job,"export_ready","customer")
    def test_deduplication(self):
        job=self.create_job(self.a,"ready")
        a=notices.create(job,"export_ready","customer")
        b=notices.create(job,"export_ready","customer")
        self.assertEqual(a.pk,b.pk)
