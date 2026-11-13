import tempfile
import unittest
import zipfile
from pathlib import Path
import xlsx_intake

MAIN="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL="http://schemas.openxmlformats.org/officeDocument/2006/relationships"

def _letters(i):
    return chr(ord("A")+i)

def make_xlsx(path,header,rows,*,formula=False,sheets=1,extra=None):
    def sheet_xml():
        parts=[]
        for idx,values in enumerate([header]+rows,1):
            cells=[]
            for col,value in enumerate(values):
                address=f"{_letters(col)}{idx}"
                if formula and idx==2 and col==1:
                    cells.append(f'<c r="{address}"><f>1+1</f><v>2</v></c>')
                elif isinstance(value,int):
                    cells.append(f'<c r="{address}"><v>{value}</v></c>')
                else:
                    cells.append(f'<c r="{address}" t="inlineStr"><is><t>{value}</t></is></c>')
            parts.append(f'<row r="{idx}">{"".join(cells)}</row>')
        return (f'<worksheet xmlns="{MAIN}"><sheetData>{"".join(parts)}'
                '</sheetData></worksheet>')
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
    def test_cannot_overwrite_existing(self):
        make_xlsx(self.source,["sku","stock"],[["A",0]])
        self.dest.write_text("important")
        with self.assertRaises(ValueError):
            xlsx_intake.convert(self.source,self.dest)
        self.assertEqual(self.dest.read_text(),"important")
if __name__=="__main__":unittest.main()
