import nepali_datetime
from .models import FiscalYear

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
        """Auto-seeds essential Chart of Accounts for GSMS IRD engine."""
        accounts = [
            ('1010', 'Cash in Hand', 'ASSET', None),
            ('1020', 'Bank Account / Card Clearing', 'ASSET', None),
            ('1030', 'Digital Wallet Clearing (Fonepay)', 'ASSET', None),
            ('1100', 'Accounts Receivable (Customers)', 'ASSET', None),
            ('1200', 'Inventory Asset Account', 'ASSET', None),
            ('2010', 'Accounts Payable (Suppliers)', 'LIABILITY', None),
            ('2020', 'Output VAT Payable', 'LIABILITY', None),
            ('2030', 'Input VAT Credit', 'LIABILITY', None),
            ('3010', 'Sales Revenue', 'REVENUE', None),
            ('3020', 'Sales Discounts Allowed', 'EXPENSE', None),
            ('3030', 'Round Off Gain/Loss', 'EXPENSE', None),
            ('4010', 'Cost of Goods Sold (COGS)', 'EXPENSE', None),
            ('4020', 'Inventory Wastage / Loss', 'EXPENSE', None),
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
        items: list of dicts -> [{'account_code': '1010', 'debit': Decimal('100'), 'credit': Decimal('0')}]
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
            return entry

    @classmethod
    @transaction.atomic
    def post_sale_journal_entry(cls, sale):
        """
        Posts complete Revenue, Discounts, VAT Output, Payments, and COGS GL Entries for a completed sale.
        """
        existing_entry = JournalEntry.objects.filter(
            reference_type='SALE',
            reference_id=sale.pk,
            description=f"Sales Invoice #{sale.invoice_no} ({sale.buyer_name})",
        ).first()
        if existing_entry:
            return existing_entry

        try:
            fiscal_year = sale.fiscal_year
        except FiscalYear.DoesNotExist:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
        if fiscal_year is None:
            raise AccountingError("No fiscal year is available for the sales journal.")

        items = []
        gross_sales = (sale.subtotal or Decimal('0.00')).quantize(Decimal('0.01'))
        discount = (sale.discount_total or Decimal('0.00')).quantize(Decimal('0.01'))
        vat = (sale.vat_total or Decimal('0.00')).quantize(Decimal('0.01'))
        grand_total = (sale.grand_total or Decimal('0.00')).quantize(Decimal('0.01'))

        # 1. DEBIT: Payment Accounts / Accounts Receivable
        if sale.payment_mode == 'SPLIT':
            for payment in sale.payment_transactions.filter(status='PAID'):
                p_acc_code = cls._resolve_payment_account(payment.payment_method)
                items.append({
                    'account_code': p_acc_code,
                    'debit': payment.amount,
                    'credit': Decimal('0.00')
                })
        else:
            acc_code = cls._resolve_payment_account(sale.payment_mode)
            # If sale is on Credit or customer ledger exists
            if sale.payment_status != 'PAID' and sale.customer and sale.customer.account:
                items.append({
                    'account_obj': sale.customer.account,
                    'debit': grand_total,
                    'credit': Decimal('0.00')
                })
            else:
                items.append({
                    'account_code': acc_code,
                    'debit': grand_total,
                    'credit': Decimal('0.00')
                })

        # 2. DEBIT: Sales Discounts Allowed
        if discount > Decimal('0.00'):
            items.append({
                'account_code': '3020',
                'debit': discount,
                'credit': Decimal('0.00')
            })

        # Legacy sales rows may contain the old text value "SALES A/C" in this FK column.
        sales_account = cls._get_account('3010')
        try:
            if sale.sales_ac_id:
                sales_account = sale.sales_ac
        except (Account.DoesNotExist, TypeError, ValueError):
            pass

        # 3. CREDIT: Sales Revenue
        items.append({
            'account_obj': sales_account,
            'debit': Decimal('0.00'),
            'credit': gross_sales
        })

        # 4. CREDIT: Output VAT Payable (Liability)
        if vat > Decimal('0.00'):
            items.append({
                'account_code': '2020',
                'debit': Decimal('0.00'),
                'credit': vat
            })

        # Reconcile legacy invoices whose stored round_off is stale or zero.
        round_off = (
            grand_total + discount - gross_sales - vat
        ).quantize(Decimal('0.01'))
        if round_off > Decimal('0.00'):
            items.append({
                'account_code': '3030',
                'debit': Decimal('0.00'),
                'credit': round_off,
            })
        elif round_off < Decimal('0.00'):
            items.append({
                'account_code': '3030',
                'debit': abs(round_off),
                'credit': Decimal('0.00'),
            })

        # --- POST REVENUE & TAX JOURNAL ENTRY ---
        rev_entry = cls.create_journal_entry(
            entry_date=timezone.now().date(),
            bs_date=sale.bs_date,
            description=f"Sales Invoice #{sale.invoice_no} ({sale.buyer_name})",
            reference_type='SALE',
            reference_id=sale.pk,
            fiscal_year=fiscal_year,
            items=items,
            created_by=sale.user
        )

        # --- POST COGS & INVENTORY ASSET ENTRY ---
        cogs_items = []
        total_cogs = Decimal('0.00')

        for item in sale.items.all():
            cost_price = getattr(item.variant, 'cost_price', Decimal('0.00')) or Decimal('0.00')
            total_cogs += (cost_price * item.quantity).quantize(Decimal('0.01'))

        if total_cogs > Decimal('0.00'):
            cogs_items = [
                {'account_code': '4010', 'debit': total_cogs, 'credit': Decimal('0.00')}, # Dr COGS
                {'account_code': '1200', 'debit': Decimal('0.00'), 'credit': total_cogs}  # Cr Inventory Asset
            ]
            if not JournalEntry.objects.filter(
                reference_type='SALE',
                reference_id=sale.pk,
                description=f"COGS Deduction for Invoice #{sale.invoice_no}",
            ).exists():
                cls.create_journal_entry(
                    entry_date=timezone.now().date(),
                    bs_date=sale.bs_date,
                    description=f"COGS Deduction for Invoice #{sale.invoice_no}",
                    reference_type='SALE',
                    reference_id=sale.pk,
                    fiscal_year=fiscal_year,
                    items=cogs_items,
                    created_by=sale.user
                )

        return rev_entry

    @staticmethod
    def _resolve_payment_account(method):
        mapping = {
            'CASH': '1010',
            'CARD': '1020',
            'BANK_TRANSFER': '1020',
            'FONEPAY': '1030',
            'CREDIT': '1100',
        }
        return mapping.get(str(method).upper(), '1010')