from django.db import models


class UnitOfMeasure(models.Model):
    uom_id = models.AutoField(primary_key=True)
    unit_name = models.CharField(unique=True, max_length=50)
    notation = models.CharField(max_length=10)
    is_weight_based = models.BooleanField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        managed = False
        db_table = 'unit_of_measure'

class ProductVariant(models.Model):
    variant_id = models.AutoField(primary_key=True)
    # product = models.ForeignKey(Product, models.DO_NOTHING)
    sku = models.CharField(unique=True, max_length=50)
    barcode = models.CharField(unique=True, max_length=100, blank=True, null=True)
    variant_name = models.CharField(max_length=150)
    primary_uom = models.ForeignKey('UnitOfMeasure', models.DO_NOTHING)
    secondary_uom = models.ForeignKey('UnitOfMeasure', models.DO_NOTHING, related_name='productvariant_secondary_uom_set', blank=True, null=True)
    is_catch_weight = models.IntegerField(blank=True, null=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    vat_percent = models.DecimalField(max_digits=5, decimal_places=2)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=3)
    target_stock_level = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        managed = False
        db_table = 'product_variant'

