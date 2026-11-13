from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Store,Membership,SupplierProfile

class OperatorSupplierConfigTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.operator=User.objects.create_user("supplier-operator",password="Long-Test-Passphrase123")
        cls.customer=User.objects.create_user("supplier-customer",password="Long-Test-Passphrase456")
        cls.other=User.objects.create_user("supplier-other",password="Long-Test-Passphrase789")
        cls.a=Store.objects.create(name="Mapped Store")
        cls.b=Store.objects.create(name="Other Store")
        Membership.objects.create(user=cls.operator,store=cls.a,role="operator")
        Membership.objects.create(user=cls.customer,store=cls.a,role="customer")
        Membership.objects.create(user=cls.other,store=cls.b,role="operator")
    def path(self,store):
        return reverse("configure_supplier",args=[store.pk])
    def test_only_store_operator_can_create_mapping(self):
        data={"name":"Vendor One",
              "mapping_json":'{"sku":"Item Number","stock":"Available Units"}'}
        self.client.force_login(self.customer)
        self.assertEqual(self.client.post(self.path(self.a),data).status_code,404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.path(self.a),data).status_code,404)
        self.client.force_login(self.operator)
        response=self.client.post(self.path(self.a),data)
        self.assertEqual(response.status_code,302)
        profile=SupplierProfile.objects.get()
        self.assertEqual(profile.store,self.a)
        self.assertEqual(profile.mapping,
            {"sku":"Item Number","stock":"Available Units"})
        self.assertFalse(SupplierProfile.objects.filter(store=self.b).exists())
    def test_duplicate_profile_name_held(self):
        self.client.force_login(self.operator)
        data={"name":"Vendor One","mapping_json":'{"sku":"Item Number"}'}
        self.assertEqual(self.client.post(self.path(self.a),data).status_code,302)
        response=self.client.post(self.path(self.a),data)
        self.assertEqual(response.status_code,200)
        self.assertContains(response,"already exists")
        self.assertEqual(SupplierProfile.objects.count(),1)
    def test_conflicting_column_assignments_rejected(self):
        self.client.force_login(self.operator)
        response=self.client.post(self.path(self.a),{
            "name":"Bad mapping",
            "mapping_json":'{"sku":"Same","stock":"Same"}'})
        self.assertEqual(response.status_code,200)
        self.assertFalse(SupplierProfile.objects.exists())
    def test_unrecognized_json_field_rejected(self):
        self.client.force_login(self.operator)
        response=self.client.post(self.path(self.a),{
            "name":"Bad",
            "mapping_json":'{"sku":"Code","payment_token":"Card"}'})
        self.assertEqual(response.status_code,200)
        self.assertFalse(SupplierProfile.objects.exists())
