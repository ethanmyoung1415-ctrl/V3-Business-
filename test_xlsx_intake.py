import tempfile
import unittest
import zipfile
from pathlib import Path
import xlsx_intake

MAIN="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL="http://schemas.openxmlformats.org/officeDocument/2006/relationships"

def _letters(i):
    return chr(ord("A")+i)

def make_xlsx(path,header,rows,*,formula=False,sheets=1,extra=None,hidden_row=False,styled_numeric=False,merged=False):
    def sheet_xml():
        parts=[]
        for idx,values in enumerate([header]+rows,1):
            cells=[]
            for col,value in enumerate(values):
                address=f"{_letters(col)}{idx}"
                if formula and idx==2 and col==1:
                    cells.append(f'<c r="{address}"><f>1+1</f><v>2</v></c>')
                elif isinstance(value,int):
                    style_attr=' s="1"' if styled_numeric else ''
                    cells.append(f'<c r="{address}"{style_attr}><v>{value}</v></c>')
                else:
                    cells.append(f'<c r="{address}" t="inlineStr"><is><t>{value}</t></is></c>')
            hidden_attr=' hidden="1"' if hidden_row and idx==2 else ''
            parts.append(f'<row r="{idx}"{hidden_attr}>{"".join(cells)}</row>')
        merged_xml='<mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells>' if merged else ''
        return (f'<worksheet xmlns="{MAIN}"><sheetData>{"".join(parts)}'
                '</sheetData>'+merged_xml+'</worksheet>')
    workbook=(f'<workbook xmlns="{MAIN}" xmlns:r="{REL}"><sheets>'+
              ''.join(f'<sheet name="Sheet{i}" sheetId="{i}" r:id="rId{i}"/>'
                      for i in range(1,sheets+1))+
              '</sheets></workbook>')
    rels=('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+
          ''.join(f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml" '
                  f'Type="{REL}/worksheet"/>' for i in range(1,sheets+1))+
          '</Relationships>')
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml","<Types/>")
        z.writestr("xl/workbook.xml",workbook)
        z.writestr("xl/_rels/workbook.xml.rels",rels)
        for i in range(1,sheets+1):
            z.writestr(f"xl/worksheets/sheet{i}.xml",sheet_xml())
        if extra:
            for name,content in extra.items():z.writestr(name,content)

class RestrictedExcelIntakeTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.source=self.root/"supplier.xlsx"
        self.dest=self.root/"converted.csv"
    def test_zero_stock_excel_is_converted(self):
        make_xlsx(self.source,["sku","stock"],[["A",0]])
        result=xlsx_intake.convert(self.source,self.dest)
        self.assertEqual(result["rows"],1)
        self.assertIn("A,0",self.dest.read_text())
    def test_baseline_excel_is_converted(self):
        make_xlsx(self.source,["sku","title","price","stock"],
                  [["A","Example",10,5]])
        result=xlsx_intake.convert(self.source,self.dest,baseline=True)
        self.assertEqual(result["rows"],1)
        self.assertIn("A,Example,10,5",self.dest.read_text())
    def test_formula_cell_is_rejected(self):
        make_xlsx(self.source,["sku","stock"],[["A",0]],formula=True)
        with self.assertRaisesRegex(ValueError,"formula"):
            xlsx_intake.convert(self.source,self.dest)
        self.assertFalse(self.dest.exists())
    def test_multiple_sheets_require_explicit_selection(self):
        make_xlsx(self.source,["sku","stock"],[["A",0]],sheets=2)
        with self.assertRaisesRegex(ValueError,"multiple"):
            xlsx_intake.convert(self.source,self.dest)
        xlsx_intake.convert(self.source,self.dest,sheet="Sheet2")
        self.assertIn("A,0",self.dest.read_text())
    def test_macro_part_rejected(self):
        make_xlsx(self.source,["sku","stock"],[["A",0]],
                  extra={"xl/vbaProject.bin":"fake-macro"})
        with self.assertRaisesRegex(ValueError,"unsupported"):
            xlsx_intake.convert(self.source,self.dest)
    def test_zip_slip_rejected(self):
        make_xlsx(self.source,["sku","stock"],[["A",0]],
                  extra={"xl/../bad.xml":"bad"})
        with self.assertRaisesRegex(ValueError,"unsafe workbook"):
            xlsx_intake.convert(self.source,self.dest)
    def test_unsafe_spreadsheet_title_is_rejected(self):
        make_xlsx(self.source,["sku","title"],[["A","=SUM(1)"]])
        with self.assertRaises(ValueError):
            xlsx_intake.convert(self.source,self.dest)
    def test_external_relationship_is_rejected(self):
        relationship=(
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
            'Target="https://example.invalid/collect" TargetMode="External"/>'
            '</Relationships>')
        make_xlsx(self.source,["sku","stock"],[["A",0]],
                  extra={"xl/worksheets/_rels/sheet1.xml.rels":relationship})
        with self.assertRaisesRegex(ValueError,"external relationships"):
            xlsx_intake.convert(self.source,self.dest)
    def test_hidden_rows_are_rejected(self):
        make_xlsx(self.source,["sku","stock"],[["A",0]],hidden_row=True)
        with self.assertRaisesRegex(ValueError,"hidden worksheet rows"):
            xlsx_intake.convert(self.source,self.dest)
    def test_styled_numeric_values_are_rejected(self):
        make_xlsx(self.source,["sku","stock"],[["A",0]],styled_numeric=True)
        with self.assertRaisesRegex(ValueError,"styled numeric"):
            xlsx_intake.convert(self.source,self.dest)
    def test_merged_cells_are_rejected(self):
        make_xlsx(self.source,["sku","stock"],[["A",0]],merged=True)
        with self.assertRaisesRegex(ValueError,"merged cells"):
            xlsx_intake.convert(self.source,self.dest)
    def test_numeric_sku_is_rejected_to_protect_leading_zeros(self):
        make_xlsx(self.source,["sku","stock"],[[123,0]])
        with self.assertRaisesRegex(ValueError,"SKU cells must be stored as text"):
            xlsx_intake.convert(self.source,self.dest)
        self.assertFalse(self.dest.exists())
    def test_text_sku_preserves_leading_zeros(self):
        make_xlsx(self.source,["sku","stock"],[["0012345",0]])
        xlsx_intake.convert(self.source,self.dest)
        self.assertIn("0012345,0",self.dest.read_text())
    def test_shared_string_cells_preserve_identifiers(self):
        # Construct a minimal real XLSX using shared string references.
        ns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        rel="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        workbook=(f'<workbook xmlns="{ns}" xmlns:r="{rel}"><sheets>'
                  '<sheet name="Stock" sheetId="1" r:id="rId1"/></sheets></workbook>')
        relationships=(
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/worksheet" '
            'Target="worksheets/sheet1.xml"/></Relationships>')
        shared=(f'<sst xmlns="{ns}" count="3" uniqueCount="3">'
                '<si><t>sku</t></si><si><t>stock</t></si>'
                '<si><t>000987</t></si></sst>')
        sheet=(f'<worksheet xmlns="{ns}"><sheetData>'
               '<row r="1"><c r="A1" t="s"><v>0</v></c>'
               '<c r="B1" t="s"><v>1</v></c></row>'
               '<row r="2"><c r="A2" t="s"><v>2</v></c>'
               '<c r="B2"><v>0</v></c></row></sheetData></worksheet>')
        with zipfile.ZipFile(self.source,"w",compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("xl/workbook.xml",workbook)
            z.writestr("xl/_rels/workbook.xml.rels",relationships)
            z.writestr("xl/sharedStrings.xml",shared)
            z.writestr("xl/worksheets/sheet1.xml",sheet)
        result=xlsx_intake.convert(self.source,self.dest)
        self.assertEqual(result["rows"],1)
        self.assertIn("000987,0",self.dest.read_text())
    def test_1000_row_supplier_workbook_preserves_values(self):
        rows=[[f"SKU-{i:06d}",0 if i%19==0 else (i%100)+1]
              for i in range(1000)]
        make_xlsx(self.source,["sku","stock"],rows)
        result=xlsx_intake.convert(self.source,self.dest)
        self.assertEqual(result["rows"],1000)
        import csv
        with self.dest.open(newline="",encoding="utf-8") as stream:
            records=list(csv.DictReader(stream))
        self.assertEqual(len(records),1000)
        self.assertEqual(records[0]["sku"],"SKU-000000")
        self.assertEqual(records[0]["stock"],"0")
        self.assertEqual(records[19]["stock"],"0")
        self.assertEqual(records[-1]["sku"],"SKU-000999")
    def test_cannot_overwrite_existing(self):
        make_xlsx(self.source,["sku","stock"],[["A",0]])
        self.dest.write_text("important")
        with self.assertRaises(ValueError):
            xlsx_intake.convert(self.source,self.dest)
        self.assertEqual(self.dest.read_text(),"important")
if __name__=="__main__":unittest.main()
