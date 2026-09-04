from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from products.models import ProductVariant
from suppliers.models import Supplier
from purchases.models import PurchaseDetail


class InventoryBatch(models.Model):
    class BatchStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        EXHAUSTED = 'EXHAUSTED', 'Exhausted'
        EXPIRED = 'EXPIRED', 'Expired'
        QUARANTINED = 'QUARANTINED', 'Quarantined / Hold'

    batch_id = models.AutoField(primary_key=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='batches')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, blank=True, null=True)
    purchase_detail = models.ForeignKey(PurchaseDetail, on_delete=models.SET_NULL, blank=True, null=True)
    
    batch_number = models.CharField(max_length=50, db_index=True)
    manufacture_date = models.DateField(blank=True, null=True)
    harvest_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(db_index=True)  # Indexed for FEFO speed
    received_date = models.DateField(auto_now_add=True)
    
    received_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    current_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    batch_status = models.CharField(
        max_length=20, 
        choices=BatchStatus.choices, 
        default=BatchStatus.ACTIVE,
        db_index=True
    )

    class Meta:
        db_table = 'inventory_batch'
        ordering = ['expiry_date', 'received_date']

    def __str__(self):
        return f"Batch: {self.batch_number} - {self.variant.product.product_name} (Stock: {self.current_quantity})"

    def save(self, *args, **kwargs):
        today = timezone.now().date()
        # Auto-update status depending on stock and expiry date
        if self.expiry_date and self.expiry_date < today:
            self.batch_status = self.BatchStatus.EXPIRED
        elif self.current_quantity <= Decimal('0.000'):
            self.batch_status = self.BatchStatus.EXHAUSTED
        super().save(*args, **kwargs)

    @property
    def abc_expiry_class(self):
        """ABC Expiry Categorization Method."""
        today = timezone.now().date()
        if self.expiry_date < today:
            return 'EXPIRED'
        days_left = (self.expiry_date - today).days
        if days_left <= 15:
            return 'A'  # Critical Urgency
        elif days_left <= 60:
            return 'B'  # Moderate Urgency
        return 'C'      # Safe Stock

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def days_until_expiry(self):
        if self.expiry_date:
            return (self.expiry_date - timezone.now().date()).days
        return None


class StockAdjustment(models.Model):
    class ReasonCode(models.TextChoices):
        EXPIRED = 'EXPIRED', 'Stock Expired'
        DAMAGED = 'DAMAGED', 'Damaged / Broken'
        THEFT = 'THEFT', 'Stolen / Missing'
        CORRECTION = 'CORRECTION', 'Inventory Audit Correction'
        RETURN = 'RETURN', 'Returned Goods Adjustment'

    adjustment_id = models.AutoField(primary_key=True)
    batch = models.ForeignKey(InventoryBatch, on_delete=models.CASCADE, related_name='adjustments')
    adjusted_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    quantity_change = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        help_text='Negative for write-off (-2.000), positive for audit gain (+2.000)'
    )
    reason_code = models.CharField(max_length=20, choices=ReasonCode.choices)
    loss_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_adjustment'
        ordering = ['-created_at']

    def __str__(self):
        return f"Adjustment #{self.adjustment_id} ({self.reason_code}): {self.quantity_change}"