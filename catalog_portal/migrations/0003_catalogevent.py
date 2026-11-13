from django.conf import settings
from django.db import migrations,models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog_portal","0002_engine_link"),
    ]
    operations=[
        migrations.CreateModel(
            name="CatalogEvent",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("kind",models.CharField(choices=[
                    ("submitted","Submitted"),("processed","Processed"),
                    ("failed","Failed"),("approved","Approved"),("rejected","Rejected"),
                    ("exported","Exported"),("downloaded","Downloaded")],max_length=20)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("detail",models.CharField(blank=True,max_length=180)),
                ("actor",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL)),
                ("job",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="portal_events",to="catalog_portal.catalogjob")),
            ],
            options={"indexes":[models.Index(fields=["job","created_at"],name="v3event_job_time_idx")]},
        ),
    ]
