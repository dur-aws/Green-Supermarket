from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('purchases', '0005_alter_purchaseorder_due_amount_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='purchaseorder',
            name='order_status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('ACCEPTED', 'Accepted'),
                    ('DELIVERED', 'Delivered by supplier'),
                    ('RECEIVED', 'Received'),
                    ('CANCELLED', 'Cancelled'),
                ],
                default='PENDING',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='purchasedetail',
            name='supplier_response',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('ACCEPT', 'Accept'),
                    ('NOT_AVAILABLE', 'Not available'),
                ],
                default='PENDING',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='purchasedetail',
            name='supplier_responded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='VendorPurchaseReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('receipt_number', models.CharField(max_length=50, unique=True)),
                ('issued_at', models.DateTimeField(auto_now_add=True)),
                ('generated_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='vendor_receipts', to=settings.AUTH_USER_MODEL)),
                ('purchase', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='vendor_receipt', to='purchases.purchaseorder')),
            ],
            options={'ordering': ['-issued_at']},
        ),
    ]
