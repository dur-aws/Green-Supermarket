
# Create your models here.

from django.db import models
from django.contrib.auth import get_user_model

from gsms import settings

User = get_user_model()
class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(unique=True, max_length=50)

class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(unique=True, max_length=150)
    password = models.CharField(max_length=128)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.SmallIntegerField()
    is_superuser = models.IntegerField()
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    last_login = models.DateTimeField(blank=True, null=True)
    date_joined = models.DateTimeField()
    role = models.ForeignKey(Role, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user'
class Supplier(models.Model):
    supplier_id = models.AutoField(primary_key=True)
    # Link to authentication user account for portal access
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.DO_NOTHING, 
        related_name='supplier_profile',
        null=True, 
        blank=True
    )
    supplier_name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True)
    pan_vat_number = models.CharField(max_length=20, blank=True, null=True)
    is_organic_certified = models.BooleanField(default=False)
    certification_details = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'supplier'

    def __str__(self):
        return self.supplier_name

    @property
    def portal_username(self):
        if not self.user_id:
            return None
        return User.objects.filter(pk=self.user_id).values_list('username', flat=True).first()
    
class PurchaseOrder(models.Model):
    purchase_id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey('Supplier', models.DO_NOTHING)
    received_by_user = models.ForeignKey('User', models.DO_NOTHING)
    purchase_date = models.DateField()
    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_status = models.CharField(max_length=7)

    class Meta:
        managed = False
        db_table = 'purchase_order'
