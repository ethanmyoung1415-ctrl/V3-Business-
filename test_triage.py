import unittest
from triage import assess_change,assess_hold
class TriageTests(unittest.TestCase):
    def change(self,field,old,new):
        return {"id":"one","sku":"A","field":field,"old":old,"new":new,"status":"pending"}
    def test_large_price(self):
        r=assess_change(self.change("price","10","15"))
        self.assertEqual(r["risk"],"high")
        self.assertEqual(r["evidence"]["percent_change"],"50.00")
    def test_small_price(self):
        self.assertEqual(assess_change(self.change("price","10","11"))["risk"],"medium")
    def test_zero_stock(self):
        self.assertEqual(assess_change(self.change("stock","12","0"))["recommendation"],"verify")
    def test_title(self):
        self.assertEqual(assess_change(self.change("title","Old","New"))["risk"],"medium")
    def test_duplicate(self):
        self.assertEqual(assess_hold({"sku":"A","reason":"duplicate SKU"})["risk"],"critical")
    def test_bad_price(self):
        self.assertEqual(assess_change(self.change("price","abc","12"))["recommendation"],"hold")
if __name__=="__main__":unittest.main()
