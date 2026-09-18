import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0005_purchase_payment'),
        ('sales', '0005_sales_return_workflow'),
        ('accounting', '0007_paymentreceipt_supplier'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentrefund',
            name='credit_memo',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='payment_refund', to='sales.creditmemo'),
        ),
        migrations.AddField(
            model_name='paymentrefund',
            name='refund_method',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='paymentrefund',
            name='confirmed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='confirmed_refunds', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='paymentrefund',
            name='confirmed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='paymentrefund',
            name='journal_entry',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='refund_records', to='accounting.journalentry'),
        ),
        migrations.AlterField(
            model_name='paymentrefund',
            name='status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('SUCCESS', 'Success'), ('FAILED', 'Failed'), ('PAID', 'Paid'), ('COMPLETED', 'Completed')], default='PENDING', max_length=20),
        ),
    ]
