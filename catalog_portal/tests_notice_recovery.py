"""Notifications remain current, and retry failures create a new alert."""
from datetime import timedelta
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from .models import Store,Membership,CatalogJob,PortalNotice
from . import notices

class NoticeReconciliationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.operator=User.objects.create_user("notice-recon-operator",password="Test-Long-Password123")
        cls.customer=User.objects.create_user("notice-recon-customer",password="Test-Long-Password456")
        cls.store=Store.objects.create(name="Notice Reconciliation Shop")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
    def job(self,status):
        return CatalogJob.objects.create(
            store=self.store,submitted_by=self.customer,status=status,
            baseline="mock/b.csv",supplier_update="mock/u.csv")
    def test_reconciliation_is_idempotent(self):
        job=self.job("ready")
        call_command("reconcile_notices",stdout=StringIO())
        call_command("reconcile_notices",stdout=StringIO())
        self.assertEqual(PortalNotice.objects.filter(job=job).count(),1)
    def test_stale_review_alert_is_hidden_after_completion(self):
        job=self.job("review")
        review_notice=notices.create(job,"needs_review","operator")
        self.assertIn(review_notice,list(notices.visible_to(self.operator)))
        job.status="ready"
        job.save(update_fields=["status","updated_at"])
        call_command("reconcile_notices",stdout=StringIO())
        self.assertNotIn(review_notice,list(notices.visible_to(self.operator)))
        self.assertEqual(list(notices.visible_to(self.customer))[0].kind,"export_ready")
    def test_refailed_job_gets_fresh_alert(self):
        job=self.job("failed")
        first=notices.create(job,"job_failed","customer")
        notices.mark_read(self.customer,first.pk)
        job.status="received";job.save(update_fields=["status","updated_at"])
        job.status="failed"
        job.save(update_fields=["status","updated_at"])
        second=notices.create(job,"job_failed","customer")
        self.assertNotEqual(first.pk,second.pk)
        self.assertIn(second,list(notices.visible_to(self.customer)))
    def test_no_notification_in_new_or_processing_job(self):
        job=self.job("received")
        call_command("reconcile_notices",stdout=StringIO())
        self.assertFalse(PortalNotice.objects.filter(job=job).exists())
