from django.test import SimpleTestCase
class NoPrivilegedAdminRouteTests(SimpleTestCase):
    def test_admin_login_is_not_routed(self):
        response=self.client.get("/admin/")
        self.assertEqual(response.status_code,404)
    def test_admin_models_are_not_exposed_as_web_pages(self):
        response=self.client.get("/admin/catalog_portal/store/")
        self.assertEqual(response.status_code,404)
