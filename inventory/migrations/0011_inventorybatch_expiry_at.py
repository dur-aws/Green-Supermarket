from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0010_inventorybatch_batch_no_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventorybatch',
            name='expiry_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
