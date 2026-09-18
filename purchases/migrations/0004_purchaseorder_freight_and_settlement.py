from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('purchases', '0003_purchaseorder_journal_entry'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseorder',
            name='freight_charge',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='paid_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='due_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
