import csv
import io
from django import forms
from .models import CatalogJob

LIMIT=15_000_000
ALLOWED={"sku","title","price","stock"}

def validate_csv(upload,baseline=False):
    if not upload.name.lower().endswith(".csv"):
        raise forms.ValidationError("Only CSV files are supported")
    if upload.size<=0 or upload.size>LIMIT:
        raise forms.ValidationError("CSV file must be between 1 byte and 15 MB")
    try:
        contents=upload.read(LIMIT+1)
        if len(contents)>LIMIT:raise ValueError("file too large")
        text=contents.decode("utf-8-sig")
        reader=csv.DictReader(io.StringIO(text))
        fields=reader.fieldnames
        if not fields:raise ValueError("missing header")
        fields=[x.strip().lower() for x in fields]
        if len(fields)!=len(set(fields)) or not set(fields)<=ALLOWED or "sku" not in fields:
            raise ValueError("unsupported or duplicate columns")
        if baseline and set(fields)!=ALLOWED:
            raise ValueError("baseline requires sku, title, price and stock")
        count=0
        for count,row in enumerate(reader,1):
            if count>100000:raise ValueError("too many rows")
            if None in row or any(v is None for v in row.values()):
                raise ValueError("malformed CSV row")
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
