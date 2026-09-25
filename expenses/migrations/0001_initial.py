from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounting', '0009_rebuild_chart_of_accounts'),
    ]
    operations = [
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('expense_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('expense_date', models.DateField()),
                ('bs_date', models.CharField(help_text='YYYY-MM-DD', max_length=10)),
                ('expense_type', models.CharField(choices=[('RENT', 'Rent Expense'), ('SALARY', 'Salary Expense'), ('ELECTRICITY', 'Electricity Expense'), ('INTERNET', 'Internet Expense'), ('PACKAGING', 'Packaging Expense'), ('DELIVERY', 'Delivery Expense'), ('BANK_CHARGES', 'Bank Charges'), ('MARKETING', 'Marketing Expense'), ('DEPRECIATION', 'Depreciation Expense')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('payment_account_code', models.CharField(choices=[('1110', '1110 - Cash in Hand'), ('1120', '1120 - Bank Account'), ('1130', '1130 - Fonepay / Digital Wallet')], max_length=4)),
                ('description', models.CharField(max_length=255)),
                ('reference_number', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recorded_expenses', to=settings.AUTH_USER_MODEL)),
                ('fiscal_year', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounting.fiscalyear')),
                ('journal_entry', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='expense_record', to='accounting.journalentry')),
            ],
            options={'db_table': 'expense', 'ordering': ['-expense_date', '-expense_id']},
        ),
    ]
