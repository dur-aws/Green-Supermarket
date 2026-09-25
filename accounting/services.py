import nepali_datetime
from decimal import Decimal

from django.db.models import Prefetch, Q, Sum
from .models import FiscalYear, JournalEntry
from .models import Account, JournalItem


class GeneralLedgerError(ValueError):
    """Raised when General Ledger filters cannot be validated."""


class TrialBalanceError(ValueError):
    """Raised when Trial Balance filters cannot be validated."""


class GeneralLedgerService:
    """Build an account-wise General Ledger from balanced JournalEntry/JournalItem data."""

    ZERO = Decimal('0.00')

    @staticmethod
    def _valid_bs_date(value, label):
        """Validate a Nepali B.S. date in YYYY-MM-DD format."""
        if not value:
            return None

        value = str(value).strip()

        if (
            len(value) != 10
            or value[4] != '-'
            or value[7] != '-'
            or not value[:4].isdigit()
            or not value[5:7].isdigit()
            or not value[8:10].isdigit()
        ):
            raise GeneralLedgerError(f'{label} must use YYYY-MM-DD format.')

        try:
            year, month, day = map(int, value.split('-'))
            parsed = nepali_datetime.date(year, month, day)
        except (TypeError, ValueError):
            raise GeneralLedgerError(
                f'{label} must be a valid Nepali date in YYYY-MM-DD format.'
            )

        if parsed.isoformat() != value:
            raise GeneralLedgerError(f'{label} must use YYYY-MM-DD format.')

        return value

    @staticmethod
    def _balance_side(balance, normal_balance):
        balance = Decimal(balance or '0.00')
        if normal_balance == 'debit':
            return 'Dr' if balance >= Decimal('0.00') else 'Cr'
        return 'Cr' if balance >= Decimal('0.00') else 'Dr'

    @classmethod
    def get_report(
        cls, *, fiscal_year_id=None, account_id=None,
        from_date='', to_date='', search=''
    ):
        fiscal_year = (
            FiscalYear.objects.filter(pk=fiscal_year_id).first()
            if fiscal_year_id
            else FiscalYear.objects.filter(is_active=True).first()
        )

        if fiscal_year is None:
            fiscal_year = FiscalYear.objects.order_by('-start_date_bs').first()

        if fiscal_year is None:
            raise GeneralLedgerError(
                'Create a Fiscal Year before opening the General Ledger.'
            )

        from_date = cls._valid_bs_date(from_date, 'From Date') or fiscal_year.start_date_bs
        to_date = cls._valid_bs_date(to_date, 'To Date') or fiscal_year.end_date_bs

        if from_date < fiscal_year.start_date_bs or to_date > fiscal_year.end_date_bs:
            raise GeneralLedgerError(
                'The selected dates must be inside the selected Fiscal Year.'
            )

        if from_date > to_date:
            raise GeneralLedgerError('From Date cannot be later than To Date.')

        account = (
            Account.objects.filter(pk=account_id, is_active=True).first()
            if account_id else None
        )
        if account is None:
            raise GeneralLedgerError('Select an account to open the General Ledger.')

        # Do not apply search here. Opening balance must include every
        # transaction before From Date, even when a search is active.
        items = (
            JournalItem.objects
            .filter(entry__fiscal_year=fiscal_year, entry__status=JournalEntry.STATUS_POSTED, account=account)
            .select_related('account', 'entry', 'entry__fiscal_year')
            .prefetch_related(
                Prefetch(
                    'entry__items',
                    queryset=JournalItem.objects.only(
                        'entry_id', 'debit', 'credit'
                    ),
                    to_attr='ledger_entry_items',
                )
            )
            .order_by('entry__entry_date', 'entry_id', 'item_id')
        )

        search = (search or '').strip()
        normal_balance = (
            'credit'
            if str(account.account_type).upper()
            in {'LIABILITY', 'EQUITY', 'REVENUE'}
            else 'debit'
        )

        opening = cls.ZERO
        period_rows = []

        for item in items:
            entry = item.entry
            entry_lines = getattr(entry, 'ledger_entry_items', [])

            total_debit = sum(
                (Decimal(line.debit or cls.ZERO) for line in entry_lines),
                cls.ZERO
            )
            total_credit = sum(
                (Decimal(line.credit or cls.ZERO) for line in entry_lines),
                cls.ZERO
            )

            # Only balanced journal entries are treated as posted ledger data.
            if total_debit != total_credit:
                continue

            date_bs = (
                entry.bs_date
                or nepali_datetime.date
                .from_datetime_date(entry.entry_date)
                .isoformat()
            )

            debit = Decimal(item.debit or cls.ZERO)
            credit = Decimal(item.credit or cls.ZERO)

            if date_bs < from_date:
                movement = debit - credit
                opening += movement if normal_balance == 'debit' else -movement
                continue

            if date_bs > to_date:
                continue

            # Search only affects visible period rows, never the opening balance.
            if search:
                searchable = ' '.join([
                    str(entry.entry_id or ''),
                    str(entry.reference_id or ''),
                    str(entry.reference_type or ''),
                    str(entry.description or ''),
                ]).lower()

                if search.lower() not in searchable:
                    continue

            period_rows.append({
                'item': item,
                'entry': entry,
                'date_bs': date_bs,
                'journal_no': f'JV-{entry.entry_id}',
                'reference': (
                    f'{entry.get_reference_type_display()} #{entry.reference_id}'
                    if entry.reference_id
                    else entry.get_reference_type_display()
                ),
                'particulars': entry.description,
                'debit': debit,
                'credit': credit,
            })

        running = opening

        for row in period_rows:
            movement = row['debit'] - row['credit']
            running += movement if normal_balance == 'debit' else -movement
            row['running_balance'] = abs(running)
            row['running_side'] = cls._balance_side(running, normal_balance)

        total_debit = sum(
            (row['debit'] for row in period_rows), cls.ZERO
        )
        total_credit = sum(
            (row['credit'] for row in period_rows), cls.ZERO
        )

        return {
            'fiscal_year': fiscal_year,
            'account': account,
            'accounts': Account.objects.filter(
                is_active=True
            ).order_by('account_code'),
            'from_date': from_date,
            'to_date': to_date,
            'search': search,
            'normal_balance': normal_balance,
            'opening_balance': abs(opening),
            'opening_side': cls._balance_side(opening, normal_balance),
            'rows': period_rows,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'closing_balance': abs(running),
            'closing_side': cls._balance_side(running, normal_balance),
        }


