# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    customer_code = models.CharField(unique=True, max_length=20)
    customer_name = models.CharField(max_length=100)
    phone = models.CharField(unique=True, max_length=20, blank=True, null=True)
    email = models.CharField(unique=True, max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=8,
        choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')],
        default='ACTIVE',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'customer'

    
    def __str__(self):
        return f"{self.customer_code} - {self.customer_name}"
    
    @property
    def transaction_count(self):
        # will connect to Sales app once that sprint is built
        from sales.models import Sales
        return Sales.objects.filter(customer=self).count()

    @property
    def current_scheme(self):
        count = self.transaction_count
        return CustomerScheme.objects.filter(
            minimum_transactions__lte=count,
            status='ACTIVE'
        ).filter(
            models.Q(maximum_transactions__gte=count) | models.Q(maximum_transactions__isnull=True)
        ).order_by('-minimum_transactions').first()

    @property
    def is_member(self):
        return self.membership_set.filter(status='ACTIVE').exists()



class CustomerScheme(models.Model):
    scheme_id = models.AutoField(primary_key=True)
    scheme_name = models.CharField(max_length=50)
    minimum_transactions = models.IntegerField()
    maximum_transactions = models.IntegerField(blank=True, null=True)
    discount_type = models.CharField(max_length=10, blank=True, null=True)
    discount_value = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=8, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'customer_scheme'
        
    def __str__(self):
        return self.scheme_name

class Membership(models.Model):
    membership_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey('customers.Customer', models.DO_NOTHING)
    membership_type = models.CharField(max_length=50)
    start_date = models.DateField()
    expiry_date = models.DateField()
    membership_fee = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=9, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'membership'
