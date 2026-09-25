from django.db import models
from django.db.models import Q, Sum, Avg, Max
from django.core.exceptions import ValidationError

class Customer(models.Model):
    TYPE_REGULAR = 'REGULAR'
    TYPE_REGISTERED = 'REGISTERED'
    TYPE_MEMBER = 'MEMBER'
    CUSTOMER_TYPE_CHOICES = [
        (TYPE_REGULAR, 'Regular'),
        (TYPE_REGISTERED, 'Registered'),
        (TYPE_MEMBER, 'Member'),
    ]

    customer_id = models.AutoField(primary_key=True)
    customer_code = models.CharField(unique=True, max_length=20)
    customer_name = models.CharField(max_length=100)
    customer_type = models.CharField(
        max_length=10, choices=CUSTOMER_TYPE_CHOICES, default=TYPE_REGULAR
    )
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

        # Auto-create the customer ledger under Accounts Receivable (1210).
        if not self.account:
            parent_ar = Account.objects.filter(account_code='1210').first()
            acc, _ = Account.objects.get_or_create(
                account_code=f"1210.{self.customer_code}",
                defaults={
                    'account_name': f"Customer - {self.customer_name}",
                    'account_type': 'ASSET',
                    'parent_account': parent_ar,
                    'is_active': True
                }
            )
            self.account = acc
            super().save(update_fields=['account'])

    def delete(self, *args, **kwargs):
        self.status = 'INACTIVE'
        self.save(update_fields=['status'])
        return (1, {self._meta.label: 1})

    @property
    def transaction_count(self):
        from sales.models import Sale
        return Sale.objects.filter(customer=self, sale_status='COMPLETED').count()

    @property
    def total_spending(self):
        from sales.models import Sale
        return Sale.objects.filter(customer=self, sale_status='COMPLETED').aggregate(
            total=Sum('grand_total')
        )['total'] or 0

    @property
    def average_bill(self):
        from sales.models import Sale
        return Sale.objects.filter(customer=self, sale_status='COMPLETED').aggregate(
            average=Avg('grand_total')
        )['average'] or 0

    @property
    def total_discount(self):
        from sales.models import Sale
        return Sale.objects.filter(customer=self, sale_status='COMPLETED').aggregate(
            total=Sum('discount_total')
        )['total'] or 0

    @property
    def last_purchase(self):
        from sales.models import Sale
        return Sale.objects.filter(
            customer=self, sale_status='COMPLETED'
        ).aggregate(last=Max('sale_date'))['last']

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
        return self.memberships.filter(status='ACTIVE').exists()


class CustomerScheme(models.Model):
    scheme_id = models.AutoField(primary_key=True)
    scheme_name = models.CharField(max_length=50)
    minimum_transactions = models.IntegerField()
    maximum_transactions = models.IntegerField(blank=True, null=True)
    discount_type = models.CharField(
        max_length=10,
        choices=[('PERCENT', 'Percent'), ('FIXED', 'Fixed')],
        default='PERCENT',
    )
    discount_value = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(
        max_length=8,
        choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')],
        default='ACTIVE',
    )

    class Meta:
        
        db_table = 'customer_scheme'
        
    def __str__(self):
        return self.scheme_name


class Membership(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]
    membership_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='memberships')
    membership_type = models.CharField(max_length=50)
    start_date = models.DateField()
    expiry_date = models.DateField()
    membership_fee = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=9, choices=STATUS_CHOICES, default='ACTIVE')

    class Meta:
        
        db_table = 'membership'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status == 'ACTIVE':
            Customer.objects.filter(pk=self.customer_id).update(customer_type=Customer.TYPE_MEMBER)
        elif not Membership.objects.filter(customer_id=self.customer_id, status='ACTIVE').exists():
            Customer.objects.filter(pk=self.customer_id).update(customer_type=Customer.TYPE_REGISTERED)