class TrialBalanceService:
    """Build a Trial Balance from posted journal items only."""

    ZERO = Decimal('0.00')

    @classmethod
    def get_report(cls, *, fiscal_year_id=None, from_date='', to_date='', search='', account_type=''):
        fiscal_year = (
            FiscalYear.objects.filter(pk=fiscal_year_id).first()
            if fiscal_year_id else FiscalYear.objects.filter(is_active=True).first()
        ) or FiscalYear.objects.order_by('-start_date_bs').first()
        if fiscal_year is None:
            raise TrialBalanceError('Create a Fiscal Year before opening the Trial Balance.')

        from_date = GeneralLedgerService._valid_bs_date(from_date, 'From Date') or fiscal_year.start_date_bs
        to_date = GeneralLedgerService._valid_bs_date(to_date, 'To Date') or fiscal_year.end_date_bs
        if from_date < fiscal_year.start_date_bs or to_date > fiscal_year.end_date_bs:
            raise TrialBalanceError('The selected dates must be inside the selected Fiscal Year.')
        if from_date > to_date:
            raise TrialBalanceError('From Date cannot be later than To Date.')

        accounts = Account.objects.filter(is_active=True).select_related('parent_account').order_by('account_code')
        search = (search or '').strip()
        if search:
            accounts = accounts.filter(Q(account_code__icontains=search) | Q(account_name__icontains=search))
        if account_type:
            accounts = accounts.filter(account_type=account_type)

        posted_items = JournalItem.objects.filter(
            entry__fiscal_year=fiscal_year,
            entry__status=JournalEntry.STATUS_POSTED,
        )
        dated_items = posted_items.filter(
            entry__bs_date__gte=fiscal_year.start_date_bs,
            entry__bs_date__lte=fiscal_year.end_date_bs,
        )
        opening = dated_items.filter(entry__bs_date__lt=from_date).values('account_id').annotate(
            debit=Sum('debit'), credit=Sum('credit')
        )
        period = dated_items.filter(entry__bs_date__gte=from_date, entry__bs_date__lte=to_date).values('account_id').annotate(
            debit=Sum('debit'), credit=Sum('credit')
        )
        opening_map = {row['account_id']: row for row in opening}
        period_map = {row['account_id']: row for row in period}

        # Older automatic journals may have an empty B.S. date. Convert their
        # Gregorian entry date using the same convention as General Ledger.
        legacy_items = posted_items.filter(
            Q(entry__bs_date='') | Q(entry__bs_date__isnull=True)
        ).select_related('entry')
        for item in legacy_items:
            date_bs = nepali_datetime.date.from_datetime_date(item.entry.entry_date).isoformat()
            target = opening_map if date_bs < from_date else period_map if date_bs <= to_date else None
            if target is None:
                continue
            row = target.setdefault(item.account_id, {'debit': cls.ZERO, 'credit': cls.ZERO})
            row['debit'] += Decimal(item.debit or cls.ZERO)
            row['credit'] += Decimal(item.credit or cls.ZERO)

        rows = []
        total_debit = cls.ZERO
        total_credit = cls.ZERO
        for account in accounts:
            opening_row = opening_map.get(account.account_id, {})
            period_row = period_map.get(account.account_id, {})
            opening_debit = Decimal(opening_row.get('debit') or cls.ZERO)
            opening_credit = Decimal(opening_row.get('credit') or cls.ZERO)
            period_debit = Decimal(period_row.get('debit') or cls.ZERO)
            period_credit = Decimal(period_row.get('credit') or cls.ZERO)
            opening_net = opening_debit - opening_credit
            closing_net = opening_net + period_debit - period_credit
            final_debit = max(closing_net, cls.ZERO)
            final_credit = max(-closing_net, cls.ZERO)
            total_debit += final_debit
            total_credit += final_credit
            rows.append({
                'account': account,
                'parent_account': account.parent_account,
                'opening_debit': opening_debit,
                'opening_credit': opening_credit,
                'opening_balance': abs(opening_net),
                'opening_side': 'Dr' if opening_net >= cls.ZERO else 'Cr',
                'period_debit': period_debit,
                'period_credit': period_credit,
                'closing_debit': final_debit,
                'closing_credit': final_credit,
            })

        difference = (total_debit - total_credit).quantize(cls.ZERO)
        return {
            'fiscal_year': fiscal_year,
            'from_date': from_date,
            'to_date': to_date,
            'search': search,
            'account_type': account_type,
            'account_types': Account.ACCOUNT_TYPE_CHOICES,
            'rows': rows,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'difference': difference,
            'is_balanced': difference == cls.ZERO,
        }


