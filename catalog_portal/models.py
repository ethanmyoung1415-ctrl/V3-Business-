"""Tenant-scoped intake records. No direct store-write feature exists."""
import uuid
from pathlib import Path
from django.conf import settings
from django.db import models

def private_upload_path(instance,filename):
    # Ignore the user-controlled name entirely.
    kind="baseline" if "baseline" in str(filename).lower() else "input"
    return f"private/{instance.store_id}/{instance.id}/{kind}-{uuid.uuid4()}.csv"

class Store(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=120)
    active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self):return self.name

class Membership(models.Model):
    ROLE_CUSTOMER="customer"
    ROLE_OPERATOR="operator"
    ROLE_CHOICES=[(ROLE_CUSTOMER,"Customer"),(ROLE_OPERATOR,"Operator")]
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="v3_memberships")
    store=models.ForeignKey(Store,on_delete=models.CASCADE,related_name="memberships")
    role=models.CharField(max_length=20,choices=ROLE_CHOICES,default=ROLE_CUSTOMER)
    class Meta:
        constraints=[models.UniqueConstraint(fields=("user","store"),name="unique_user_store_membership")]
    def __str__(self):return f"{self.user_id} in {self.store_id}"

class SupplierProfile(models.Model):
    """Operator-controlled exact supplier header mapping for one store."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    store=models.ForeignKey(Store,on_delete=models.CASCADE,related_name="supplier_profiles")
    name=models.CharField(max_length=120)
    mapping=models.JSONField(default=dict)
    active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=("store","name"),
                                              name="unique_supplier_profile_store_name")]
    def clean(self):
        from django.core.exceptions import ValidationError
        import mapping as mapper
        try:mapper.validate_mapping(self.mapping)
        except ValueError as exc:raise ValidationError({"mapping":str(exc)})
    def __str__(self):return self.name

class CatalogJob(models.Model):
    STATUS_RECEIVED="received"
    STATUS_PROCESSING="processing"
    STATUS_REVIEW="review"
    STATUS_FAILED="failed"
    STATUS_READY="ready"
    STATUSES=[(x,x.title()) for x in
              (STATUS_RECEIVED,STATUS_PROCESSING,STATUS_REVIEW,STATUS_FAILED,STATUS_READY)]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    store=models.ForeignKey(Store,on_delete=models.PROTECT,related_name="catalog_jobs")
    submitted_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    baseline=models.FileField(upload_to=private_upload_path,max_length=255)
    supplier_update=models.FileField(upload_to=private_upload_path,max_length=255)
    status=models.CharField(max_length=20,choices=STATUSES,default=STATUS_RECEIVED)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    error_code=models.CharField(max_length=60,blank=True)
    engine_job_id=models.UUIDField(null=True,blank=True,editable=False)
    export_sha256=models.CharField(max_length=64,blank=True,editable=False)
    mapping_snapshot=models.JSONField(default=dict,blank=True,editable=False)
    baseline_sha256=models.CharField(max_length=64,blank=True,editable=False)
    supplier_sha256=models.CharField(max_length=64,blank=True,editable=False)
    class Meta:
        indexes=[models.Index(fields=("store","created_at"),name="v3job_store_created_idx")]

class CatalogEvent(models.Model):
    """Metadata-only event trail; never put supplier CSV content in details."""
    TYPES=[
        ("submitted","Submitted"),("processed","Processed"),
        ("failed","Failed"),("approved","Approved"),("rejected","Rejected"),
        ("exported","Exported"),("downloaded","Downloaded"),("source_purged","Source purged"),("hold_excluded","Hold excluded"),("advisory","Advisory"),("retry_requested","Retry requested"),
    ]
    job=models.ForeignKey(CatalogJob,on_delete=models.CASCADE,related_name="portal_events")
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,
                            null=True,blank=True)
    kind=models.CharField(max_length=20,choices=TYPES)
    created_at=models.DateTimeField(auto_now_add=True)
    detail=models.CharField(max_length=180,blank=True)
    class Meta:
        indexes=[models.Index(fields=("job","created_at"),name="v3event_job_time_idx")]
