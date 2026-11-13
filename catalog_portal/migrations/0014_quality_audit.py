from django.db import migrations,models
class Migration(migrations.Migration):
    dependencies=[("catalog_portal","0013_customer_issues")]
    operations=[migrations.AlterField(
        model_name="catalogevent",name="kind",
        field=models.CharField(max_length=20,choices=[
            ("submitted","Submitted"),("processed","Processed"),
            ("failed","Failed"),("approved","Approved"),("rejected","Rejected"),
            ("exported","Exported"),("downloaded","Downloaded"),
            ("source_purged","Source purged"),("hold_excluded","Hold excluded"),
            ("advisory","Advisory"),("retry_requested","Retry requested"),
            ("import_confirmed","Import confirmed"),("issue_opened","Issue opened"),
            ("issue_resolved","Issue resolved")
        ]),
    )]
