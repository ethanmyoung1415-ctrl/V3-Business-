import uuid
from django.db import migrations,models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[("catalog_portal","0005_hold_excluded")]
    operations=[
        migrations.CreateModel(
            name="SupplierProfile",
            fields=[
                ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
                ("name",models.CharField(max_length=120)),
                ("mapping",models.JSONField(default=dict)),
                ("active",models.BooleanField(default=True)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("store",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                          related_name="supplier_profiles",to="catalog_portal.store")),
            ],
        ),
        migrations.AddField(
            model_name="catalogjob",name="mapping_snapshot",
            field=models.JSONField(blank=True,default=dict,editable=False)),
        migrations.AddConstraint(
            model_name="supplierprofile",
            constraint=models.UniqueConstraint(fields=("store","name"),
                                               name="unique_supplier_profile_store_name")),
    ]
