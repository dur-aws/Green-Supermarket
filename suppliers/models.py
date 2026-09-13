
# Create your models here.

from django.db import models
from django.contrib.auth import get_user_model
from gsms import settings

User = get_user_model()

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
    account = models.ForeignKey('accounting.Account', models.DO_NOTHING, blank=True, null=True)
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
    

