from django.db import migrations,models

class Migration(migrations.Migration):
    dependencies=[("catalog_portal","0003_catalogevent")]
    operations=[
        migrations.AlterField(
            model_name="catalogevent",name="kind",
            field=models.CharField(choices=[
                ("submitted","Submitted"),("processed","Processed"),
                ("failed","Failed"),("approved","Approved"),("rejected","Rejected"),
                ("exported","Exported"),("downloaded","Downloaded"),
                ("source_purged","Source purged")],max_length=20),
        ),
    ]
