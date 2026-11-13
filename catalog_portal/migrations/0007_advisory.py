from django.db import migrations,models
class Migration(migrations.Migration):
    dependencies=[("catalog_portal","0006_supplier_profiles")]
    operations=[
        migrations.AlterField(
            model_name="catalogevent",name="kind",
            field=models.CharField(max_length=20,choices=[
                ("submitted","Submitted"),("processed","Processed"),
                ("failed","Failed"),("approved","Approved"),("rejected","Rejected"),
                ("exported","Exported"),("downloaded","Downloaded"),
                ("source_purged","Source purged"),("hold_excluded","Hold excluded"),
                ("advisory","Advisory")
            ]),
        ),
    ]
