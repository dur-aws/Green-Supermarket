import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0004_rename_payment_id_payment_transaction_id_and_more'),
        ('purchases', '0004_purchaseorder_freight_and_settlement'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='sale',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payment_transactions', to='sales.sale'),
        ),
        migrations.AddField(
            model_name='payment',
            name='purchase',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='purchase_payments', to='purchases.purchaseorder'),
        ),
    ]
