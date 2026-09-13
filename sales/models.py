from decimal import Decimal
from django.db import models
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
    customer_pan = models.CharField(max_length=20, blank=True, null=True)
    
    # Financial Totals
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    non_taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    vat_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
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
    fiscal_year = models.ForeignKey('accounting.FiscalYear', on_delete=models.PROTECT)
    sales_ac = models.ForeignKey('accounting.Account', on_delete=models.PROTECT, related_name='sale_records', null=True, blank=True)
    bs_date = models.CharField(max_length=10)
    sale_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
            
            db_table = 'sale'
            ordering = ['-sale_date']
    
    def __str__(self):
        return f"{self.invoice_no} - {self.grand_total}"
    
    def clean(self):
        # Prevent saving invoices in closed fiscal years.
        if self.fiscal_year_id and self.fiscal_year.is_closed:
            raise ValidationError(f"Cannot save invoice: Fiscal Year {self.fiscal_year.name} is closed.")

    def save(self, *args, **kwargs):
        if self.sales_ac_id is None:
            from accounting.services import AccountingService
            self.sales_ac = AccountingService._get_account('3010')
        if self._state.adding:
            self.full_clean()
        else:
            self.clean()
        return super().save(*args, **kwargs)
    

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

    def __str__(self):
        return f"{self.variant.variant_name} x {self.quantity}"

