from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError

class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    customer_code = models.CharField(unique=True, max_length=20)
    customer_name = models.CharField(max_length=100)
    pan_vat_number = models.CharField(max_length=20, blank=True, null=True, help_text="IRD PAN/VAT number for Tax Billing")
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
    account = models.ForeignKey(
        'accounting.Account', 
        on_delete=models.PROTECT, 
        blank=True, 
        null=True,
        related_name='customer_ledgers'
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        
        db_table = 'customer'

    def __str__(self):
        return f"{self.customer_code} - {self.customer_name}"

    def save(self, *args, **kwargs):
        from accounting.models import Account
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Auto-create Ledger Account under Accounts Receivable (1100)
        if not self.account:
            parent_ar = Account.objects.filter(account_code='1100').first()
            acc, _ = Account.objects.get_or_create(
                account_code=f"1100.{self.customer_code}",
                defaults={
                    'account_name': f"Customer - {self.customer_name}",
                    'account_type': 'ASSET',
                    'parent_account': parent_ar,
                    'is_active': True
                }
            )
            self.account = acc
            super().save(update_fields=['account'])

    @property
    def transaction_count(self):
        from sales.models import Sale
        return Sale.objects.filter(customer=self).count()

    @property
    def current_scheme(self):
        count = self.transaction_count
        return CustomerScheme.objects.filter(
            minimum_transactions__lte=count,
            status='ACTIVE'
        ).filter(
            Q(maximum_transactions__gte=count) | Q(maximum_transactions__isnull=True)
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
        
        db_table = 'customer_scheme'
        
    def __str__(self):
        return self.scheme_name


class Membership(models.Model):
    membership_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    membership_type = models.CharField(max_length=50)
    start_date = models.DateField()
    expiry_date = models.DateField()
    membership_fee = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=9, blank=True, null=True)

    class Meta:
        
        db_table = 'membership'