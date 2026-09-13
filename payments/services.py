from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import uuid

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from accounting.models import PaymentReceipt
from accounting.services import AccountingService

from .models import Payment

class PaymentProcessingService:
    @classmethod
    def record_payment(cls, sale, method, amount, reference=None, user=None, is_instant_settlement=False):
        """
        Records a payment towards a sale (supports Single, Digital Wallets, and Split Payments).
        """
        with transaction.atomic():
            status = 'PAID' if is_instant_settlement else 'PENDING'
            
            payment = Payment.objects.create(
                sale=sale,
                payment_method=method,
                amount=Decimal(str(amount)),
                status=status,
                internal_reference=reference,
                created_by=user,
                verified_at=timezone.now() if status == 'PAID' else None
            )

            if status == 'PAID':
                # Recalculate sale totals and update payment_status / sale_status
                sale.update_payment_summary()

                # If sale is fully completed, post GL double-entry journal records
                if sale.sale_status == 'COMPLETED':
                    AccountingService.post_sale_journal_entry(sale)

            return payment

    @classmethod
    def verify_digital_payment(cls, payment_id, gateway_ref, is_success, response_payload=None):
        """
        Webhook/Callback verification for digital wallets (eSewa, Khalti, Fonepay).
        """
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(pk=payment_id)
            
            if payment.status == 'PAID':
                return payment # Idempotency check

            if is_success:
                payment.status = 'PAID'
                payment.provider_reference = gateway_ref
                payment.verified_at = timezone.now()
                payment.save(update_fields=['status', 'provider_reference', 'verified_at', 'updated_at'])

                # Sync back to Sale
                sale = payment.sale
                sale.update_payment_summary()

                # Trigger Accounting Journal Postings
                if sale.sale_status == 'COMPLETED':
                    AccountingService.post_sale_journal_entry(sale)
            else:
                payment.status = 'FAILED'
                payment.failure_reason = str(response_payload or '')
                payment.save(update_fields=['status', 'failure_reason', 'updated_at'])

            return payment

