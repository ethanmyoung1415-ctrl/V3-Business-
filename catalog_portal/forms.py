"""Preproduction CSV upload checks. These mirror engine rules at intake."""
import csv
import io
from django import forms
import engine
from .models import CatalogJob

LIMIT=15_000_000
ALLOWED={"sku","title","price","stock"}
DANGEROUS_PREFIX=("=","+","-","@")
CONTROL_CHARS=("\x00","\t","\r","\n")

def validate_csv(upload,baseline=False):
    if not upload.name.lower().endswith(".csv"):
        raise forms.ValidationError("Only CSV files are supported")
    if upload.size<=0 or upload.size>LIMIT:
        raise forms.ValidationError("CSV file must be between 1 byte and 15 MB")
    try:
        contents=upload.read(LIMIT+1)
        if len(contents)>LIMIT:raise ValueError("file too large")
        text=contents.decode("utf-8-sig")
        reader=csv.DictReader(io.StringIO(text,newline=""),strict=True)
        fields=reader.fieldnames
        if not fields:raise ValueError("missing header")
        normalized=[name.strip().lower() for name in fields]
        if len(normalized)!=len(set(normalized)) or not set(normalized)<=ALLOWED or "sku" not in normalized:
            raise ValueError("unsupported or duplicate columns")
        if baseline and set(normalized)!=ALLOWED:
            raise ValueError("baseline requires sku, title, price and stock")
        seen=set()
        count=0
        for count,row in enumerate(reader,1):
            if count>100000:raise ValueError("too many rows")
            if None in row or any(v is None for v in row.values()):
                raise ValueError("malformed CSV row")
            cleaned={key.strip().lower():value for key,value in row.items()}
            sku=cleaned["sku"].strip()
            if not sku:
                raise ValueError("blank SKU")
            for field in ("sku","title"):
                value=cleaned.get(field,"")
                if value.lstrip().startswith(DANGEROUS_PREFIX) or any(ch in value for ch in CONTROL_CHARS):
                    raise ValueError(f"unsafe spreadsheet text in {field}")
            if baseline:
                if sku in seen:raise ValueError("duplicate baseline SKU")
                seen.add(sku)
                # Prevent partial acceptance: anything that would make the
                # baseline unprocessable is rejected at the upload boundary.
                engine.price(cleaned["price"])
                engine.stock(cleaned["stock"])
            else:
                # Updates with empty values remain valid inputs but are HELD
                # by the engine; don't turn valid empty/zero stock into a blank.
                for field,validator in (("price",engine.price),("stock",engine.stock)):
                    if field in cleaned and cleaned[field].strip():
                        validator(cleaned[field])
        if count==0:raise ValueError("empty catalog")
    except (UnicodeDecodeError,csv.Error,ValueError) as ex:
        raise forms.ValidationError("Invalid CSV: %(reason)s",params={"reason":str(ex)})
    finally:
        upload.seek(0)
    return upload

class JobForm(forms.ModelForm):
    class Meta:
        model=CatalogJob
        fields=["baseline","supplier_update"]
    def clean_baseline(self):
        return validate_csv(self.cleaned_data["baseline"],baseline=True)
    def clean_supplier_update(self):
        return validate_csv(self.cleaned_data["supplier_update"],baseline=False)
