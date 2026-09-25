from decimal import Decimal

from django.test import TestCase

from accounting.models import Account, FiscalYear
from .models import Expense
from .services import post_expense


class ExpensePostingTests(TestCase):
	def setUp(self):
		self.fiscal_year = FiscalYear.objects.create(
			name='2083/84', start_date_bs='2083-04-01', end_date_bs='2084-03-31', is_active=True
		)
		self.expense_account = Account.objects.create(
			account_code='6010', account_name='Rent Expense', account_type='EXPENSE'
		)
		self.cash_account = Account.objects.create(
			account_code='1110', account_name='Cash in Hand', account_type='ASSET'
		)

	def test_expense_posts_balanced_journal_entry(self):
		expense = Expense.objects.create(
			expense_date='2026-08-01', bs_date='2083-04-16', expense_type='RENT',
			amount=Decimal('15000.00'), payment_account_code='1110',
			description='Shop rent', fiscal_year=self.fiscal_year,
		)
		entry = post_expense(expense)
		self.assertEqual(entry.reference_type, 'EXPENSE')
		self.assertEqual(entry.items.count(), 2)
		self.assertEqual(sum(item.debit for item in entry.items.all()), Decimal('15000.00'))
		self.assertEqual(sum(item.credit for item in entry.items.all()), Decimal('15000.00'))
		self.assertEqual(expense.journal_entry_id, entry.entry_id)
