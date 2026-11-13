import uuid
from django.conf import settings
from django.db import migrations,models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog_portal","0009_retry_audit"),
    ]
    operations=[
        migrations.CreateModel(
            name="PortalNotice",
            fields=[
                ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
                ("kind",models.CharField(choices=[
                    ("needs_review","Needs review"),("job_failed","Job failed"),
                    ("export_ready","Export ready")],max_length=30)),
                ("audience",models.CharField(choices=[
                    ("operator","Operator"),("customer","Customer")],max_length=20)),
                ("dedupe_key",models.CharField(max_length=120,unique=True)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("job",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                        related_name="notices",to="catalog_portal.catalogjob")),
                ("store",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                          related_name="notices",to="catalog_portal.store")),
            ],
            options={"indexes":[models.Index(fields=["store","audience","created_at"],
                                              name="v3notice_audience_idx")]},
        ),
        migrations.CreateModel(
            name="NoticeRead",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,
                                          serialize=False,verbose_name="ID")),
                ("read_at",models.DateTimeField(auto_now_add=True)),
                ("notice",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                            related_name="read_receipts",to="catalog_portal.portalnotice")),
                ("user",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                          to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="noticeread",
            constraint=models.UniqueConstraint(fields=("notice","user"),
                                               name="unique_notice_read_user")),
    ]
