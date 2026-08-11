from django.db import models

# Create your models here.
# dashboard/models.py


class Sales(models.Model):
    sales_id = models.AutoField(primary_key=True)
    sale_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'sales'
        
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'category'


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.DO_NOTHING, db_column='category_id')
    product_name = models.CharField(max_length=150)
    status = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'product'



class SalesDetail(models.Model):
    sales_detail_id = models.AutoField(primary_key=True)
    sales = models.ForeignKey(Sales, on_delete=models.DO_NOTHING, db_column='sales_id')
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, db_column='product_id')
    quantity = models.IntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'sales_detail'


class Inventory(models.Model):
    inventory_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, db_column='product_id')
    quantity = models.IntegerField()
    reorder_level = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'inventory'


class Expense(models.Model):
    expense_id = models.AutoField(primary_key=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    expense_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'expense'