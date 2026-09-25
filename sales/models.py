from decimal import Decimal
from django.db import models
from django.db.models import Q
import uuid
from django.conf import settings
from products.models import ProductVariant
from inventory.models import InventoryBatch
from customers.models import Customer
from accounting.models import FiscalYear, JournalEntry, Account
from django.core.exceptions import ValidationError
from payments.choices import PAYMENT_METHOD_CHOICES, PAYMENT_STATUS_CHOICES, SALE_STATUS_CHOICES

class Sale(models.Model):
    sales_id = models.AutoField(primary_key=True)
    invoice_no = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, null=True, blank=True)
    buyer_name = models.CharField(max_length=150, blank=True, null=True)
   
    
    # Financial Totals
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    non_taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    vat_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    grand_total_in_words = models.CharField(max_length=255, blank=True, null=True)
    idempotency_key = models.CharField(unique=True, max_length=64, blank=True, null=True)
     # Payment & Idempotency
    narration = models.TextField(blank=True, null=True)
    round_off = models.DecimalField(max_digits=6, decimal_places=2)
    tender_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    received_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
        
    # Settlement Breakdown
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    due_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Methods & Statuses
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    sale_status = models.CharField(max_length=20, choices=SALE_STATUS_CHOICES, default='DRAFT')

    # Fiscal & Accounting
    fiscal_year = models.ForeignKey(
        'accounting.FiscalYear',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text='Required for new sales; legacy rows are backfilled during migration.',
    )
    sales_ac = models.ForeignKey('accounting.Account', on_delete=models.PROTECT, related_name='sale_records', null=True, blank=True)
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sales',
    )
    bs_date = models.CharField(max_length=10)
    sale_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'sale'
        ordering = ['-sale_date']
        constraints = [
            models.CheckConstraint(
                condition=Q(subtotal__gte=0) & Q(discount_total__gte=0)
                & Q(taxable_amount__gte=0) & Q(non_taxable_amount__gte=0)
                & Q(vat_total__gte=0) & Q(grand_total__gte=0)
                & Q(paid_amount__gte=0) & Q(due_amount__gte=0),
                name='sale_non_negative_totals',
            ),
        ]
    
    def __str__(self):
        return f"{self.invoice_no} - {self.grand_total}"
    
    def clean(self):
        # Prevent saving invoices in closed fiscal years.
        if self.fiscal_year_id and self.fiscal_year.is_closed:
            raise ValidationError(f"Cannot save invoice: Fiscal Year {self.fiscal_year.name} is closed.")

    def update_payment_summary(self):
        """Recalculates paid & due totals from all SUCCESSFUL payments."""
        successful_payments = self.payment_transactions.filter(status='PAID')
        total_paid = sum(p.amount for p in successful_payments)
        self.paid_amount = total_paid
        self.due_amount = max(Decimal('0.00'), self.grand_total - total_paid)

        if self.paid_amount >= self.grand_total:
            self.payment_status = 'PAID'
            self.sale_status = 'COMPLETED'
        elif self.paid_amount > Decimal('0.00'):
            self.payment_status = 'PARTIAL'
        else:
            self.payment_status = 'PENDING'

        self.save(update_fields=['paid_amount', 'due_amount', 'payment_status', 'sale_status'])
        
    @staticmethod
    def number_to_words(amount):
        from num2words import num2words
        
        amount = Decimal(str(amount))
        integer_part = int(amount)
        decimal_part = int((amount - integer_part) * 100)

        words = num2words(integer_part, lang='en').title() + " Rupees"
        if decimal_part > 0:
            words += " and " + num2words(decimal_part, lang='en').title() + " Paisa"
        return words

    def save(self, *args, **kwargs):
        if self.sales_ac_id is None:
            from accounting.services import AccountingService
            self.sales_ac = AccountingService._get_account('4100')
        if self.grand_total:
            self.grand_total_in_words = self.number_to_words(self.grand_total)
        if self._state.adding:
            self.full_clean()
        else:
            self.clean()
        return super().save(*args, **kwargs)


