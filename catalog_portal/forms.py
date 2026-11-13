"""Tenant-limited catalog upload validation and explicit supplier mappings."""
import csv
import io
from django import forms
import engine
import mapping as mapper
from .models import CatalogJob,SupplierProfile

LIMIT=15_000_000
ALLOWED=set(engine.FIELDS)
DANGEROUS_PREFIX=("=","+","-","@")
CONTROL_CHARS=("\x00","\t","\r","\n")

def validate_csv(upload,baseline=False,mapping=None):
    if not upload.name.lower().endswith(".csv"):
        raise forms.ValidationError("Only CSV files are supported")
    if upload.size<=0 or upload.size>LIMIT:
        raise forms.ValidationError("CSV file must be between 1 byte and 15 MB")
    try:
        contents=upload.read(LIMIT+1)
        if len(contents)>LIMIT:raise ValueError("file too large")
        text=contents.decode("utf-8-sig")
        reader=csv.DictReader(io.StringIO(text,newline=""),strict=True)
        raw_fields=reader.fieldnames
        if not raw_fields:raise ValueError("missing header")
        if len(raw_fields)!=len(set(raw_fields)):
            raise ValueError("duplicate source column")
        if mapping is not None:
            spec=mapper.validate_mapping(mapping,baseline=baseline)
            if not set(spec.values()).issubset(raw_fields):
                raise ValueError("source does not contain required mapped columns")
        else:
            normalized=[name.strip().lower() for name in raw_fields]
            if (len(normalized)!=len(set(normalized)) or
                    not set(normalized)<=ALLOWED or "sku" not in normalized):
                raise ValueError("unsupported or duplicate columns")
            if baseline and set(normalized)!=ALLOWED:
                raise ValueError("baseline requires sku, title, price and stock")
            spec={name:name_orig for name,name_orig in zip(normalized,raw_fields)}
        seen=set()
        count=0
        for count,row in enumerate(reader,1):
            if count>100000:raise ValueError("too many rows")
            if None in row or any(v is None for v in row.values()):
                raise ValueError("malformed CSV row")
            cleaned={field:row[column] for field,column in spec.items()}
            sku=cleaned["sku"].strip()
            if not sku:raise ValueError("blank SKU")
            for field in ("sku","title"):
                value=cleaned.get(field,"")
                if (value.lstrip().startswith(DANGEROUS_PREFIX) or
                        any(ch in value for ch in CONTROL_CHARS)):
                    raise ValueError(f"unsafe spreadsheet text in {field}")
            if baseline:
                if sku in seen:raise ValueError("duplicate baseline SKU")
                seen.add(sku)
            for field,validate in (("price",engine.price),("stock",engine.stock)):
                if field not in cleaned:continue
                if baseline or cleaned[field].strip():
                    validate(cleaned[field])
        if count==0:raise ValueError("empty catalog")
    except (UnicodeDecodeError,csv.Error,ValueError) as ex:
        raise forms.ValidationError("Invalid CSV: %(reason)s",params={"reason":str(ex)})
    finally:
        upload.seek(0)
    return upload

class JobForm(forms.ModelForm):
    supplier_profile=forms.ModelChoiceField(
        queryset=SupplierProfile.objects.none(),required=False,
        empty_label="Standard V3 columns (no mapping)",
        help_text="Choose an approved supplier header mapping for this store.")
    class Meta:
        model=CatalogJob
        fields=["baseline","supplier_update"]
    def __init__(self,*args,store=None,**kwargs):
        if store is None:
            raise ValueError("a store context is required")
        super().__init__(*args,**kwargs)
        self.fields["supplier_profile"].queryset=SupplierProfile.objects.filter(
            store=store,active=True)
    def clean_baseline(self):
        return validate_csv(self.cleaned_data["baseline"],baseline=True)
    def clean(self):
        data=super().clean()
        update=data.get("supplier_update")
        profile=data.get("supplier_profile")
        if update is not None:
            try:
                validate_csv(update,mapping=profile.mapping if profile else None)
            except forms.ValidationError as exc:
                self.add_error("supplier_update",exc)
        return data