class FiscalYearService:

    @staticmethod
    def get_current_fy_info(np_date=None):
        """Calculates default fiscal year details for a given B.S. date."""
        if np_date is None:
            np_date = nepali_datetime.date.today()

        year, month = np_date.year, np_date.month

        if month >= 4:  # Shrawan (Month 4) onwards
            start_year, end_year = year, year + 1
        else:
            start_year, end_year = year - 1, year

        fy_code = f"{start_year}/{str(end_year)[-2:]}"
        start_date = f"{start_year}-04-01"
        
        last_day = nepali_datetime._days_in_month(year, 3)

        end_date = f"{end_year}-03-{last_day:02d}"

        return {
            "name": fy_code,
            "start_date_bs": start_date,
            "end_date_bs": end_date,
        }

    @classmethod
    def auto_create_current_fy(cls):
        """Creates and activates the current fiscal year if missing."""
        info = cls.get_current_fy_info()
        fy, created = FiscalYear.objects.get_or_create(
            name=info["name"],
            defaults={
                "start_date_bs": info["start_date_bs"],
                "end_date_bs": info["end_date_bs"],
                "is_active": True
            }
        )
        if created:
            cls.set_active_fiscal_year(fy.id)
        return fy

    @staticmethod
    def set_active_fiscal_year(fy_id):
        """Sets a specific fiscal year as active and deactivates others."""
        FiscalYear.objects.filter(is_active=True).update(is_active=False)
        FiscalYear.objects.filter(id=fy_id).update(is_active=True)

    @staticmethod
    def toggle_close_status(fy_id):
        """Toggles the closed state of a fiscal year."""
        fy = FiscalYear.objects.get(id=fy_id)
        fy.is_closed = not fy.is_closed
        fy.save()
        return fy
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Account, FiscalYear, JournalEntry, JournalItem

class AccountingError(Exception):
    pass


