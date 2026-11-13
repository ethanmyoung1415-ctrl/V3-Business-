"""Boundary tests: uploads must be safe BEFORE persisting the job."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ValidationError
from django.test import SimpleTestCase
from .forms import validate_csv

class UploadBoundaryTests(SimpleTestCase):
    def check(self,body,baseline=False):
        file=SimpleUploadedFile("sample.csv",body)
        return validate_csv(file,baseline=baseline)
    def test_zero_stock_is_valid_update(self):
        upload=self.check(b"sku,stock\nA,0\n")
        self.assertEqual(upload.tell(),0)
    def test_duplicate_updates_are_preserved_for_engine_hold(self):
        self.check(b"sku,stock\nA,2\nA,3\n")
    def test_blank_update_value_is_held_downstream(self):
        self.check(b"sku,stock\nA,\n")
    def test_unsafe_formula_rejected(self):
        with self.assertRaises(ValidationError):
            self.check(b"sku,title\nA,=HYPERLINK(1)\n")
    def test_control_character_rejected(self):
        with self.assertRaises(ValidationError):
            self.check(b'sku,title\nA,"Hello\nworld"\n')
    def test_invalid_price_rejected(self):
        with self.assertRaises(ValidationError):
            self.check(b"sku,price\nA,NaN\n")
    def test_duplicate_baseline_sku_rejected(self):
        with self.assertRaises(ValidationError):
            self.check(b"sku,title,price,stock\nA,One,1,2\nA,Two,1,2\n",baseline=True)
    def test_blank_sku_rejected(self):
        with self.assertRaises(ValidationError):
            self.check(b"sku,stock\n,2\n")
    def test_negative_stock_rejected(self):
        with self.assertRaises(ValidationError):
            self.check(b"sku,stock\nA,-1\n")
    def test_malformed_utf8_rejected(self):
        with self.assertRaises(ValidationError):
            self.check(b"sku,title\nA,\xff\n")
