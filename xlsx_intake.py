"""Restricted XLSX -> canonical V3 CSV conversion for *fictional* supplier data.

No macro, formula, hyperlink, external relationship or calculation support.
Uses only the Python standard library, parses one explicitly identified worksheet,
and rejects unsupported workbook features rather than guessing their meaning.
This is not a full Excel import implementation and is NOT production approved.
"""
import argparse
import csv
import json
import os
import posixpath
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import engine

MAIN="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG="http://schemas.openxmlformats.org/package/2006/relationships"
MAX_COMPRESSED=15_000_000
MAX_UNCOMPRESSED=50_000_000
MAX_ENTRIES=250
MAX_ROWS=100_000
MAX_COLUMNS=12
MAX_STRINGS=100_000
MAX_SHARED_BYTES=16_000_000
CELL_REF=re.compile(r"^([A-Z]{1,3})([1-9][0-9]{0,6})$")
FIELDS=set(engine.FIELDS)

def _safe_zip(path):
    path=Path(path)
    if path.suffix.lower()!=".xlsx" or not path.is_file():
        raise ValueError("only regular .xlsx files are accepted")
    if path.is_symlink() or path.stat().st_size>MAX_COMPRESSED:
        raise ValueError("linked or oversized workbook")
    try:
        archive=zipfile.ZipFile(path,"r")
    except (OSError,zipfile.BadZipFile) as exc:
        raise ValueError("not a valid XLSX package") from exc
    members=archive.infolist()
    if len(members)>MAX_ENTRIES or not members:
        archive.close();raise ValueError("workbook contains too many package members")
    seen=set()
    size=0
    for member in members:
        name=member.filename
        normalized=posixpath.normpath(name)
        if (name in seen or name.startswith("/") or "\\" in name or
                normalized!=name.rstrip("/") or
                any(part in ("..",".") for part in name.split("/"))):
            archive.close();raise ValueError("unsafe workbook package path")
        seen.add(name)
        size+=member.file_size
        if (size>MAX_UNCOMPRESSED or member.file_size>MAX_UNCOMPRESSED or
                member.file_size>max(member.compress_size,1)*200):
            archive.close();raise ValueError("workbook exceeds decompression safety limit")
        lowered=name.lower()
        if (any(word in lowered for word in (
                "vbaproject","externallinks/","connections.xml",
                "querytables/","calcchain.xml","embeddings/","activex/"))
                or lowered.endswith(".bin")):
            archive.close();raise ValueError("unsupported or external workbook feature")
    # Reject all outbound relationships, even when a particular sheet does
    # not reference them. Never fetch or silently accept remote workbook data.
    for member in members:
        if not member.filename.lower().endswith(".rels"):
            continue
        if member.file_size>2_000_000:
            archive.close();raise ValueError("oversized workbook relationships")
        try:
            relationships=ET.fromstring(archive.read(member.filename))
        except (ET.ParseError,zipfile.BadZipFile) as exc:
            archive.close();raise ValueError("malformed workbook relationships") from exc
        for link in relationships.findall(f"{{{PKG}}}Relationship"):
            target=link.attrib.get("Target","").strip().lower()
            if (link.attrib.get("TargetMode")=="External" or
                    target.startswith(("http:","https:","ftp:","file:","mailto:"))):
                archive.close();raise ValueError("external relationships are not supported")
    return archive

def _read_xml(archive,name,limit=MAX_UNCOMPRESSED):
    if name not in archive.namelist():raise ValueError("missing workbook package part")
    info=archive.getinfo(name)
    if info.file_size>limit:raise ValueError("workbook XML part too large")
    try:
        data=archive.read(name)
        return ET.fromstring(data)
    except (ET.ParseError,RuntimeError,zipfile.BadZipFile) as exc:
        raise ValueError("malformed workbook XML") from exc