class SaleItem(models.Model):
    sale_item_id = models.AutoField(primary_key=True)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='sale_items')
    batch = models.ForeignKey(InventoryBatch, on_delete=models.PROTECT, null=True, blank=True)
    
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # VAT fields made nullable
    vat_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=Decimal('0.00'))
    vat_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, default=Decimal('0.00'))
    
    net_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'sale_item'
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name='sale_item_positive_quantity'),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name='sale_item_non_negative_price'),
            models.CheckConstraint(condition=Q(discount_amount__gte=0), name='sale_item_non_negative_discount'),
            models.CheckConstraint(condition=Q(vat_percent__gte=0), name='sale_item_non_negative_vat_percent'),
            models.CheckConstraint(condition=Q(net_subtotal__gte=0) & Q(line_total__gte=0), name='sale_item_non_negative_totals'),
        ]

    def __str__(self):
        return f"{self.variant.variant_name} x {self.quantity}"


class SalesReturn(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        RECEIVED = 'RECEIVED', 'Received'
        INSPECTED = 'INSPECTED', 'Inspected'
        APPROVED = 'APPROVED', 'Approved'
        CREDITED = 'CREDITED', 'Credited'
        REFUNDED = 'REFUNDED', 'Refunded'
        CANCELLED = 'CANCELLED', 'Cancelled'

    rma_id = models.BigAutoField(primary_key=True)
    rma_number = models.CharField(max_length=32, unique=True, default='')
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='return_requests')
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_rmas')
    created_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(null=True, blank=True)
    inspected_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.rma_number:
            self.rma_number = f"RMA-{uuid.uuid4().hex[:10].upper()}"
        if not self.customer_id and self.sale_id:
            self.customer_id = self.sale.customer_id
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.rma_number} - {self.sale.invoice_no}"


class SalesReturnItem(models.Model):
    rma = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT, related_name='return_items')
    quantity_requested = models.DecimalField(max_digits=10, decimal_places=3)
    quantity_received = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('0.000'))
    unit_refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    source_batch = models.ForeignKey(InventoryBatch, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['rma', 'sale_item'], name='unique_rma_sale_item')]


class InventoryReturnReceipt(models.Model):
    class Status(models.TextChoices):
        APPROVED = 'APPROVED', 'Approved'
        VOID = 'VOID', 'Void'

    receipt_id = models.BigAutoField(primary_key=True)
    receipt_number = models.CharField(max_length=32, unique=True, default='')
    rma = models.OneToOneField(SalesReturn, on_delete=models.PROTECT, related_name='inventory_receipt')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.APPROVED)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='received_return_receipts')
    inspected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='inspected_return_receipts')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"IRR-{uuid.uuid4().hex[:10].upper()}"
        return super().save(*args, **kwargs)


class InventoryReturnItem(models.Model):
    class Condition(models.TextChoices):
        RESALABLE = 'RESALABLE', 'Resalable'
        DAMAGED = 'DAMAGED', 'Damaged'
        EXPIRED = 'EXPIRED', 'Expired'

    receipt = models.ForeignKey(InventoryReturnReceipt, on_delete=models.CASCADE, related_name='items')
    return_item = models.OneToOneField(SalesReturnItem, on_delete=models.PROTECT, related_name='receipt_item')
    condition = models.CharField(max_length=10, choices=Condition.choices)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    target_batch = models.ForeignKey(InventoryBatch, on_delete=models.PROTECT, null=True, blank=True, related_name='returned_stock')
    disposition_note = models.TextField(blank=True)


class CreditMemo(models.Model):
    class Status(models.TextChoices):
        APPROVED = 'APPROVED', 'Approved'
        PENDING_REFUND = 'PENDING_REFUND', 'Pending Refund'
        PAID = 'PAID', 'Paid'
        COMPLETED = 'COMPLETED', 'Completed'

    memo_id = models.BigAutoField(primary_key=True)
    memo_number = models.CharField(max_length=32, unique=True, default='')
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='credit_memos')
    receipt = models.OneToOneField(InventoryReturnReceipt, on_delete=models.PROTECT, related_name='credit_memo')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPROVED)
    journal_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.PROTECT, null=True, blank=True, related_name='credit_memos')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_credit_memos')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.memo_number:
            self.memo_number = f"CM-{uuid.uuid4().hex[:10].upper()}"
        return super().save(*args, **kwargs)

