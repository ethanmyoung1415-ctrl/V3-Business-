# Restricted Excel (.xlsx) intake — synthetic local demonstration

V3 now accepts simple XLSX input through the local customer portal as well as
standard CSV. Excel is converted to a separate, canonical CSV snapshot for the
engine. The original XLSX upload remains private and SHA-256 hashed in the
job record.

This is a deliberately **restricted importer**, not a full-featured Excel
calculation or spreadsheet-editing application.

## Supported
- Unencrypted `.xlsx` ZIP packages containing one unambiguous visible worksheet
- Standard canonical V3 headings (`sku`, `title`, `price`, `stock`)
- Standard text/shared-string and unstyled numeric cell values
- Valid stock `0`; it remains an approval-required proposed update
- Mixed inputs such as baseline CSV and supplier XLSX
- Up to 100,000 rows and 12 columns, subject to file-size and ZIP safety limits
- Optional CLI selection of a named sheet in a multi-sheet workbook; **portal users must supply a single-sheet workbook**

## Explicitly rejected
- Legacy `.xls`, macro-enabled `.xlsm`, encrypted workbooks
- Formulas, even when Excel provides cached formula results
- External relationships, linked tables, embedded objects, macros or connections
- Hidden rows/columns/sheets, merged ranges and styled numeric/date cells
- Multi-sheet uploads through the portal (avoid guessing which is authoritative)
- Unsupported column names, duplicate headings and unsafe spreadsheet text
- Archives violating ZIP size/decompression limits or containing unsafe package paths
- Supplier header mappings combined with XLSX; use a pre-approved CSV mapping instead

## Command-line demonstration
```bash
python xlsx_intake.py supplier.xlsx clean_supplier.csv
python xlsx_intake.py baseline.xlsx clean_baseline.csv --baseline
python xlsx_intake.py multi_sheet.xlsx output.csv --sheet "Inventory"
```

The output is never overwritten. After conversion, the normal V3 CSV rules
apply and any suspicious supplier records are held, not silently imported.

## Local portal
The customer upload form accepts CSV and simple single-sheet XLSX files. The
portal checks the workbook before saving, records source hashes, stages
immutable originals, and processes only the validated canonical CSV. The
operator must still approve changes before independently verified export.

## Limitations and next steps
Real supplier workbooks commonly contain formatted numeric cells, extra sheets,
tables, hyperlinks and inconsistent formats. This restricted implementation
rejects them by design. For those files, export a reviewed plain CSV or obtain
technical approval for a fuller parsing architecture and representative
supplier fixtures.

There is no proof of safe processing for arbitrary XLSX files. Additional
fuzz testing, resource-limit tests, malware scanning, professional security
review and authorized infrastructure remain prerequisites for real customer
files. Do not use this importer with real customer data.