class ChartOfAccountsService:
    @staticmethod
    def ensure_default_accounts():
        """Ensure the hierarchical GSMS Chart of Accounts exists."""
        accounts = [
            ('1000', 'ASSETS', 'ASSET', None),
            ('1100', 'Cash & Bank', 'ASSET', '1000'),
            ('1110', 'Cash in Hand', 'ASSET', '1100'),
            ('1120', 'Bank Account', 'ASSET', '1100'),
            ('1130', 'Fonepay / Digital Wallet', 'ASSET', '1100'),
            ('1200', 'Receivables', 'ASSET', '1000'),
            ('1210', 'Accounts Receivable', 'ASSET', '1200'),
            ('1220', 'Refund Clearing', 'ASSET', '1200'),
            ('1300', 'Inventory', 'ASSET', '1000'),
            ('1310', 'Inventory Asset', 'ASSET', '1300'),
            ('2000', 'LIABILITIES', 'LIABILITY', None),
            ('2100', 'Accounts Payable', 'LIABILITY', '2000'),
            ('2200', 'VAT Payable', 'LIABILITY', '2000'),
            ('2300', 'TDS Payable', 'LIABILITY', '2000'),
            ('3000', 'EQUITY', 'EQUITY', None),
            ('3100', "Owner's Capital", 'EQUITY', '3000'),
            ('3200', 'Retained Earnings', 'EQUITY', '3000'),
            ('4000', 'REVENUE', 'REVENUE', None),
            ('4100', 'Sales Revenue', 'REVENUE', '4000'),
            ('5000', 'COST OF SALES', 'EXPENSE', None),
            ('5100', 'Cost of Goods Sold', 'EXPENSE', '5000'),
            ('6000', 'EXPENSES', 'EXPENSE', None),
            ('6010', 'Rent Expense', 'EXPENSE', '6000'),
            ('6020', 'Salary Expense', 'EXPENSE', '6000'),
            ('6030', 'Electricity Expense', 'EXPENSE', '6000'),
            ('6040', 'Internet Expense', 'EXPENSE', '6000'),
            ('6050', 'Packaging Expense', 'EXPENSE', '6000'),
            ('6060', 'Delivery Expense', 'EXPENSE', '6000'),
            ('6070', 'Bank Charges', 'EXPENSE', '6000'),
            ('6080', 'Marketing Expense', 'EXPENSE', '6000'),
            ('6090', 'Depreciation Expense', 'EXPENSE', '6000'),
            ('6100', 'Inventory Wastage / Loss', 'EXPENSE', '6000'),
            ('6200', 'Sales Discounts', 'EXPENSE', '6000'),
            ('6300', 'Round-off Loss', 'EXPENSE', '6000'),
            ('7000', 'OTHER INCOME', 'REVENUE', None),
            ('7100', 'Round-off Gain', 'REVENUE', '7000'),
        ]
        
        created_accounts = {}
        for code, name, acc_type, parent_code in accounts:
            parent = created_accounts.get(parent_code) if parent_code else None
            acc, _ = Account.objects.get_or_create(
                account_code=code,
                defaults={
                    'account_name': name,
                    'account_type': acc_type,
                    'parent_account': parent,
                    'is_active': True
                }
            )
            created_accounts[code] = acc
        return created_accounts