def _shared_strings(archive):
    if "xl/sharedStrings.xml" not in archive.namelist():return []
    root=_read_xml(archive,"xl/sharedStrings.xml",MAX_SHARED_BYTES)
    strings=[]
    for entry in root.findall(f"{{{MAIN}}}si"):
        if len(strings)>=MAX_STRINGS:raise ValueError("too many shared strings")
        text="".join(node.text or "" for node in entry.iter(f"{{{MAIN}}}t"))
        if len(text)>20000:raise ValueError("single cell text is too long")
        strings.append(text)
    return strings

def _sheet_path(archive,sheet_name):
    root=_read_xml(archive,"xl/workbook.xml",2_000_000)
    sheets=root.findall(f".//{{{MAIN}}}sheets/{{{MAIN}}}sheet")
    if not sheets:raise ValueError("workbook has no worksheets")
    if sheet_name is None:
        if len(sheets)!=1:
            raise ValueError("multiple worksheets: select one explicitly by name")
        selected=sheets[0]
    else:
        matched=[s for s in sheets if s.attrib.get("name")==sheet_name]
        if len(matched)!=1:raise ValueError("requested worksheet not found")
        selected=matched[0]
    if selected.attrib.get("state","visible")!="visible":
        raise ValueError("hidden worksheets are not supported")
    relation=selected.attrib.get(f"{{{REL}}}id")
    if not relation:raise ValueError("worksheet relationship missing")
    relations=_read_xml(archive,"xl/_rels/workbook.xml.rels",2_000_000)
    candidates=[
        r for r in relations.findall(f"{{{PKG}}}Relationship")
        if r.attrib.get("Id")==relation
    ]
    if len(candidates)!=1 or candidates[0].attrib.get("TargetMode")=="External":
        raise ValueError("ambiguous or external worksheet relationship")
    target=candidates[0].attrib.get("Target","")
    normalized=posixpath.normpath(
        target.lstrip("/") if target.startswith("/xl/") else posixpath.join("xl",target))
    if not normalized.startswith("xl/worksheets/") or normalized not in archive.namelist():
        raise ValueError("worksheet path outside supported package")
    return normalized

def _column_number(letters):
    value=0
    for letter in letters:
        value=value*26+(ord(letter)-64)
    return value

def _cell_text(cell,strings):
    if cell.find(f"{{{MAIN}}}f") is not None:
        raise ValueError("formula cell not supported")
    kind=cell.attrib.get("t","n")
    # Excel encodes dates as plain numbers with a date formatting style.
    # This restricted reader deliberately refuses styled numeric values
    # rather than mistaking a date serial for stock or a unit price.
    if kind=="n" and cell.attrib.get("s","0")!="0":
        raise ValueError("styled numeric/date cells require CSV conversion")
    if kind in ("b","e","d"):
        raise ValueError("boolean, error and date cell types are unsupported")
    if kind=="inlineStr":
        text="".join(t.text or "" for t in cell.iter(f"{{{MAIN}}}t"))
    else:
        field=cell.find(f"{{{MAIN}}}v")
        text=field.text if field is not None and field.text is not None else ""
        if kind=="s":
            try:
                index=int(text)
                if index<0:raise ValueError()
                text=strings[index]
            except (ValueError,IndexError):
                raise ValueError("invalid shared string reference")
        elif kind not in ("n","str"):
            raise ValueError("unsupported cell representation")
    if len(text)>20000:
        raise ValueError("cell text is too long")
    return text

