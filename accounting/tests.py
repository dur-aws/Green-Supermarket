from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import ModulePermission, Role

from .models import Account, FiscalYear, JournalEntry, JournalItem
from .services import GeneralLedgerService


class GeneralLedgerServiceTests(TestCase):
	def setUp(self):
		self.fiscal_year = FiscalYear.objects.create(
			name='2080/81', start_date_bs='2080-04-01', end_date_bs='2081-03-31', is_active=True
		)
		self.next_fiscal_year = FiscalYear.objects.create(
			name='2081/82', start_date_bs='2081-04-01', end_date_bs='2082-03-31'
		)
		self.cash = Account.objects.create(account_code='1110', account_name='Cash', account_type='ASSET')
		self.sales = Account.objects.create(account_code='4100', account_name='Sales', account_type='REVENUE')

		opening = JournalEntry.objects.create(
			entry_date='2023-07-18', bs_date='2080-04-02', description='Opening sale',
			reference_type='SALE', reference_id=1, fiscal_year=self.fiscal_year,
		)
		JournalItem.objects.create(entry=opening, account=self.cash, debit=Decimal('1000.00'))
		JournalItem.objects.create(entry=opening, account=self.sales, credit=Decimal('1000.00'))
		JournalEntry.objects.filter(pk=opening.pk).update(status=JournalEntry.STATUS_POSTED)

		period = JournalEntry.objects.create(
			entry_date='2023-08-01', bs_date='2080-04-17', description='Counter sale',
				reference_type='SALE', reference_id=2, fiscal_year=self.fiscal_year,
		)
		JournalItem.objects.create(entry=period, account=self.cash, debit=Decimal('250.00'))
		JournalItem.objects.create(entry=period, account=self.sales, credit=Decimal('250.00'))
		JournalEntry.objects.filter(pk=period.pk).update(status=JournalEntry.STATUS_POSTED)

		other_year = JournalEntry.objects.create(
			entry_date='2024-07-18', bs_date='2081-04-02', description='Other year',
				reference_type='SALE', reference_id=3, fiscal_year=self.next_fiscal_year,
		)
		JournalItem.objects.create(entry=other_year, account=self.cash, debit=Decimal('900.00'))
		JournalItem.objects.create(entry=other_year, account=self.sales, credit=Decimal('900.00'))
		JournalEntry.objects.filter(pk=other_year.pk).update(status=JournalEntry.STATUS_POSTED)

	def test_opening_running_and_closing_balances_use_debit_normal_balance(self):
		report = GeneralLedgerService.get_report(
			fiscal_year_id=self.fiscal_year.pk,
			account_id=self.cash.pk,
			from_date='2080-04-10',
			to_date='2080-04-30',
		)
		self.assertEqual(report['opening_balance'], Decimal('1000.00'))
		self.assertEqual(report['opening_side'], 'Dr')
		self.assertEqual(report['total_debit'], Decimal('250.00'))
		self.assertEqual(report['total_credit'], Decimal('0.00'))
		self.assertEqual(report['rows'][0]['running_balance'], Decimal('1250.00'))
		self.assertEqual(report['rows'][0]['running_side'], 'Dr')
		self.assertEqual(report['closing_balance'], Decimal('1250.00'))

	def test_credit_normal_balance_uses_credit_minus_debit(self):
		report = GeneralLedgerService.get_report(
			fiscal_year_id=self.fiscal_year.pk, account_id=self.sales.pk,
			from_date='2080-04-01', to_date='2080-04-30',
		)
		self.assertEqual(report['closing_balance'], Decimal('1250.00'))
		self.assertEqual(report['closing_side'], 'Cr')

	def test_fiscal_year_filter_excludes_other_year_entries(self):
		report = GeneralLedgerService.get_report(
			fiscal_year_id=self.fiscal_year.pk, account_id=self.cash.pk,
		)
		self.assertEqual(len(report['rows']), 2)


class GeneralLedgerViewTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username='ledger-admin', email='ledger@example.com', password='password'
		)
		self.user.is_superuser = True
		self.user.is_staff = True
		self.user.save(update_fields=['is_superuser', 'is_staff'])
		self.fiscal_year = FiscalYear.objects.create(
			name='2082/83', start_date_bs='2082-04-01', end_date_bs='2083-03-31', is_active=True
		)
		self.account = Account.objects.create(account_code='1110', account_name='Cash', account_type='ASSET')

	def test_ledger_requires_authentication_and_pdf_is_available_to_authorized_user(self):
		client = Client()
		self.assertIn(client.get(reverse('general_ledger')).status_code, {302, 403})
		client.force_login(self.user)
		response = client.get(reverse('general_ledger'), {'account': self.account.pk})
		self.assertEqual(response.status_code, 200)
		pdf = client.get(reverse('general_ledger_pdf'), {'account': self.account.pk})
		self.assertEqual(pdf.status_code, 200)
		self.assertEqual(pdf['Content-Type'], 'application/pdf')
		self.assertTrue(pdf.content.startswith(b'%PDF'))

	def test_accounting_permission_controls_direct_ledger_url(self):
		role = Role.objects.create(role_name=Role.STAFF)
		restricted_user = get_user_model().objects.create_user(
			username='ledger-restricted', email='restricted@example.com', password='password', role_name=role
		)
		ModulePermission.objects.create(role=role, module_name='accounting', can_view=False)
		client = Client()
		client.force_login(restricted_user)
		response = client.get(reverse('general_ledger'), {'account': self.account.pk})
		self.assertEqual(response.status_code, 403)