class PaymentProcess:

    @staticmethod
    def generate_reference():
        import uuid

        return (
            f"GSMS-{timezone.now().strftime('%Y%m%d%H%M%S')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

    @staticmethod
    @transaction.atomic
    def create_payment(sale, payment_method, received_amount=None):

        payment_method = payment_method.upper()

        total_amount = Decimal(str(sale.grand_total))

        # -------------------------------------------------
        # CASH PAYMENT
        # -------------------------------------------------

        if payment_method == "CASH":

            if received_amount is None:
                raise ValueError("Received cash amount is required.")

            received_amount = Decimal(str(received_amount))

            if received_amount < total_amount:
                raise ValueError(
                    f"Insufficient payment. "
                    f"Required Rs. {total_amount}, "
                    f"received Rs. {received_amount}."
                )

            change_amount = received_amount - total_amount

            sale.tender_amount = received_amount
            sale.received_amount = received_amount
            sale.change_amount = change_amount
            sale.payment_mode = "CASH"
            sale.payment_status = "PAID"
            sale.sale_status = "COMPLETED"

            sale.save(
                update_fields=[
                    "tender_amount",
                    "received_amount",
                    "change_amount",
                    "payment_mode",
                    "payment_status",
                    "sale_status",
                ]
            )
            Payment.objects.create(
                sale=sale,
                payment_method='CASH',
                amount=total_amount,
                internal_reference=PaymentProcess.generate_reference(),
                status='PAID',
            )
            sale.update_payment_summary()
            AccountingService.post_sale_journal_entry(sale)

            return {
                "success": True,
                "payment_method": "CASH",
                "amount": total_amount,
                "received": received_amount,
                "change": change_amount,
                "status": "SUCCESS",
            }

        # -------------------------------------------------
        # CARD PAYMENT
        # -------------------------------------------------

        if payment_method == "CARD":

            received_amount = total_amount

            sale.tender_amount = received_amount
            sale.received_amount = received_amount
            sale.change_amount = Decimal("0.00")
            sale.payment_mode = "CARD"
            sale.payment_status = "PAID"
            sale.sale_status = "COMPLETED"

            sale.save(
                update_fields=[
                    "tender_amount",
                    "received_amount",
                    "change_amount",
                    "payment_mode",
                    "payment_status",
                    "sale_status",
                ]
            )
            Payment.objects.create(
                sale=sale,
                payment_method='CARD',
                amount=total_amount,
                internal_reference=PaymentProcess.generate_reference(),
                status='PAID',
            )
            sale.update_payment_summary()
            AccountingService.post_sale_journal_entry(sale)

            return {
                "success": True,
                "payment_method": "CARD",
                "amount": total_amount,
                "status": "SUCCESS",
            }

        # -------------------------------------------------
        # DIGITAL PAYMENT
        # -------------------------------------------------

        if payment_method in [
            "FONEPAY",
            "BANK_TRANSFER",
        ]:

            reference = PaymentProcess.generate_reference()

            payment = Payment.objects.create(
                sale=sale,
                payment_method=payment_method,
                amount=total_amount,
                internal_reference=reference,
                status="PENDING",
            )

            sale.payment_mode = payment_method
            sale.payment_status = "PENDING"

            sale.save(
                update_fields=[
                    "payment_mode",
                    "payment_status",
                ]
            )

            return {
                "success": True,
                "payment_method": payment_method,
                "payment_id": payment.transaction_id,
                "amount": total_amount,
                "reference": payment.internal_reference,
                "status": "PENDING",
            }

        raise ValueError(
            f"Unsupported payment method: {payment_method}"
        )

from urllib.parse import urlencode
from datetime import timedelta


class FonepayService:

    MERCHANT_CODE = "GSMS-DEMO-001"
    MERCHANT_NAME = "Green Supermarket"

    @staticmethod
    def generate_qr(payment):

        params = {
            "merchant": FonepayService.MERCHANT_CODE,
            "merchant_name": FonepayService.MERCHANT_NAME,
            "amount": str(payment.amount),
            "reference": payment.internal_reference,
            "currency": "NPR",
        }

        qr_payload = (
            "GSMS-DEMO-FONEPAY?"
            + urlencode(params)
        )

        payment.qr_payload = qr_payload
        payment.status = "PROCESSING"

        payment.expires_at = (
            timezone.now() + timedelta(minutes=10)
        )

        payment.save(
            update_fields=[
                "qr_payload",
                "status",
                "expires_at",
            ]
        )

        return payment
    
class PaymentVerificationService:

    @staticmethod
    @transaction.atomic
    def mark_success(payment_id, provider_transaction_id=None, provider_reference=None):
        payment = (
            Payment.objects
            .select_for_update()
            .select_related("sale")
            .get(transaction_id=payment_id)
        )

        if payment.status == "PAID":
            return payment

        if payment.status not in ["PENDING", "PROCESSING"]:
            raise ValueError(f"Payment cannot be completed. Current status: {payment.status}")

        sale = payment.sale

        # Update Payment Record
        payment.status = "PAID"
        payment.provider_transaction_id = provider_transaction_id
        payment.provider_reference = provider_reference
        payment.verified_at = timezone.now()
        payment.save(update_fields=["status", "provider_transaction_id", "provider_reference", "verified_at"])

        # Update Sale Record
        sale.tender_amount = payment.amount
        sale.received_amount = payment.amount
        sale.change_amount = Decimal("0.00")
        sale.payment_mode = payment.payment_method
        sale.save(update_fields=["tender_amount", "received_amount", "change_amount", "payment_mode"])
        sale.update_payment_summary()

        # Create Accounting Receipt
        PaymentReceipt.objects.get_or_create(
            payment=payment,
            defaults={
                "voucher_no": f"PR-{payment.internal_reference}",
                "party_type": "CUSTOMER",
                "payment_mode": payment.payment_method,
                "amount": payment.amount,
                "payment_date": timezone.now(),
                "reference_number": provider_reference or payment.internal_reference,
                "narration": f"Payment against invoice {sale.invoice_no}",
                "customer": sale.customer,
            },
        )

        if sale.sale_status == "COMPLETED":
            from accounting.services import AccountingService
            AccountingService.post_sale_journal_entry(sale)
        return payment