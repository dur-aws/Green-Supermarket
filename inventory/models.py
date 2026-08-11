# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.conf import settings
from products.models import Product

class StockHistory(models.Model):
    TRANSACTION_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJUSTMENT', 'Adjustment'),
    ]

    stock_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_id', related_name='stock_history')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, db_column='user_id')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()  # positive for IN, negative for OUT/decrease adjustments
    reason = models.CharField(max_length=255, blank=True, null=True)
    transaction_date = models.DateField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'stock_history'
        ordering = ['-stock_id']

    def __str__(self):
        return f"{self.transaction_type} - {self.product.product_name} ({self.quantity})"