class AccountingService:
    ZERO = Decimal("0.00")

    @staticmethod
    def _money(value):
        return Decimal(str(value or "0.00")).quantize(Decimal("0.01"))

    @staticmethod
    def _get_customer_receivable_account(customer):
        """Return the customer's A/R account; never fall back to parent 1210."""
        if customer is None:
            raise AccountingError("Customer is required for an Accounts Receivable transaction.")
        account = getattr(customer, "account", None)
        if account is None:
            raise AccountingError(f"Customer {customer} does not have an Accounts Receivable account configured.")
        return account
    
    @staticmethod
    def _get_account(code):
        acc = Account.objects.filter(account_code=code).first()
        if not acc:
            ChartOfAccountsService.ensure_default_accounts()
            acc = Account.objects.filter(account_code=code).first()
        if not acc:
            raise AccountingError(f"Account code {code} not configured in Chart of Accounts.")
        return acc

    @staticmethod
    def create_journal_entry(entry_date, bs_date, description, reference_type, reference_id, fiscal_year, items, created_by=None):
        """
        Creates a balanced GL Journal Entry.
        items: list of dicts -> [{'account_code': '1110', 'debit': Decimal('100'), 'credit': Decimal('0')}]
        """
        if not items:
            raise AccountingError("Cannot post empty journal voucher.")

        total_debit = sum(Decimal(str(i.get('debit', '0.00'))) for i in items).quantize(Decimal('0.01'))
        total_credit = sum(Decimal(str(i.get('credit', '0.00'))) for i in items).quantize(Decimal('0.01'))

        if total_debit != total_credit:
            raise AccountingError(
                f"Unbalanced Journal Voucher! Total Debit ({total_debit}) != Total Credit ({total_credit})."
            )

        if getattr(fiscal_year, 'is_closed', False):
            raise AccountingError(f"Cannot post to closed Fiscal Year {fiscal_year.name}.")

        with transaction.atomic():
            entry = JournalEntry.objects.create(
                entry_date=entry_date,
                bs_date=bs_date or '',
                description=description,
                reference_type=reference_type,
                reference_id=reference_id,
                fiscal_year=fiscal_year,
                created_by=created_by
            )

            for item in items:
                account = item.get('account_obj') or AccountingService._get_account(item['account_code'])
                JournalItem.objects.create(
                    entry=entry,
                    account=account,
                    debit=Decimal(str(item.get('debit', '0.00'))).quantize(Decimal('0.01')),
                    credit=Decimal(str(item.get('credit', '0.00'))).quantize(Decimal('0.01'))
                )
            AccountingService.post_journal_entry(entry, user=created_by)
            return entry

    @classmethod
    @transaction.atomic
    def post_journal_entry(cls, entry, user=None):
        entry = JournalEntry.objects.select_for_update().get(pk=entry.pk)
        if entry.status == JournalEntry.STATUS_POSTED:
            return entry
        if entry.status == JournalEntry.STATUS_REVERSED:
            raise AccountingError('A reversed journal entry cannot be posted.')
        lines = list(entry.items.all())
        if not lines:
            raise AccountingError('A journal entry must contain at least one line.')
        total_debit = sum((Decimal(line.debit or '0.00') for line in lines), Decimal('0.00'))
        total_credit = sum((Decimal(line.credit or '0.00') for line in lines), Decimal('0.00'))
        if total_debit.quantize(Decimal('0.01')) != total_credit.quantize(Decimal('0.01')):
            raise AccountingError('Journal entry debit and credit totals must balance before posting.')
        entry.status = JournalEntry.STATUS_POSTED
        entry.posted_by = user or entry.created_by
        entry.posted_at = timezone.now()
        entry.save(update_fields=['status', 'posted_by', 'posted_at'])
        return entry

    @classmethod
    @transaction.atomic
    def reverse_journal_entry(cls, entry, user=None):
        entry = JournalEntry.objects.select_for_update().prefetch_related('items').get(pk=entry.pk)
        if entry.status != JournalEntry.STATUS_POSTED:
            raise AccountingError('Only posted journal entries can be reversed.')
        reversal = JournalEntry.objects.create(
            entry_date=timezone.now().date(), bs_date=entry.bs_date,
            description=f'Reversal of JV-{entry.entry_id}: {entry.description}',
            reference_type='MANUAL', reference_id=entry.entry_id,
            fiscal_year=entry.fiscal_year, created_by=user,
        )
        for line in entry.items.all():
            JournalItem.objects.create(entry=reversal, account=line.account, debit=line.credit, credit=line.debit)
        cls.post_journal_entry(reversal, user=user)
        entry.status = JournalEntry.STATUS_REVERSED
        entry.reversed_by = user
        entry.reversed_at = timezone.now()
        entry.save(update_fields=['status', 'reversed_by', 'reversed_at'])
        return reversal

    @classmethod
    def post_inventory_loss_journal_entry(
        cls, *, entry_date, reference_id, amount, description, created_by=None
    ):
        """Post the standard debit-loss/credit-inventory entry for stock write-offs."""
        amount = Decimal(str(amount)).quantize(Decimal('0.01'))
        if amount <= Decimal('0.00'):
            raise AccountingError("Inventory loss must be greater than zero.")

        existing_entry = JournalEntry.objects.filter(
            reference_type='ADJUST', reference_id=reference_id, description=description
        ).first()
        if existing_entry:
            return existing_entry

        fiscal_year = FiscalYear.objects.filter(is_active=True).first()
        if fiscal_year is None:
            fiscal_year = FiscalYearService.auto_create_current_fy()

        return cls.create_journal_entry(
            entry_date=entry_date,
            bs_date='',
            description=description,
            reference_type='ADJUST',
            reference_id=reference_id,
            fiscal_year=fiscal_year,
            items=[
                {'account_code': '6100', 'debit': amount, 'credit': Decimal('0.00')},
                {'account_code': '1310', 'debit': Decimal('0.00'), 'credit': amount},
            ],
            created_by=created_by,
        )

    @classmethod
    def post_purchase_return_journal_entry(
        cls, *, entry_date, reference_id, amount, description, created_by=None
    ):
        """Reduce supplier liability when inventory is returned to the supplier."""
        amount = Decimal(str(amount)).quantize(Decimal('0.01'))
        if amount <= Decimal('0.00'):
            raise AccountingError("Purchase return value must be greater than zero.")

        existing_entry = JournalEntry.objects.filter(
            reference_type='ADJUST', reference_id=reference_id, description=description
        ).first()
        if existing_entry:
            return existing_entry

        fiscal_year = FiscalYear.objects.filter(is_active=True).first()
        if fiscal_year is None:
            fiscal_year = FiscalYearService.auto_create_current_fy()

        return cls.create_journal_entry(
            entry_date=entry_date,
            bs_date='',
            description=description,
            reference_type='ADJUST',
            reference_id=reference_id,
            fiscal_year=fiscal_year,
            items=[
                {'account_code': '2100', 'debit': amount, 'credit': Decimal('0.00')},
                {'account_code': '1310', 'debit': Decimal('0.00'), 'credit': amount},
            ],
            created_by=created_by,
        )

    @classmethod
    @transaction.atomic
    def post_purchase_receipt_journal_entry(cls, purchase, created_by=None):
        """Post inventory, input VAT, supplier payable, and TDS for a received purchase."""
        if purchase.journal_entry_id:
            return purchase.journal_entry

        fiscal_year = FiscalYear.objects.filter(is_active=True).first()
        if fiscal_year is None:
            fiscal_year = FiscalYearService.auto_create_current_fy()

        subtotal = Decimal(str(purchase.subtotal or 0)).quantize(Decimal('0.01'))
        freight = Decimal(str(purchase.freight_charge or 0)).quantize(Decimal('0.01'))
        vat = Decimal(str(purchase.vat_amount or 0)).quantize(Decimal('0.01'))
        tds = Decimal(str(purchase.tds_amount or 0)).quantize(Decimal('0.01'))
        inventory_value = subtotal + freight
        payable = Decimal(str(purchase.net_payable_amount or 0)).quantize(Decimal('0.01'))

        grn_entry = cls.create_journal_entry(
            entry_date=purchase.received_date or purchase.order_date or timezone.now().date(),
            bs_date='',
            description=f'GRN receipt for purchase #{purchase.purchase_id}',
            reference_type='PURCHASE',
            reference_id=purchase.purchase_id,
            fiscal_year=fiscal_year,
            items=[
                {'account_code': '1310', 'debit': inventory_value, 'credit': 0},
                {'account_code': '2100', 'debit': 0, 'credit': inventory_value},
            ],
            created_by=created_by or purchase.received_by_user,
        )

        items = [
            {'account_code': '2100', 'debit': inventory_value, 'credit': 0},
            {'account_code': '2100', 'debit': 0, 'credit': payable},
        ]
        if vat > 0:
            items.append({'account_code': '2200', 'debit': vat, 'credit': 0})
        if tds > 0:
            items.append({'account_code': '2300', 'debit': 0, 'credit': tds})

        entry = cls.create_journal_entry(
            entry_date=purchase.received_date or purchase.order_date or timezone.now().date(),
            bs_date='',
            description=f'Purchase invoice #{purchase.purchase_id}',
            reference_type='PURCHASE',
            reference_id=purchase.purchase_id,
            fiscal_year=fiscal_year,
            items=items,
            created_by=created_by or purchase.received_by_user,
        )
        purchase.journal_entry = entry
        purchase.save(update_fields=['journal_entry'])
        return entry

    @classmethod
    @transaction.atomic
    def post_purchase_payment_journal_entry(cls, payment, created_by=None):
        """Post a supplier settlement from cash/bank to accounts payable."""
        existing_entry = JournalEntry.objects.filter(
            reference_type='PAYMENT', reference_id=payment.pk
        ).first()
        if existing_entry:
            return existing_entry

        fiscal_year = FiscalYear.objects.filter(is_active=True).first()
        if fiscal_year is None:
            fiscal_year = FiscalYearService.auto_create_current_fy()
        amount = Decimal(str(payment.amount)).quantize(Decimal('0.01'))
        return cls.create_journal_entry(
            entry_date=timezone.now().date(),
            bs_date='',
            description=f'Supplier payment for purchase #{payment.purchase_id}',
            reference_type='PAYMENT',
            reference_id=payment.pk,
            fiscal_year=fiscal_year,
            items=[
                {'account_code': cls._resolve_payment_account(payment.payment_method), 'debit': amount, 'credit': 0},
                {'account_code': '2100', 'debit': 0, 'credit': amount},
            ],
            created_by=created_by or payment.created_by,
        )

    @classmethod
    @transaction.atomic
    def post_sale_journal_entry(cls, sale):
        """Post sale revenue/tax/settlement and COGS journals.

        CREDIT supports partial settlement:
            Dr actual settlement accounts
            Dr customer A/R for the unpaid balance
                Cr Sales Revenue / VAT / round-off as applicable

        CREDIT is never treated as a settlement account.
        """
        fiscal_year = (
            getattr(sale, 'fiscal_year', None)
            or FiscalYear.objects.filter(is_active=True).first()
        )
        if fiscal_year is None:
            raise AccountingError(
                'No fiscal year is available for the sales journal.'
            )
        if getattr(fiscal_year, 'is_closed', False):
            raise AccountingError(
                f'Cannot post to closed Fiscal Year {fiscal_year.name}.'
            )

        gross_sales = cls._money(getattr(sale, 'subtotal', 0))
        discount = cls._money(getattr(sale, 'discount_total', 0))
        vat = cls._money(getattr(sale, 'vat_total', 0))
        grand_total = cls._money(getattr(sale, 'grand_total', 0))

        description = f"Sales Invoice #{sale.invoice_no} ({sale.buyer_name})"

        # Posted journals must not be deleted/rebuilt.
        existing = JournalEntry.objects.filter(
            reference_type='SALE',
            reference_id=sale.pk,
            description=description,
        ).first()
        if existing:
            if getattr(sale, 'journal_entry_id', None) != existing.entry_id:
                sale.journal_entry = existing
                sale.save(update_fields=['journal_entry'])
            return existing

        items = []
        mode = str(
            getattr(sale, 'payment_mode', '') or ''
        ).strip().upper()

        settlement_methods = {
            'CASH', 'CARD', 'BANK_TRANSFER', 'FONEPAY'
        }

        # ---------------------------------------------------------
        # DEBIT: settlement accounts + customer-specific A/R
        # ---------------------------------------------------------
        if mode in {'CREDIT', 'SPLIT'}:
            receivable = cls._get_customer_receivable_account(
                getattr(sale, 'customer', None)
            )

            paid = Decimal('0.00')

            for payment in sale.payment_transactions.filter(status='PAID'):
                method = str(
                    getattr(payment, 'payment_method', '') or ''
                ).strip().upper()
                amount = cls._money(getattr(payment, 'amount', 0))

                if amount <= Decimal('0.00'):
                    continue

                # CREDIT is the outstanding portion, not a settlement.
                if method == 'CREDIT':
                    continue

                if method not in settlement_methods:
                    raise AccountingError(
                        f'Unsupported settlement method: {method}'
                    )

                items.append({
                    'account_code': cls._resolve_payment_account(method),
                    'debit': amount,
                    'credit': Decimal('0.00'),
                })
                paid += amount

            due = cls._money(grand_total - paid)

            if due < Decimal('0.00'):
                raise AccountingError(
                    f'Payment amount exceeds invoice total. '
                    f'Invoice total: {grand_total}, paid: {paid}.'
                )

            if due > Decimal('0.00'):
                items.append({
                    'account_obj': receivable,
                    'debit': due,
                    'credit': Decimal('0.00'),
                })

        elif mode in settlement_methods:
            items.append({
                'account_code': cls._resolve_payment_account(mode),
                'debit': grand_total,
                'credit': Decimal('0.00'),
            })
        else:
            raise AccountingError(
                f'Unsupported sale payment mode: {mode or "EMPTY"}'
            )

        # Sales discount
        if discount > Decimal('0.00'):
            items.append({
                'account_code': '6200',
                'debit': discount,
                'credit': Decimal('0.00'),
            })

        # Sales revenue
        items.append({
            'account_obj': cls._get_account('4100'),
            'debit': Decimal('0.00'),
            'credit': gross_sales,
        })

        # Output VAT
        if vat > Decimal('0.00'):
            items.append({
                'account_code': '2200',
                'debit': Decimal('0.00'),
                'credit': vat,
            })

        # Round-off
        round_off = cls._money(
            grand_total + discount - gross_sales - vat
        )
        if round_off > Decimal('0.00'):
            items.append({
                'account_code': '7100',
                'debit': Decimal('0.00'),
                'credit': round_off,
            })
        elif round_off < Decimal('0.00'):
            items.append({
                'account_code': '6300',
                'debit': abs(round_off),
                'credit': Decimal('0.00'),
            })

        entry = cls.create_journal_entry(
            entry_date=timezone.now().date(),
            bs_date=getattr(sale, 'bs_date', '') or '',
            description=description,
            reference_type='SALE',
            reference_id=sale.pk,
            fiscal_year=fiscal_year,
            items=items,
            created_by=getattr(sale, 'user', None),
        )

        # COGS / Inventory Asset
        total_cogs = Decimal('0.00')
        for item in sale.items.all():
            cost = cls._money(
                getattr(getattr(item, 'variant', None), 'cost_price', 0)
            )
            qty = Decimal(str(getattr(item, 'quantity', 0) or 0))
            total_cogs += (
                cost * qty
            ).quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            )

        if total_cogs > Decimal('0.00'):
            cogs_desc = f"COGS Deduction for Invoice #{sale.invoice_no}"
            if not JournalEntry.objects.filter(
                reference_type='SALE',
                reference_id=sale.pk,
                description=cogs_desc,
            ).exists():
                cls.create_journal_entry(
                    entry_date=timezone.now().date(),
                    bs_date=getattr(sale, 'bs_date', '') or '',
                    description=cogs_desc,
                    reference_type='SALE',
                    reference_id=sale.pk,
                    fiscal_year=fiscal_year,
                    items=[
                        {
                            'account_code': '5100',
                            'debit': total_cogs,
                            'credit': Decimal('0.00'),
                        },
                        {
                            'account_code': '1310',
                            'debit': Decimal('0.00'),
                            'credit': total_cogs,
                        },
                    ],
                    created_by=getattr(sale, 'user', None),
                )

        sale.journal_entry = entry
        sale.save(update_fields=['journal_entry'])
        return entry

    @classmethod
    @transaction.atomic
    def post_sale_payment_journal_entry(cls, payment, created_by=None):
        """Post a later customer settlement against customer-specific A/R."""
        existing = JournalEntry.objects.filter(
            reference_type='PAYMENT',
            reference_id=payment.pk
        ).first()
        if existing:
            return existing

        sale = getattr(payment, 'sale', None)
        if sale is None:
            raise AccountingError(
                'A sale payment must reference a sale.'
            )

        fiscal_year = (
            getattr(sale, 'fiscal_year', None)
            or FiscalYear.objects.filter(is_active=True).first()
        )
        if fiscal_year is None:
            raise AccountingError(
                'No fiscal year is available for the payment journal.'
            )
        if getattr(fiscal_year, 'is_closed', False):
            raise AccountingError(
                f'Cannot post to closed Fiscal Year {fiscal_year.name}.'
            )

        amount = cls._money(getattr(payment, 'amount', 0))
        if amount <= Decimal('0.00'):
            raise AccountingError(
                'Customer payment amount must be greater than zero.'
            )

        method = str(
            getattr(payment, 'payment_method', '') or ''
        ).strip().upper()
        if method == 'CREDIT':
            raise AccountingError(
                'A customer settlement cannot use CREDIT. '
                'Use CASH, CARD, BANK_TRANSFER, or FONEPAY.'
            )

        receivable = cls._get_customer_receivable_account(
            getattr(sale, 'customer', None)
        )

        return cls.create_journal_entry(
            entry_date=timezone.now().date(),
            bs_date=getattr(sale, 'bs_date', '') or '',
            description=f'Customer payment for invoice #{sale.invoice_no}',
            reference_type='PAYMENT',
            reference_id=payment.pk,
            fiscal_year=fiscal_year,
            items=[
                {
                    'account_code': cls._resolve_payment_account(method),
                    'debit': amount,
                    'credit': Decimal('0.00'),
                },
                {
                    'account_obj': receivable,
                    'debit': Decimal('0.00'),
                    'credit': amount,
                },
            ],
            created_by=created_by or getattr(payment, 'created_by', None),
        )

    @staticmethod
    def _resolve_payment_account(method):
        """Return only real settlement accounts; CREDIT is customer A/R."""
        mapping = {
            'CASH': '1110',
            'CARD': '1120',
            'BANK_TRANSFER': '1120',
            'FONEPAY': '1130',
        }
        normalized = str(method or '').strip().upper()

        if normalized == 'CREDIT':
            raise AccountingError(
                'CREDIT is not a settlement account. '
                'Use the customer A/R account.'
            )

        account_code = mapping.get(normalized)
        if not account_code:
            raise AccountingError(
                f'Unsupported payment method: {method}'
            )
        return account_code

