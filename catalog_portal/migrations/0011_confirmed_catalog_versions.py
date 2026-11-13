from django.conf import settings
from django.db import migrations,models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog_portal","0010_notices"),
    ]
    operations=[
        migrations.AddField(
            model_name="catalogjob",name="baseline_source_job",
            field=models.ForeignKey(blank=True,editable=False,null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="derived_catalog_jobs",to="catalog_portal.catalogjob")),
        migrations.CreateModel(
            name="CatalogConfirmation",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,
                                          serialize=False,verbose_name="ID")),
                ("confirmed_at",models.DateTimeField(auto_now_add=True)),
                ("export_sha256",models.CharField(max_length=64)),
                ("confirmed_by",models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to=settings.AUTH_USER_MODEL)),
                ("job",models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,
                    related_name="confirmed_import",to="catalog_portal.catalogjob")),
                ("store",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="confirmed_imports",to="catalog_portal.store")),
            ],
        ),
    ]
