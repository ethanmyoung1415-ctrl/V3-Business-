from django.conf import settings
from django.db import migrations,models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    dependencies=[
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog_portal","0014_quality_audit"),
    ]
    operations=[
        migrations.CreateModel(
            name="StoreInvitation",
            fields=[
                ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
                ("token_sha256",models.CharField(unique=True,max_length=64)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("expires_at",models.DateTimeField()),
                ("redeemed_at",models.DateTimeField(blank=True,null=True)),
                ("store",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="local_invitations",to="catalog_portal.store")),
                ("created_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="issued_v3_invitations",to=settings.AUTH_USER_MODEL)),
                ("redeemed_by",models.ForeignKey(blank=True,null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="redeemed_v3_invitations",to=settings.AUTH_USER_MODEL)),
            ],
            options={"indexes":[models.Index(fields=["store","expires_at"],
                       name="v3invite_store_expiry_idx")]},
        ),
    ]
