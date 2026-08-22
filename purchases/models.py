# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from accounts.models import Role
from suppliers.models import Supplier, User

class PurchaseOrder(models.Model):
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
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
    order_date = models.DateField()
    received_date = models.DateField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tds_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tds_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_payable_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = True
        db_table = 'purchase_order'

    

class ProductVariant(models.Model):
    variant_id = models.AutoField(primary_key=True)
    variant_name = models.CharField(max_length=150)

    class Meta:
        managed = False
        db_table = 'product_variant'
    def __str__(self):
        return self.variant_name

class PurchaseDetail(models.Model):
    purchase_detail_id = models.AutoField(primary_key=True)
    purchase = models.ForeignKey(PurchaseOrder, models.DO_NOTHING)
    particular = models.CharField(max_length=255, null= True)
    variant = models.ForeignKey('ProductVariant', models.DO_NOTHING)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField(blank=True, null=True)
    ordered_quantity = models.DecimalField(max_digits=10, decimal_places=3, db_comment='Qty requested')
    agreed_unit_price = models.DecimalField(max_digits=10, decimal_places=2, db_comment='Initial PO price')
    received_quantity = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True, db_comment='Actual catch-weight received')
    actual_unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_comment='Price charged on final supplier invoice')

    class Meta:
        managed = True
        db_table = 'purchase_detail'

    
    
    
