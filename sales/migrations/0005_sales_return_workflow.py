from decimal import Decimal
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0004_rename_customer_pan_sale_buyer_pan_and_more'),
        ('accounting', '0007_paymentreceipt_supplier'),
        ('customers', '0001_initial'),
        ('inventory', '0001_initial'),
        ('products', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SalesReturn',
            fields=[
                ('rma_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('rma_number', models.CharField(default='', max_length=32, unique=True)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('RECEIVED', 'Received'), ('INSPECTED', 'Inspected'), ('APPROVED', 'Approved'), ('CREDITED', 'Credited'), ('REFUNDED', 'Refunded'), ('CANCELLED', 'Cancelled')], db_index=True, default='DRAFT', max_length=20)),
                ('reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('received_at', models.DateTimeField(blank=True, null=True)),
                ('inspected_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_rmas', to=settings.AUTH_USER_MODEL)),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='customers.customer')),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='return_requests', to='sales.sale')),
            ],
        ),
        migrations.CreateModel(
            name='InventoryReturnReceipt',
            fields=[
                ('receipt_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('receipt_number', models.CharField(default='', max_length=32, unique=True)),
                ('status', models.CharField(choices=[('APPROVED', 'Approved'), ('VOID', 'Void')], default='APPROVED', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('inspected_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='inspected_return_receipts', to=settings.AUTH_USER_MODEL)),
                ('received_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='received_return_receipts', to=settings.AUTH_USER_MODEL)),
                ('rma', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='inventory_receipt', to='sales.salesreturn')),
            ],
        ),
        migrations.CreateModel(
            name='CreditMemo',
            fields=[
                ('memo_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('memo_number', models.CharField(default='', max_length=32, unique=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('status', models.CharField(choices=[('APPROVED', 'Approved'), ('PENDING_REFUND', 'Pending Refund'), ('PAID', 'Paid'), ('COMPLETED', 'Completed')], default='APPROVED', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_credit_memos', to=settings.AUTH_USER_MODEL)),
                ('journal_entry', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='credit_memos', to='accounting.journalentry')),
                ('receipt', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='credit_memo', to='sales.inventoryreturnreceipt')),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='credit_memos', to='sales.sale')),
            ],
        ),
        migrations.CreateModel(
            name='SalesReturnItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_requested', models.DecimalField(decimal_places=3, max_digits=10)),
                ('quantity_received', models.DecimalField(decimal_places=3, default=Decimal('0.000'), max_digits=10)),
                ('unit_refund_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('rma', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='sales.salesreturn')),
                ('sale_item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='return_items', to='sales.saleitem')),
                ('source_batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='inventory.inventorybatch')),
            ],
        ),
        migrations.CreateModel(
            name='InventoryReturnItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('condition', models.CharField(choices=[('RESALABLE', 'Resalable'), ('DAMAGED', 'Damaged'), ('EXPIRED', 'Expired')], max_length=10)),
                ('quantity', models.DecimalField(decimal_places=3, max_digits=10)),
                ('unit_cost', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('disposition_note', models.TextField(blank=True)),
                ('receipt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='sales.inventoryreturnreceipt')),
                ('return_item', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='receipt_item', to='sales.salesreturnitem')),
                ('target_batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='returned_stock', to='inventory.inventorybatch')),
            ],
        ),
        migrations.AddConstraint(
            model_name='salesreturnitem',
            constraint=models.UniqueConstraint(fields=('rma', 'sale_item'), name='unique_rma_sale_item'),
        ),
    ]
