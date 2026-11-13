from django.db import migrations,models
class Migration(migrations.Migration):
    dependencies=[("catalog_portal","0001_initial")]
    operations=[
        migrations.AddField(
            model_name="catalogjob",name="engine_job_id",
            field=models.UUIDField(blank=True,editable=False,null=True)),
        migrations.AddField(
            model_name="catalogjob",name="export_sha256",
            field=models.CharField(blank=True,editable=False,max_length=64)),
    ]
