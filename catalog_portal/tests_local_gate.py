from django.test import SimpleTestCase
from django.urls import reverse

class LocalGateTests(SimpleTestCase):
    def test_non_loopback_request_denied(self):
        response=self.client.get(reverse("login"),REMOTE_ADDR="203.0.113.18")
        self.assertEqual(response.status_code,403)
        self.assertNotIn(b"Sign in",response.content)
    def test_ipv6_loopback_allowed(self):
        response=self.client.get(reverse("login"),REMOTE_ADDR="::1")
        self.assertEqual(response.status_code,200)
    def test_proxy_header_does_not_override_remote_address(self):
        response=self.client.get(reverse("login"),REMOTE_ADDR="198.51.100.32",
                                 HTTP_X_FORWARDED_FOR="127.0.0.1")
        self.assertEqual(response.status_code,403)
