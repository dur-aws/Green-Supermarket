from django.db import models
from decimal import Decimal
from django.conf import settings
from .choices import PAYMENT_METHOD_CHOICES, PAYMENT_STATUS_CHOICES

class Payment(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    sale = models.ForeignKey('sales.Sale', on_delete=models.CASCADE, related_name='payment_transactions', null=True, blank=True)
    purchase = models.ForeignKey(
        'purchases.PurchaseOrder', on_delete=models.CASCADE,
        related_name='purchase_payments', null=True, blank=True
    )

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
        
    amount = models.DecimalField(
                max_digits=12,
                decimal_places=2
            )
        
    internal_reference = models.CharField(
                max_length=150,
                unique=True,
                null=True
            )
        
    provider_transaction_id = models.CharField(
                max_length=150,
                blank=True,
                null=True
            )
        
    provider_reference = models.CharField(
                max_length=150,
                blank=True,
                null=True
            )
        
    

    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    # Gateway / Reference Details
    qr_payload = models.TextField(
                blank=True,
                null=True
            )
        
    expires_at = models.DateTimeField(
                blank=True,
                null=True
            )
        
    verified_at = models.DateTimeField(blank=True, null=True)
        
    failure_reason = models.TextField(
                blank=True,
                null=True
            )
        
    created_at = models.DateTimeField(
                auto_now_add=True
            )
        
    updated_at = models.DateTimeField(
                auto_now=True
            )
        
    
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'payment'
        

    def __str__(self):
        party = f"Sale #{self.sale.invoice_no}" if self.sale_id else f"Purchase #{self.purchase_id}"
        return f"Payment #{self.transaction_id} - {party} ({self.payment_method}: {self.amount})"





   
class FonepayTransaction(models.Model):

    STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("EXPIRED", "Expired"),
    ]

    fonepay_id = models.BigAutoField(primary_key=True)

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name="fonepay_transaction"
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    merchant_code = models.CharField(
        max_length=100
    )

    transaction_reference = models.CharField(
        max_length=150,
        unique=True
    )

    provider_transaction_id = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    qr_payload = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="CREATED"
    )

    response_code = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    response_message = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "fonepay_transaction"

    def __str__(self):
        return self.transaction_reference


class PaymentRefund(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("PAID", "Paid"),
        ("COMPLETED", "Completed"),
    ]

    refund_id = models.BigAutoField(primary_key=True)

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="refunds"
    )

    credit_memo = models.OneToOneField(
        'sales.CreditMemo', on_delete=models.PROTECT, related_name='payment_refund',
        null=True, blank=True
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    refund_reference = models.CharField(
        max_length=100,
        unique=True
    )

    provider_refund_id = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    refund_method = models.CharField(max_length=20, blank=True, null=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='confirmed_refunds'
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry', on_delete=models.PROTECT,
        null=True, blank=True, related_name='refund_records'
    )

    reason = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    class Meta:
        db_table = "payment_refund"


    