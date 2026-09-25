from django.db import models

# Create your models here.
from django.conf import settings

from django.core.exceptions import ValidationError
import nepali_datetime

# ==============================================================================
# 1. ENHANCED EXISTING CORE ACCOUNTING MODELS
# ==============================================================================

class Account(models.Model):
    ACCOUNT_TYPE_CHOICES = (
        ('ASSET', 'Asset'),
        ('LIABILITY', 'Liability'),
        ('EQUITY', 'Equity'),
        ('REVENUE', 'Revenue'),
        ('EXPENSE', 'Expense'),
    )

    account_id = models.AutoField(primary_key=True)
    account_code = models.CharField(unique=True, max_length=20)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPE_CHOICES)
    parent_account = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_accounts')
    is_active = models.BooleanField(default=True)

    class Meta:
     
        db_table = 'account'

    def __str__(self):
        return f"{self.account_code} - {self.account_name}"

class FiscalYear(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=10, unique=True, help_text="Format: 2080/81")
    start_date_bs = models.CharField(max_length=10, help_text="YYYY-MM-DD (Shrawan 1)")
    end_date_bs = models.CharField(max_length=10, help_text="YYYY-MM-DD (Ashadh End)")
    is_active = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date_bs']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure only one fiscal year is active at a time
        if self.is_active:
            FiscalYear.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"FY {self.name}"

class JournalEntry(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_POSTED = 'POSTED'
    STATUS_REVERSED = 'REVERSED'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_POSTED, 'Posted'),
        (STATUS_REVERSED, 'Reversed'),
    )
    REFERENCE_TYPE_CHOICES = (
        ('SALE', 'Sales Invoice'),
        ('PURCHASE', 'Purchase Order'),
        ('ADJUST', 'Stock Adjustment/Wastage'),
        ('PAYMENT', 'Payment Settlement'),
        ('EXPENSE', 'Expense Voucher'),
        ('MANUAL', 'Manual Journal Voucher'),
    )

    entry_id = models.AutoField(primary_key=True)
    entry_date = models.DateField()
    bs_date = models.CharField(max_length=10, blank=True, null=True)
    description = models.CharField(max_length=255)
    reference_type = models.CharField(max_length=10, choices=REFERENCE_TYPE_CHOICES)
    reference_id = models.IntegerField(null=True, blank=True)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='journal_entries'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='posted_journal_entries'
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reversed_journal_entries'
    )
    reversed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'journal_entry'

    def clean(self):
        if self.fiscal_year and self.fiscal_year.is_closed:
            raise ValidationError(f"Cannot post journal entries to closed Fiscal Year {self.fiscal_year.name}.")

    def save(self, *args, **kwargs):
        if self.pk:
            previous = type(self).objects.get(pk=self.pk)
            if previous.status == self.STATUS_DRAFT and self.status not in {self.STATUS_DRAFT, self.STATUS_POSTED}:
                raise ValidationError('A draft journal entry can only be saved or posted.')
            if previous.status == self.STATUS_POSTED and self.status not in {self.STATUS_POSTED, self.STATUS_REVERSED}:
                raise ValidationError('A posted journal entry can only be reversed.')
            if previous.status == self.STATUS_REVERSED and self.status != self.STATUS_REVERSED:
                raise ValidationError('A reversed journal entry cannot change status.')
            if previous.status in {self.STATUS_POSTED, self.STATUS_REVERSED}:
                protected = {'entry_date', 'bs_date', 'description', 'reference_type', 'reference_id', 'fiscal_year_id', 'created_by_id'}
                if any(getattr(self, field) != getattr(previous, field) for field in protected):
                    raise ValidationError('Posted and reversed journal entries are immutable.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status != self.STATUS_DRAFT:
            raise ValidationError('Only draft journal entries can be deleted.')
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"JV-{self.entry_id} ({self.reference_type} #{self.reference_id})"


class JournalItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='items')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    class Meta:
        db_table = 'journal_item'

    def clean(self):
        if self.debit < 0 or self.credit < 0:
            raise ValidationError("Debit and Credit values cannot be negative.")
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("A single line item cannot contain both debit and credit amounts.")

    def save(self, *args, **kwargs):
        if self.entry_id and JournalEntry.objects.filter(
            pk=self.entry_id
        ).exclude(status=JournalEntry.STATUS_DRAFT).exists():
            raise ValidationError('Only draft journal entries can be edited.')
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.entry.status != JournalEntry.STATUS_DRAFT:
            raise ValidationError('Only draft journal entries can be edited.')
        return super().delete(*args, **kwargs)

# ==============================================================================
# 2. NECESSARY ADDITIONS FOR NEPALESE RETAIL COMPLIANCE & SETTLEMENTS
# ==============================================================================



class PaymentReceipt(models.Model):

    PARTY_TYPE_CHOICES = [
        ("CUSTOMER", "Customer"),
        ("SUPPLIER", "Supplier"),
        ("OTHER", "Other"),
    ]

    receipt_id = models.BigAutoField(primary_key=True)

    voucher_no = models.CharField(
        max_length=50,
        unique=True
    )

    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="receipt"
    )

    party_type = models.CharField(
        max_length=10,
        choices=PARTY_TYPE_CHOICES
    )

    payment_mode = models.CharField(
        max_length=20
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_date = models.DateTimeField()

    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    narration = models.TextField(
        blank=True,
        null=True
    )

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "payment_receipt"

    def __str__(self):
        return self.voucher_no

