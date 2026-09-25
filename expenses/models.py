from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Expense(models.Model):
	EXPENSE_TYPE_CHOICES = [
		('RENT', 'Rent Expense'),
		('SALARY', 'Salary Expense'),
		('ELECTRICITY', 'Electricity Expense'),
		('INTERNET', 'Internet Expense'),
		('PACKAGING', 'Packaging Expense'),
		('DELIVERY', 'Delivery Expense'),
		('BANK_CHARGES', 'Bank Charges'),
		('MARKETING', 'Marketing Expense'),
		('DEPRECIATION', 'Depreciation Expense'),
	]
	PAYMENT_ACCOUNT_CHOICES = [
		('1110', '1110 - Cash in Hand'),
		('1120', '1120 - Bank Account'),
		('1130', '1130 - Fonepay / Digital Wallet'),
	]

	expense_id = models.BigAutoField(primary_key=True)
	expense_date = models.DateField()
	bs_date = models.CharField(max_length=10, help_text='YYYY-MM-DD')
	expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES)
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	payment_account_code = models.CharField(max_length=4, choices=PAYMENT_ACCOUNT_CHOICES)
	description = models.CharField(max_length=255)
	reference_number = models.CharField(max_length=100, blank=True)
	fiscal_year = models.ForeignKey('accounting.FiscalYear', on_delete=models.PROTECT)
	journal_entry = models.OneToOneField(
		'accounting.JournalEntry', on_delete=models.PROTECT,
		null=True, blank=True, related_name='expense_record'
	)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
		null=True, blank=True, related_name='recorded_expenses'
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-expense_date', '-expense_id']
		db_table = 'expense'

	def clean(self):
		if self.amount is not None and self.amount <= 0:
			raise ValidationError({'amount': 'Expense amount must be greater than zero.'})
		if self.fiscal_year_id and self.fiscal_year.is_closed:
			raise ValidationError('Cannot record an expense in a closed Fiscal Year.')

	def __str__(self):
		return f'{self.get_expense_type_display()} - {self.amount}'
