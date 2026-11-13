from django.core.management import call_command,CommandError
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from catalog_portal.models import Store,Membership

class DemoSeedTests(TestCase):
    @override_settings(LOCAL_DEV=True)
    def test_seed_creates_two_isolated_stores(self):
        call_command("seed_portal_demo","--synthetic-only",verbosity=0)
        self.assertEqual(Store.objects.count(),2)
        self.assertEqual(Membership.objects.count(),4)
        with self.assertRaises(CommandError):
            call_command("seed_portal_demo","--synthetic-only",verbosity=0)
    @override_settings(LOCAL_DEV=False)
    def test_seed_denied_outside_local_dev(self):
        with self.assertRaises(CommandError):
            call_command("seed_portal_demo","--synthetic-only",verbosity=0)
