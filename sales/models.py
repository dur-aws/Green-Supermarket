from django.db import models
from django.conf import settings
from products.models import Product, Customer


class Sale(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]

    invoice_no = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales')
    sale_date = models.DateTimeField(auto_now_add=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    round_off = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='COMPLETED')
    narration = models.TextField(blank=True, null=True)
    idempotency_key = models.CharField(max_length=64, unique=True)

    class Meta:
        managed = False
        db_table = 'tbl_sale'
        ordering = ['-sale_date']

    def __str__(self):
        return self.invoice_no

    @property
    def paid_total(self):
        return sum(p.amount for p in self.payments.all())

    @property
    def payment_status(self):
        if self.paid_total >= self.grand_total:
            return 'PAID'
        elif self.paid_total > 0:
            return 'PARTIAL'
        return 'UNPAID'


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')

    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)   # snapshot, not live product.price
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'tbl_sale_item'

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Payment(models.Model):
    METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('WALLET', 'Digital Wallet'),
    ]

    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='payments')
    method = models.CharField(max_length=15, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    reference_no = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tbl_payment'


class SaleReturn(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='returns')
    return_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, null=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        managed = False
        db_table = 'tbl_sale_return'


class SaleReturnItem(models.Model):
    sale_return = models.ForeignKey(SaleReturn, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT)
    quantity_returned = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'tbl_sale_return_item'