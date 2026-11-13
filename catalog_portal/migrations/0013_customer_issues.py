import uuid
from django.conf import settings
from django.db import migrations,models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog_portal","0012_import_confirmation_event"),
    ]
    operations=[migrations.CreateModel(
        name="CustomerIssue",
        fields=[
            ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,
                                   serialize=False)),
            ("subject",models.CharField(max_length=120)),
            ("message",models.CharField(max_length=500)),
            ("status",models.CharField(choices=[
                ("open","Open"),("resolved","Resolved")],default="open",max_length=15)),
            ("resolution",models.CharField(blank=True,max_length=500)),
            ("created_at",models.DateTimeField(auto_now_add=True)),
            ("resolved_at",models.DateTimeField(blank=True,null=True)),
            ("job",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                     related_name="catalog_issues",
                                     to="catalog_portal.catalogjob")),
            ("store",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                       related_name="catalog_issues",
                                       to="catalog_portal.store")),
            ("opened_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                related_name="opened_catalog_issues",to=settings.AUTH_USER_MODEL)),
            ("resolved_by",models.ForeignKey(blank=True,null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="resolved_catalog_issues",to=settings.AUTH_USER_MODEL)),
        ],
        options={"indexes":[models.Index(fields=["store","status","created_at"],
                                           name="v3issue_status_idx")]},
    )]