def _rows(archive,sheet_name):
    strings=_shared_strings(archive)
    sheet=_read_xml(archive,_sheet_path(archive,sheet_name),32_000_000)
    if (sheet.find(f"{{{MAIN}}}mergeCells") is not None or
            sheet.find(f"{{{MAIN}}}tableParts") is not None):
        raise ValueError("merged cells and linked tables are unsupported")
    for column in sheet.findall(f".//{{{MAIN}}}cols/{{{MAIN}}}col"):
        if column.attrib.get("hidden")=="1":
            raise ValueError("hidden columns are not supported")
    if (sheet.find(f"{{{MAIN}}}hyperlinks") is not None or
            sheet.find(f"{{{MAIN}}}drawing") is not None):
        raise ValueError("linked or embedded sheet content not supported")
    data=sheet.find(f"{{{MAIN}}}sheetData")
    if data is None:raise ValueError("worksheet has no rows")
    records=[]
    previous=0
    for row in data.findall(f"{{{MAIN}}}row"):
        if row.attrib.get("hidden")=="1":
            raise ValueError("hidden worksheet rows are not supported")
        index=int(row.attrib.get("r",str(previous+1)))
        if index<=previous or index>MAX_ROWS+1:
            raise ValueError("invalid or duplicate row reference")
        previous=index
        values={}
        cell_types={}
        for cell in row.findall(f"{{{MAIN}}}c"):
            ref=cell.attrib.get("r","")
            match=CELL_REF.fullmatch(ref)
            if not match or int(match.group(2))!=index:
                raise ValueError("invalid cell reference")
            column=_column_number(match.group(1))
            if column>MAX_COLUMNS or column in values:
                raise ValueError("unexpected or duplicate worksheet column")
            values[column]=_cell_text(cell,strings)
            cell_types[column]=cell.attrib.get("t","n")
        if values:records.append((index,values,cell_types))
        if len(records)>MAX_ROWS+1:raise ValueError("too many rows")
    if not records or records[0][0]!=1:
        raise ValueError("first worksheet row must contain headers")
    headers=records[0][1]
    if not headers or 1 not in headers:raise ValueError("missing first header")
    max_col=max(headers)
    if set(headers)!=set(range(1,max_col+1)):
        raise ValueError("headers must occupy adjacent columns")
    names=[headers[i].strip().lower() for i in range(1,max_col+1)]
    if len(names)!=len(set(names)) or not set(names)<=FIELDS or "sku" not in names:
        raise ValueError("unsupported or duplicate headers")
    sku_column=names.index("sku")+1
    converted=[]
    for index,cells,types in records[1:]:
        if index<=1:continue
        if any(column>max_col for column in cells):
            raise ValueError("data found outside header columns")
        # Numeric identifiers can lose leading zeros before V3 receives them.
        # A named SKU must be stored as text in the workbook.
        if sku_column in cells and types.get(sku_column)=="n":
            raise ValueError("SKU cells must be stored as text, not numbers")
        converted.append({name:cells.get(column,"")
                          for column,name in enumerate(names,1)})
    if not converted:raise ValueError("worksheet has no data")
    return names,converted

def convert(source,destination,*,baseline=False,sheet=None):
    """Produce canonical CSV only after all workbook guards and engine checks."""
    destination=Path(destination)
    if destination.exists():raise ValueError("destination already exists")
    with _safe_zip(source) as archive:
        headers,rows=_rows(archive,sheet)
    if baseline and set(headers)!=FIELDS:
        raise ValueError("baseline must contain all canonical fields")
    destination.parent.mkdir(parents=True,exist_ok=True)
    temp_path=None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",encoding="utf-8",newline="",suffix=".csv",
            prefix=".xlsx-normalized-",dir=destination.parent,delete=False
        ) as output:
            temp_path=Path(output.name)
            writer=csv.DictWriter(output,fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        verified,fields=engine.load(temp_path)
        if baseline:
            seen=set()
            for _,row in verified:
                sku=row["sku"].strip()
                if not sku or sku in seen:raise ValueError("invalid or duplicate baseline SKU")
                seen.add(sku)
                engine.price(row["price"])
                engine.stock(row["stock"])
        os.link(temp_path,destination)
        return {"path":str(destination),"rows":len(verified),
                "sha256":engine.digest(destination),
                "fields":fields,"source_type":"restricted_xlsx"}
    finally:
        if temp_path is not None:temp_path.unlink(missing_ok=True)

def main():
    p=argparse.ArgumentParser(description="Restricted synthetic XLSX -> V3 CSV")
    p.add_argument("source")
    p.add_argument("destination")
    p.add_argument("--baseline",action="store_true")
    p.add_argument("--sheet")
    args=p.parse_args()
    print(json.dumps(convert(args.source,args.destination,baseline=args.baseline,
                             sheet=args.sheet),indent=2))
if __name__=="__main__":main()
