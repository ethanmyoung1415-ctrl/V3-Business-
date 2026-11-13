import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import catalog_portal.models

class Migration(migrations.Migration):
    initial=True
    dependencies=[migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(
            name="Store",
            fields=[
                ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
                ("name",models.CharField(max_length=120)),
                ("active",models.BooleanField(default=True)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("role",models.CharField(choices=[("customer","Customer"),("operator","Operator")],default="customer",max_length=20)),
                ("store",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="memberships",to="catalog_portal.store")),
                ("user",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="v3_memberships",to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="CatalogJob",
            fields=[
                ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
                ("baseline",models.FileField(max_length=255,upload_to=catalog_portal.models.private_upload_path)),
                ("supplier_update",models.FileField(max_length=255,upload_to=catalog_portal.models.private_upload_path)),
                ("status",models.CharField(choices=[("received","Received"),("processing","Processing"),("review","Review"),("failed","Failed"),("ready","Ready")],default="received",max_length=20)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("updated_at",models.DateTimeField(auto_now=True)),
                ("error_code",models.CharField(blank=True,max_length=60)),
                ("store",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="catalog_jobs",to="catalog_portal.store")),
                ("submitted_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to=settings.AUTH_USER_MODEL)),
            ],
            options={"indexes":[models.Index(fields=["store","created_at"],name="v3job_store_created_idx")]},
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(fields=("user","store"),name="unique_user_store_membership"),
        ),
    ]
