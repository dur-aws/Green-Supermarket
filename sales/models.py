from decimal import Decimal
from django.db import models
from django.conf import settings
from products.models import ProductVariant
from inventory.models import InventoryBatch
from customers.models import Customer


class Sale(models.Model):
    class SaleStatus(models.TextChoices):
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        
    class PaymentStatus(models.TextChoices):
        PAID = 'PAID', 'Paid'
        PARTIAL = 'PARTIAL', 'Partially Paid'
        UNPAID = 'UNPAID', 'Unpaid'
    
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        CARD = 'CARD', 'Card / POS'
        FONEPAY = 'FONEPAY', 'Fonepay (QR)'

    sales_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True)
    customer_pan = models.CharField(max_length=20, blank=True, null=True)
    buyer_name = models.CharField(max_length=100, default="Walk-in Customer")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sales_processed'
    )
    invoice_no = models.IntegerField(unique=True, editable=False)
    fiscal_year = models.CharField(max_length=10, default="2083/84")
    
    # Dual Dates & Exact Time
    bs_date = models.CharField(max_length=15, blank=True, null=True)  # E.g., 2083-05-14
    sale_date = models.DateTimeField(auto_now_add=True)
    
    # Financial Totals
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    non_taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    vat_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=Decimal('0.00'))
    round_off = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Payment & Idempotency
    tender_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    received_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    sales_ac = models.CharField(max_length=50, default="SALES A/C")
    payment_status = models.CharField(
        max_length=14, 
        choices=PaymentStatus.choices, 
        default=PaymentStatus.PAID
    )
    payment_mode = models.CharField(
        max_length=10, 
        choices=PaymentMethod.choices, 
        default=PaymentMethod.CASH
    )
    sale_status = models.CharField(
        max_length=20, 
        choices=SaleStatus.choices,
        default=SaleStatus.COMPLETED 
    )
    narration = models.TextField(blank=True, null=True)
    idempotency_key = models.CharField(max_length=64, unique=True, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'sale'
        ordering = ['-sale_date']

    def __str__(self):
        return f"{self.invoice_no} - {self.grand_total}"


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
        managed = True
        db_table = 'sale_item'

    def __str__(self):
        return f"{self.variant.variant_name} x {self.quantity}"