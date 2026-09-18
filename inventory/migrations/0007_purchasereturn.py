import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounting', '0006_remove_fiscalyear_bs_year_remove_fiscalyear_end_date_and_more'),
        ('inventory', '0006_alter_stockadjustment_adjusted_by_user'),
        ('purchases', '0003_purchaseorder_journal_entry'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PurchaseReturn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=3, max_digits=10)),
                ('unit_cost', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_value', models.DecimalField(decimal_places=2, max_digits=12)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_returns', to='inventory.inventorybatch')),
                ('journal_entry', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='accounting.journalentry')),
                ('purchase_order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_returns', to='purchases.purchaseorder')),
                ('returned_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('stock_adjustment', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_return', to='inventory.stockadjustment')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]