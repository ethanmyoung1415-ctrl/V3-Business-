from django.db import migrations,models
class Migration(migrations.Migration):
    dependencies=[("catalog_portal","0007_advisory")]
    operations=[
        migrations.AddField(
            model_name="catalogjob",name="baseline_sha256",
            field=models.CharField(max_length=64,blank=True,editable=False)),
        migrations.AddField(
            model_name="catalogjob",name="supplier_sha256",
            field=models.CharField(max_length=64,blank=True,editable=False)),
    ]
