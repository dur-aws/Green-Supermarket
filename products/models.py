# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(unique=True, max_length=100)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'category'
    
    def __str__(self):
        return self.category_name
    

class Unit(models.Model):
    unit_id = models.AutoField(primary_key=True)
    unit_name = models.CharField(unique=True, max_length=50)
    notation = models.CharField(max_length=30)
    
    def __str__(self):
        return self.unit_name
    
    class Meta:
        managed = False
        db_table = 'unit'
        


 
class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.DO_NOTHING, db_column='category_id')
    brand = models.CharField(max_length=100, blank=True, null=True)
    unit = models.ForeignKey(Unit, on_delete=models.DO_NOTHING, db_column='unit_id')
    product_name = models.CharField(max_length=150)
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    vat_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    expiry_date = models.DateField(blank=True, null=True)
    status = models.IntegerField(default=1)  # 1 = enabled for sale, 0 = disabled — NOT stock status
 
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
 
    @property
    def stock_status(self):
        """
        Returns a clean status string:
        - Disabled (if product.status == 0)
        - Out of Stock (if quantity == 0)
        - Low Stock (if quantity <= reorder_level)
        - Active (if product.status == 1 and stock > reorder_level)
        """
        try:
            inv = self.inventory
        except Inventory.DoesNotExist:
            return "no-inventory"

        # First check product status
        if self.status == 0:
            return "disable"

        # Then check inventory levels
        if inv.quantity == 0:
            return "out-of-stock"
        if inv.quantity <= inv.reorder_level:
            return "low-stock"

        # Finally, if status is enabled and stock is fine
        return "active"
        
            

 

class Inventory(models.Model):
    inventory_id = models.AutoField(primary_key=True)
    product = models.OneToOneField(Product, on_delete=models.DO_NOTHING, db_column='product_id', related_name='inventory')
    quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=0)
 
    class Meta:
        managed = False
        db_table = 'inventory'
 


class Supplier(models.Model):
    supplier_id = models.AutoField(primary_key=True)
    supplier_name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(unique=True, max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'supplier'


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(unique=True, max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'customer'
