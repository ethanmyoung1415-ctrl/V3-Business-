import tempfile,unittest
from pathlib import Path
import engine
class NumericSafetyTests(unittest.TestCase):
    def test_equivalent_price_strings_are_identical(self):
        self.assertEqual(engine.price("10"),"10")
        self.assertEqual(engine.price("10.0"),"10")
        self.assertEqual(engine.price("10.00"),"10")
        self.assertEqual(engine.price("00010.0000"),"10")
    def test_fractional_price_preserved_up_to_four_places(self):
        self.assertEqual(engine.price("5.1250"),"5.125")
        with self.assertRaises(ValueError):engine.price("5.12345")
    def test_unbounded_decimals_rejected(self):
        for value in ("1E+10000","NaN","Infinity","-1","1000000001"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):engine.price(value)
    def test_stock_bounds(self):
        self.assertEqual(engine.stock("0000"),"0")
        for value in ("-1","1.0","9999999999999999999"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):engine.stock(value)
    def test_unchanged_numeric_price_does_not_trigger_review(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)/"base.csv";update=Path(temp)/"update.csv"
            base.write_text("sku,title,price,stock\nA,Test,10.00,4\n")
            update.write_text("sku,price\nA,10\n")
            result=engine.ingest(Path(temp)/"db.sqlite3",base,update)
            self.assertEqual(result["changes"],0)
            self.assertEqual(result["holds"],[])
if __name__=="__main__":unittest.main()
