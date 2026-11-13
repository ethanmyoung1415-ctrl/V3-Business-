from django.core.cache import cache
from django.test import SimpleTestCase
from django.urls import reverse

class LocalLoginThrottleTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
    def test_login_post_rate_limit(self):
        path=reverse("login")
        data={"username":"synthetic-attempt","password":"NotARealPassword"}
        for _ in range(8):
            response=self.client.post(path,data)
            self.assertNotEqual(response.status_code,429)
        blocked=self.client.post(path,data)
        self.assertEqual(blocked.status_code,429)
        self.assertEqual(blocked["Retry-After"],"900")
    def test_other_pages_not_throttled(self):
        path=reverse("dashboard")
        for _ in range(12):
            self.assertNotEqual(self.client.get(path).status_code,429)
