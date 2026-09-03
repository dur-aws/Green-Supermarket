from django.utils import timezone
from decimal import Decimal

from django.db import models
from django.db.models.aggregates import Sum

from units.models import UnitOfMeasure
from categories.models import Category



class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    brand = models.CharField(max_length=100, blank=True, null=True)
    product_name = models.CharField(max_length=150)
    is_organic = models.BooleanField(default=False)
    is_eco_friendly = models.BooleanField(default=False)
    shelf_life_days = models.IntegerField(blank=True, null=True, help_text="Typical shelf life in days")
    status = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'product'

    def __str__(self):
        return self.product_name

    @property
    def code(self):
        """Display-only code like P-001. Not stored in DB — derived from product_id."""
        return f"P-{self.product_id:03d}"
    def __str__(self):
        return self.code
 
    

class ProductVariant(models.Model):
    variant_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(unique=True, max_length=50)
    barcode = models.CharField(unique=True, max_length=100, blank=True, null=True)
    variant_name = models.CharField(max_length=150)
    
    primary_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='primary_variants')
    secondary_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.SET_NULL, blank=True, null=True, related_name='secondary_variants')
    
    is_catch_weight = models.BooleanField(default=False)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_vatable = models.BooleanField(default=False)
    
    reorder_level = models.DecimalField(max_digits=10, decimal_places=3, default=10.000)
    target_stock_level = models.DecimalField(max_digits=10, decimal_places=3, default=50.000)
    abc_class = models.CharField(max_length=1, blank=True, null=True, choices=[('A', 'High Value'), ('B', 'Medium Value'), ('C', 'Low Value')])
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'product_variant'

    def __str__(self):
        return f"{self.product.product_name} - {self.variant_name} ({self.weight}{self.unit})"
    
    def __str__(self):
        return self.primary_uom
    
    

    @property
    def total_active_stock(self):
        """Calculates total stock available across all non-expired, active batches."""
        today = timezone.now().date()
        result = self.batches.filter(
            batch_status='ACTIVE',
            expiry_date__gte=today,
            current_quantity__gt=0
        ).aggregate(total=Sum('current_quantity'))['total']
        
        return result or Decimal('0.000')

    @property
    def nearest_expiry_date(self):
        """Gets the earliest expiry date from active stock (FEFO priority)."""
        today = timezone.now().date()
        next_batch = self.batches.filter(
            batch_status='ACTIVE',
            expiry_date__gte=today,
            current_quantity__gt=0
        ).order_by('expiry_date').first()
        
        return next_batch.expiry_date if next_batch else None

    @property
    def vat_status(self):
        """Display-only % like 13%/0%. Not stored in DB — derived from is_vatable."""
        return "13" if self.is_vatable else "0"
    
    def __str__(self):
        return f"{self.variant_name} {self.vat_status}"

    
    
    @property
    def stock_status(self):
    # Check is_active on variant or parent product
        variant_active = getattr(self, 'is_active', True)
        product_active = getattr(self.product, 'status', True)
        stock = self.total_active_stock

        if not variant_active or not product_active:
            return "disable"

        elif stock <= Decimal('0.000'):
            return "out-of-stock"
        elif stock <= self.reorder_level:
            return "low-stock"
        
        return "active"
