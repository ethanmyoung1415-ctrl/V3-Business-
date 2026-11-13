from django.test import SimpleTestCase
from django.urls import reverse
class PortalHeaderTests(SimpleTestCase):
    def test_login_not_cacheable(self):
        response=self.client.get(reverse("login"))
        self.assertEqual(response.status_code,200)
        self.assertIn("no-store",response["Cache-Control"])
        self.assertIn("frame-ancestors 'none'",response["Content-Security-Policy"])
        self.assertEqual(response["Referrer-Policy"],"no-referrer")
    def test_redirect_not_cacheable(self):
        response=self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code,302)
        self.assertIn("no-store",response["Cache-Control"])
