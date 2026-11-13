"""Explicit source-field mapping for fictional supplier CSVs.

A provider's spreadsheet column names are untrusted. Operators must supply an
unambiguous exact mapping; this tool never guesses about price, stock or SKU.
All source values are validated by engine.load after canonicalization.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import tempfile
import engine

FIELDS=frozenset(engine.FIELDS)

def validate_mapping(mapping,baseline=False):
    if not isinstance(mapping,dict) or not mapping:
        raise ValueError("field mapping must be an object")
    if set(mapping)-FIELDS:
        raise ValueError("field mapping contains unsupported canonical field")
    required=FIELDS if baseline else {"sku"}
    if not required.issubset(mapping):
        raise ValueError("required canonical fields not mapped")
    labels=list(mapping.values())
    if any(not isinstance(label,str) or not label.strip() or len(label)>120
           for label in labels):
        raise ValueError("source column names must be nonblank strings")
    if len(set(labels))!=len(labels):
        raise ValueError("two canonical fields cannot share one source column")
    return dict(mapping)

def normalize_csv(source,destination,mapping,baseline=False):
    """Create one immutable canonical CSV. Never overwrite existing files."""
    mapping=validate_mapping(mapping,baseline)
    source=Path(source)
    destination=Path(destination)
    if source.resolve()==destination.resolve():
        raise ValueError("source and destination cannot be the same")
    if not source.is_file() or source.stat().st_size>15_000_000:
        raise ValueError("source missing or exceeds size cap")
    if destination.exists():
        raise ValueError("destination exists")
    destination.parent.mkdir(parents=True,exist_ok=True)
    tmp_path=None
    try:
        with source.open(encoding="utf-8-sig",newline="") as input_file:
            reader=csv.DictReader(input_file,strict=True)
            if not reader.fieldnames:
                raise ValueError("missing source headers")
            if len(reader.fieldnames)!=len(set(reader.fieldnames)):
                raise ValueError("duplicate source headers")
            if not set(mapping.values()).issubset(reader.fieldnames):
                raise ValueError("source missing explicitly mapped columns")
            with tempfile.NamedTemporaryFile(
                mode="w",encoding="utf-8",newline="",prefix=".mapped-",
                suffix=".csv",dir=destination.parent,delete=False
            ) as out:
                tmp_path=Path(out.name)
                fields=[field for field in engine.FIELDS if field in mapping]
                writer=csv.DictWriter(out,fieldnames=fields)
                writer.writeheader()
                count=0
                for count,row in enumerate(reader,1):
                    if count>100000:
                        raise ValueError("too many rows")
                    if None in row or any(val is None for val in row.values()):
                        raise ValueError("malformed source record")
                    canonical={field:row[source_field] for field,source_field in
                               mapping.items()}
                    writer.writerow(canonical)
                if count==0:
                    raise ValueError("empty source")
        # Exactly the same validation the engine uses on supplier updates.
        rows,headers=engine.load(tmp_path)
        if baseline:
            if set(headers)!=FIELDS:raise ValueError("baseline fields missing")
            seen=set()
            for _,row in rows:
                sku=row["sku"].strip()
                if not sku or sku in seen:
                    raise ValueError("invalid or duplicate baseline SKU")
                seen.add(sku)
                engine.price(row["price"])
                engine.stock(row["stock"])
        os.replace(tmp_path,destination)
        return {"output":str(destination),"rows":len(rows),
                "sha256":engine.digest(destination),"fields":headers}
    except BaseException:
        if tmp_path is not None:tmp_path.unlink(missing_ok=True)
        raise

def main():
    parser=argparse.ArgumentParser(
        description="Explicitly map supplier headers into V3 canonical CSV")
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--mapping",required=True,
                        help="JSON object: canonical field to exact supplier heading")
    parser.add_argument("--baseline",action="store_true")
    args=parser.parse_args()
    result=normalize_csv(args.source,args.destination,json.loads(args.mapping),
                         baseline=args.baseline)
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
