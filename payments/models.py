from django.db import models
from decimal import Decimal
from django.conf import settings
from .choices import PAYMENT_METHOD_CHOICES, PAYMENT_STATUS_CHOICES

class Payment(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    sale = models.ForeignKey('sales.Sale', on_delete=models.CASCADE, related_name='payment_transactions')

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
        return f"Payment #{self.transaction_id} - Sale #{self.sale.invoice_no} ({self.payment_method}: {self.amount})"





   
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
    ]

    refund_id = models.BigAutoField(primary_key=True)

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="refunds"
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


    