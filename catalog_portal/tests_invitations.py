"""Local-only invitation safety, expiry, single-use and store permissions."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase,override_settings
from django.urls import reverse
from django.utils import timezone
from catalog_portal import invitations
from catalog_portal.models import Store,Membership,StoreInvitation

class LocalInvitationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.operator=User.objects.create_user("invite-operator",password="StrongDemoPassphrase123")
        cls.customer=User.objects.create_user("invite-customer",password="StrongDemoPassphrase456")
        cls.store=Store.objects.create(name="Mock Invite Store")
        cls.unrelated=Store.objects.create(name="Unrelated Mock Store")
        Membership.objects.create(user=cls.operator,store=cls.store,role="operator")
        Membership.objects.create(user=cls.customer,store=cls.store,role="customer")
    @override_settings(LOCAL_DEV=True)
    def test_one_use_customer_invitation(self):
        code=invitations.issue(self.store,self.operator)["code"]
        self.assertEqual(StoreInvitation.objects.count(),1)
        invite=StoreInvitation.objects.get()
        self.assertNotEqual(invite.token_sha256,code)
        self.assertNotIn(code,str(invite.__dict__))
        created=invitations.redeem(code,"new-demo-customer","VeryLongLocalPassphrase999")
        user=get_user_model().objects.get(pk=created["user_id"])
        self.assertTrue(user.check_password("VeryLongLocalPassphrase999"))
        self.assertTrue(Membership.objects.filter(
            user=user,store=self.store,role="customer").exists())
        self.assertFalse(Membership.objects.filter(user=user,role="operator").exists())
        with self.assertRaisesRegex(ValueError,"invalid or expired"):
            invitations.redeem(code,"another-user","VeryLongLocalPassphrase999")
    @override_settings(LOCAL_DEV=True)
    def test_unauthorized_issuer_cannot_invite(self):
        with self.assertRaises(PermissionError):
            invitations.issue(self.store,self.customer)
        with self.assertRaises(PermissionError):
            invitations.issue(self.unrelated,self.operator)
    @override_settings(LOCAL_DEV=True)
    def test_expired_invite_rejected(self):
        code=invitations.issue(self.store,self.operator)["code"]
        StoreInvitation.objects.update(expires_at=timezone.now()-timedelta(minutes=1))
        with self.assertRaises(ValueError):
            invitations.redeem(code,"expired-user","VeryLongLocalPassphrase999")
    @override_settings(LOCAL_DEV=True)
    def test_duplicate_username_does_not_consume_invite(self):
        code=invitations.issue(self.store,self.operator)["code"]
        with self.assertRaisesRegex(ValueError,"username unavailable"):
            invitations.redeem(code,self.customer.username,"VeryLongLocalPassphrase999")
        self.assertIsNone(StoreInvitation.objects.get().redeemed_at)
        invitations.redeem(code,"different-user","VeryLongLocalPassphrase999")
        self.assertIsNotNone(StoreInvitation.objects.get().redeemed_at)
    @override_settings(LOCAL_DEV=True)
    def test_view_does_not_allow_open_registration(self):
        url=reverse("join_local_demo")
        response=self.client.post(url,{
            "code":"totally-invalid-synthetic-code-123456789",
            "username":"never-registered","password":"VeryLongLocalPassphrase999",
            "confirm_password":"VeryLongLocalPassphrase999",
        })
        self.assertEqual(response.status_code,200)
        self.assertContains(response,"Invitation could not be accepted")
        self.assertFalse(get_user_model().objects.filter(username="never-registered").exists())
    @override_settings(LOCAL_DEV=True)
    def test_join_view_redeems_real_one_time_code(self):
        code=invitations.issue(self.store,self.operator)["code"]
        response=self.client.post(reverse("join_local_demo"),{
            "code":code,"username":"invited-new",
            "password":"VeryLongLocalPassphrase999",
            "confirm_password":"VeryLongLocalPassphrase999",
        })
        self.assertEqual(response.status_code,302)
        self.assertTrue(get_user_model().objects.filter(username="invited-new").exists())
    @override_settings(LOCAL_DEV=False)
    def test_local_invitation_disabled_by_default(self):
        with self.assertRaises(PermissionError):
            invitations.issue(self.store,self.operator)
        self.assertEqual(self.client.get(reverse("join_local_demo")).status_code,404)
