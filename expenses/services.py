from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from accounting.services import AccountingService, AccountingError
from .models import Expense


EXPENSE_ACCOUNT_CODES = {
    'RENT': '6010',
    'SALARY': '6020',
    'ELECTRICITY': '6030',
    'INTERNET': '6040',
    'PACKAGING': '6050',
    'DELIVERY': '6060',
    'BANK_CHARGES': '6070',
    'MARKETING': '6080',
    'DEPRECIATION': '6090',
}


@transaction.atomic
def post_expense(expense, user=None):
    if expense.journal_entry_id:
        return expense.journal_entry
    if expense.fiscal_year.is_closed:
        raise AccountingError(f'Cannot post to closed Fiscal Year {expense.fiscal_year.name}.')

    amount = Decimal(str(expense.amount)).quantize(Decimal('0.01'))
    if amount <= 0:
        raise AccountingError('Expense amount must be greater than zero.')

    entry = AccountingService.create_journal_entry(
        entry_date=expense.expense_date or timezone.now().date(),
        bs_date=expense.bs_date,
        description=expense.description,
        reference_type='EXPENSE',
        reference_id=expense.pk,
        fiscal_year=expense.fiscal_year,
        items=[
            {'account_code': EXPENSE_ACCOUNT_CODES[expense.expense_type], 'debit': amount, 'credit': 0},
            {'account_code': expense.payment_account_code, 'debit': 0, 'credit': amount},
        ],
        created_by=user or expense.created_by,
    )
    expense.journal_entry = entry
    expense.created_by = user or expense.created_by
    expense.save(update_fields=['journal_entry', 'created_by'])
    return entry
