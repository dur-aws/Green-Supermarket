from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0004_stockadjustment_adjusted_by_user_and_more'),
    ]

    operations = [
       
        migrations.AlterField(
            model_name='stockadjustment',
            name='reason_code',
            field=models.CharField(
                choices=[
                    ('EXPIRED', 'Stock Expired'),
                    ('DAMAGED', 'Damaged / Broken'),
                    ('THEFT', 'Stolen / Missing'),
                    ('CORRECTION', 'Inventory Audit Correction'),
                    ('RETURN', 'Returned Goods Adjustment'),
                    ('WASTAGE', 'Wastage'),
                ],
                max_length=20,
            ),
        ),
    ]
