from django.db import models
from accounts.models import Role
from suppliers.models import Supplier, User
from products.models import ProductVariant
from accounting.models import JournalEntry


class PurchaseOrder(models.Model):
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('DELIVERED', 'Delivered by supplier'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('UNPAID', 'Unpaid'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Paid'),
    ]

    order_status = models.CharField(
        max_length=20, 
        choices=ORDER_STATUS_CHOICES, 
        default='PENDING'
    )
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='UNPAID'
    )
    purchase_id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.DO_NOTHING,
        related_name='purchase_orders'  
    )
    received_by_user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.DO_NOTHING,
        related_name='received_purchase_orders'  
    )
    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    
    order_date = models.DateField(blank=True, null=True)
    delivery_date = models.DateField(blank=True, null=True)
    received_date = models.DateField(blank=True, null=True)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tds_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    tds_amount = models.DecimalField(max_digits=12, decimal_places=2)
    freight_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True, null = True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_payable_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True, null=True)
    due_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True, null=True)
    journal_entry = models.ForeignKey(JournalEntry, models.DO_NOTHING, blank=True, null=True)

    def update_payment_summary(self):
        from django.db.models import Sum

        paid = self.purchase_payments.filter(status='PAID').aggregate(
            total=Sum('amount')
        )['total'] or 0
        returned = self.purchase_returns.aggregate(total=Sum('total_value'))['total'] or 0
        effective_payable = max(0, self.net_payable_amount - returned)
        self.paid_amount = min(paid, effective_payable)
        self.due_amount = max(0, effective_payable - paid)
        if paid >= effective_payable:
            self.payment_status = 'PAID'
        elif paid > 0:
            self.payment_status = 'PARTIAL'
        else:
            self.payment_status = 'UNPAID'
        self.save(update_fields=['paid_amount', 'due_amount', 'payment_status'])

    @property
    def returned_amount(self):
        from django.db.models import Sum

        return self.purchase_returns.aggregate(total=Sum('total_value'))['total'] or 0

    @property
    def effective_payable_amount(self):
        return max(0, self.net_payable_amount - self.returned_amount)

    class Meta:
        managed = True
        db_table = 'purchase_order'

    


class PurchaseDetail(models.Model):
    purchase_detail_id = models.AutoField(primary_key=True)
    purchase = models.ForeignKey(PurchaseOrder, models.DO_NOTHING)
    variant = models.ForeignKey(ProductVariant, models.DO_NOTHING)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    batch_no = models.CharField(max_length=100, blank=True, null=True)
    manufacture_date = models.DateField(blank=True, null = True)
    harvest_date = models.DateField(blank=True, null = True)
    expiry_date = models.DateField(blank=True, null = True)
    ordered_quantity = models.DecimalField(max_digits=10, decimal_places=3, db_comment='Qty requested')
    agreed_unit_price = models.DecimalField(max_digits=10, decimal_places=2, db_comment='Initial PO price')
    received_quantity = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True, db_comment='Actual catch-weight received')
    actual_unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_comment='Price charged on final supplier invoice')
    SUPPLIER_RESPONSE_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPT', 'Accept'),
        ('NOT_AVAILABLE', 'Not available'),
    ]
    supplier_response = models.CharField(max_length=20, choices=SUPPLIER_RESPONSE_CHOICES, default='PENDING')
    supplier_responded_at = models.DateTimeField(blank=True, null=True)
    class Meta:
        managed = True
        db_table = 'purchase_detail'



class VendorPurchaseReceipt(models.Model):
    purchase = models.OneToOneField(
        PurchaseOrder, on_delete=models.PROTECT, related_name='vendor_receipt'
    )
    receipt_number = models.CharField(max_length=50, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.PROTECT, related_name='vendor_receipts'
    )

    class Meta:
        ordering = ['-issued_at']

