from django.db import models
from accounts.models import Role
from suppliers.models import Supplier, User
from products.models import ProductVariant

class PurchaseOrder(models.Model):
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
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
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_payable_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = True
        db_table = 'purchase_order'

    


class PurchaseDetail(models.Model):
    purchase_detail_id = models.AutoField(primary_key=True)
    purchase = models.ForeignKey(PurchaseOrder, models.DO_NOTHING)
    variant = models.ForeignKey(ProductVariant, models.DO_NOTHING)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    manufacture_date = models.DateField(blank=True, null = True)
    harvest_date = models.DateField(blank=True, null = True)
    expiry_date = models.DateField(blank=True, null = True)
    ordered_quantity = models.DecimalField(max_digits=10, decimal_places=3, db_comment='Qty requested')
    agreed_unit_price = models.DecimalField(max_digits=10, decimal_places=2, db_comment='Initial PO price')
    received_quantity = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True, db_comment='Actual catch-weight received')
    actual_unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_comment='Price charged on final supplier invoice')
    class Meta:
        managed = True
        db_table = 'purchase_detail'

