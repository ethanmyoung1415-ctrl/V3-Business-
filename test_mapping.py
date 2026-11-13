import csv,tempfile,unittest
from pathlib import Path
from mapping import normalize_csv,validate_mapping

class ExplicitMappingTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
    def test_maps_columns_without_guessing(self):
        source=self.root/"supplier.csv"
        source.write_text(
            "Item Code,Qty Available,Wholesale Cost,Ignore Me\n"
            "00123,0,12.50,test\n",encoding="utf-8")
        target=self.root/"normalized.csv"
        result=normalize_csv(source,target,{
            "sku":"Item Code","stock":"Qty Available",
            "price":"Wholesale Cost"})
        self.assertEqual(result["rows"],1)
        with target.open(newline="",encoding="utf-8") as f:
            row=list(csv.DictReader(f))[0]
        self.assertEqual(row,{"sku":"00123","price":"12.50","stock":"0"})
        self.assertNotIn("Ignore Me",target.read_text())
    def test_duplicate_source_mapping_denied(self):
        with self.assertRaises(ValueError):
            validate_mapping({"sku":"Code","stock":"Code"})
    def test_missing_source_mapping_denied(self):
        source=self.root/"supplier.csv"
        source.write_text("Code,Qty\nA,1\n")
        with self.assertRaises(ValueError):
            normalize_csv(source,self.root/"out.csv",
                          {"sku":"Code","stock":"Inventory"})
        self.assertFalse((self.root/"out.csv").exists())
    def test_baseline_must_map_all_fields(self):
        with self.assertRaises(ValueError):
            validate_mapping({"sku":"Code","stock":"Qty"},baseline=True)
    def test_reject_unsafe_spreadsheet_content(self):
        source=self.root/"supplier.csv"
        source.write_text("Code,Title\nA,=HYPERLINK(1)\n")
        with self.assertRaises(ValueError):
            normalize_csv(source,self.root/"out.csv",{"sku":"Code","title":"Title"})
        self.assertFalse((self.root/"out.csv").exists())
    def test_existing_destination_not_overwritten(self):
        source=self.root/"supplier.csv"
        source.write_text("Code,Qty\nA,1\n")
        target=self.root/"out.csv";target.write_text("keep")
        with self.assertRaises(ValueError):
            normalize_csv(source,target,{"sku":"Code","stock":"Qty"})
        self.assertEqual(target.read_text(),"keep")
    def test_duplicate_header_denied(self):
        source=self.root/"supplier.csv"
        source.write_text("Code,Code\nA,1\n")
        with self.assertRaises(ValueError):
            normalize_csv(source,self.root/"out.csv",{"sku":"Code"})
    def test_unmapped_extra_columns_not_exported(self):
        source=self.root/"supplier.csv"
        source.write_text("Code,Script,Qty\nA,=ALERT(1),0\n")
        result=normalize_csv(source,self.root/"out.csv",
                             {"sku":"Code","stock":"Qty"})
        self.assertEqual(result["fields"],["sku","stock"])
if __name__=="__main__":unittest.main()
