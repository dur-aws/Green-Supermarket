from datetime import timedelta
from urllib.parse import urlencode

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
    @transaction.atomic
    def record_purchase_payment(cls, purchase, method, amount, reference=None, user=None, is_instant_settlement=True):
        """Record a full or partial supplier payment and its accounting receipt."""
        purchase = purchase.__class__.objects.select_for_update().get(pk=purchase.pk)
        purchase.update_payment_summary()
        amount = Decimal(str(amount)).quantize(Decimal('0.01'))
        if amount <= 0:
            raise ValueError('Payment amount must be greater than zero.')
        if amount > purchase.due_amount:
            raise ValueError(f'Payment cannot exceed the due amount of {purchase.due_amount}.')

        status = 'PAID' if is_instant_settlement else 'PENDING'
        payment = Payment.objects.create(
            purchase=purchase,
            payment_method=method,
            amount=amount,
            status=status,
            internal_reference=reference or PaymentProcess.generate_reference(),
            created_by=user,
            verified_at=timezone.now() if status == 'PAID' else None,
        )
        if status == 'PAID':
            cls._settle_purchase_payment(payment, user=user)
        return payment

    @staticmethod
    def _settle_purchase_payment(payment, user=None):
        purchase = payment.purchase
        purchase.update_payment_summary()
        AccountingService.post_purchase_payment_journal_entry(payment, created_by=user)
        PaymentReceipt.objects.get_or_create(
            payment=payment,
            defaults={
                'voucher_no': f'PR-{payment.internal_reference}',
                'party_type': 'SUPPLIER',
                'payment_mode': payment.payment_method,
                'amount': payment.amount,
                'payment_date': timezone.now(),
                'reference_number': payment.internal_reference,
                'narration': f'Payment against purchase #{purchase.purchase_id}',
                'supplier': purchase.supplier,
            },
        )
        return purchase

    @classmethod
    @transaction.atomic
    def record_payment(cls, sale, method, amount, reference=None, user=None, is_instant_settlement=False):
        """Record one actual settlement payment against a sale.

        CREDIT is not a settlement method.  A credit/partial-credit sale is
        represented by the sale's payment_mode and customer A/R; only the
        amount actually received is stored here as a Payment row.
        """
        sale = sale.__class__.objects.select_for_update().get(pk=sale.pk)
        sale.update_payment_summary()

        method = str(method or '').upper().strip()
        if method in {'', 'CREDIT', 'SPLIT'}:
            raise ValueError('Payment method must be an actual settlement method (e.g. CASH, CARD or FONEPAY).')

        amount = Decimal(str(amount)).quantize(Decimal('0.01'))
        if amount <= Decimal('0.00'):
            raise ValueError('Payment amount must be greater than zero.')
        if amount > sale.due_amount:
            raise ValueError(f'Payment cannot exceed the due amount of {sale.due_amount}.')

        status = 'PAID' if is_instant_settlement else 'PENDING'
        payment = Payment.objects.create(
            sale=sale,
            payment_method=method,
            amount=amount,
            status=status,
            internal_reference=reference or PaymentProcess.generate_reference(),
            created_by=user,
            verified_at=timezone.now() if status == 'PAID' else None,
        )

        if status == 'PAID':
            sale.update_payment_summary()

            # First settlement creates the complete sale journal, including
            # any outstanding A/R. Later settlements only clear A/R.
            if sale.journal_entry_id:
                journal = AccountingService.post_sale_payment_journal_entry(
                    payment, created_by=user
                )
            else:
                journal = AccountingService.post_sale_journal_entry(
                    sale, created_by=user
                )
                if sale.journal_entry_id != journal.entry_id:
                    sale.journal_entry = journal
                    sale.save(update_fields=['journal_entry'])

            PaymentReceipt.objects.get_or_create(
                payment=payment,
                defaults={
                    'voucher_no': f'PR-{payment.internal_reference}',
                    'party_type': 'CUSTOMER',
                    'payment_mode': payment.payment_method,
                    'amount': payment.amount,
                    'payment_date': timezone.now(),
                    'reference_number': payment.internal_reference,
                    'narration': f'Payment against invoice {sale.invoice_no}',
                    'customer': sale.customer,
                },
            )

        return payment

    @classmethod
    @transaction.atomic
    def verify_digital_payment(cls, payment_id, gateway_ref, is_success, response_payload=None):
        """Verify a pending digital payment and post its accounting entry exactly once."""
        payment = (
            Payment.objects.select_for_update()
            .select_related('sale', 'purchase')
            .get(pk=payment_id)
        )

        if payment.status == 'PAID':
            return payment

        if not is_success:
            payment.status = 'FAILED'
            payment.failure_reason = str(response_payload or '')
            payment.save(update_fields=['status', 'failure_reason', 'updated_at'])
            return payment

        payment.status = 'PAID'
        payment.provider_reference = gateway_ref
        payment.verified_at = timezone.now()
        payment.save(update_fields=['status', 'provider_reference', 'verified_at', 'updated_at'])

        if payment.purchase_id:
            cls._settle_purchase_payment(payment)
            return payment

        sale = payment.sale
        sale = sale.__class__.objects.select_for_update().get(pk=sale.pk)
        sale.update_payment_summary()

        if sale.journal_entry_id:
            journal = AccountingService.post_sale_payment_journal_entry(payment)
        else:
            journal = AccountingService.post_sale_journal_entry(sale)
            if sale.journal_entry_id != journal.entry_id:
                sale.journal_entry = journal
                sale.save(update_fields=['journal_entry'])

        PaymentReceipt.objects.get_or_create(
            payment=payment,
            defaults={
                'voucher_no': f'PR-{payment.internal_reference}',
                'party_type': 'CUSTOMER',
                'payment_mode': payment.payment_method,
                'amount': payment.amount,
                'payment_date': timezone.now(),
                'reference_number': gateway_ref or payment.internal_reference,
                'narration': f'Payment against invoice {sale.invoice_no}',
                'customer': sale.customer,
            },
        )
        return payment


class PaymentProcess:

    @staticmethod
    def generate_reference():
        return (
            f"GSMS-{timezone.now().strftime('%Y%m%d%H%M%S')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

    @staticmethod
    @transaction.atomic
    def create_payment(sale, payment_method, received_amount=None, allow_credit=True, user=None):
        """Create a POS payment without duplicating Payment/accounting logic.

        CASH may be partial when allow_credit=True. The unpaid balance remains
        customer A/R. FONEPAY is created as PENDING and is posted only after
        verification.
        """
        payment_method = str(payment_method or '').upper().strip()
        sale = sale.__class__.objects.select_for_update().get(pk=sale.pk)
        sale.update_payment_summary()
        total_amount = Decimal(str(sale.grand_total)).quantize(Decimal('0.01'))
        due_before = sale.due_amount

        if payment_method == 'CREDIT':
            if not allow_credit:
                raise ValueError('Credit payment is not allowed for this transaction.')
            payment_amount = Decimal('0.00')
            received = Decimal(str(received_amount or '0.00'))
            if received > 0:
                raise ValueError('For a credit sale, send the actual settlement method (for example CASH), not CREDIT.')
            sale.payment_mode = 'CREDIT'
            sale.payment_status = 'PENDING'
            sale.sale_status = 'COMPLETED'
            sale.tender_amount = Decimal('0.00')
            sale.received_amount = Decimal('0.00')
            sale.change_amount = Decimal('0.00')
            sale.save(update_fields=['payment_mode', 'payment_status', 'sale_status', 'tender_amount', 'received_amount', 'change_amount'])
            sale.update_payment_summary()
            if not sale.journal_entry_id:
                journal = AccountingService.post_sale_journal_entry(sale)
                if sale.journal_entry_id != journal.entry_id:
                    sale.journal_entry = journal
                    sale.save(update_fields=['journal_entry'])
            return {'success': True, 'payment_method': 'CREDIT', 'amount': Decimal('0.00'), 'received': Decimal('0.00'), 'change': Decimal('0.00'), 'status': 'SUCCESS'}

        if payment_method not in {'CASH', 'CARD', 'BANK_TRANSFER', 'FONEPAY'}:
            raise ValueError(f'Unsupported payment method: {payment_method}')

        if payment_method == 'CASH':
            if received_amount is None:
                raise ValueError('Received cash amount is required.')
            tender = Decimal(str(received_amount)).quantize(Decimal('0.01'))
            if tender <= Decimal('0.00'):
                raise ValueError('Received cash amount must be greater than zero.')
            payment_amount = min(tender, due_before)
            change = max(Decimal('0.00'), tender - due_before)

            if tender < due_before and not allow_credit:
                raise ValueError(f'Insufficient payment. Required Rs. {due_before}, received Rs. {tender}.')

            # Mark a partial cash sale as CREDIT before accounting is posted,
            # so the sale journal debits Cash for the received amount and
            # customer A/R for the outstanding balance.
            if tender < due_before:
                sale.payment_mode = 'CREDIT'
                sale.payment_status = 'PARTIAL'
                sale.sale_status = 'COMPLETED'
                sale.save(update_fields=['payment_mode', 'payment_status', 'sale_status'])

            payment = PaymentProcessingService.record_payment(
                sale, 'CASH', payment_amount, user=user, is_instant_settlement=True
            )
            sale = sale.__class__.objects.select_for_update().get(pk=sale.pk)
            sale.tender_amount = tender
            sale.received_amount = payment_amount
            sale.change_amount = change
            sale.payment_mode = 'CASH' if sale.due_amount == 0 else 'CREDIT'
            sale.payment_status = 'PAID' if sale.due_amount == 0 else 'PARTIAL'
            sale.sale_status = 'COMPLETED'
            sale.save(update_fields=['tender_amount', 'received_amount', 'change_amount', 'payment_mode', 'payment_status', 'sale_status'])
            return {'success': True, 'payment_method': 'CASH', 'amount': payment_amount, 'received': tender, 'change': change, 'status': 'SUCCESS'}

        if payment_method in {'CARD', 'BANK_TRANSFER'}:
            if due_before <= Decimal('0.00'):
                raise ValueError('This sale has no outstanding balance.')
            payment = PaymentProcessingService.record_payment(
                sale, payment_method, due_before, user=user, is_instant_settlement=True
            )
            sale = sale.__class__.objects.select_for_update().get(pk=sale.pk)
            sale.tender_amount = due_before
            sale.received_amount = due_before
            sale.change_amount = Decimal('0.00')
            sale.payment_mode = payment_method
            sale.payment_status = 'PAID'
            sale.sale_status = 'COMPLETED'
            sale.save(update_fields=['tender_amount', 'received_amount', 'change_amount', 'payment_mode', 'payment_status', 'sale_status'])
            return {'success': True, 'payment_method': payment_method, 'amount': due_before, 'status': 'SUCCESS'}

        # Digital payment: create a pending payment for the outstanding balance.
        if due_before <= Decimal('0.00'):
            raise ValueError('This sale has no outstanding balance.')
        reference = PaymentProcess.generate_reference()
        payment = PaymentProcessingService.record_payment(
            sale, 'FONEPAY', due_before, reference=reference, user=user, is_instant_settlement=False
        )
        sale = sale.__class__.objects.select_for_update().get(pk=sale.pk)
        sale.payment_mode = 'FONEPAY'
        sale.payment_status = 'PENDING'
        sale.save(update_fields=['payment_mode', 'payment_status'])
        return {'success': True, 'payment_method': 'FONEPAY', 'payment_id': payment.transaction_id, 'amount': due_before, 'reference': payment.internal_reference, 'status': 'PENDING'}


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

        if payment.purchase_id:
            payment.status = "PAID"
            payment.provider_transaction_id = provider_transaction_id
            payment.provider_reference = provider_reference
            payment.verified_at = timezone.now()
            payment.save(update_fields=["status", "provider_transaction_id", "provider_reference", "verified_at"])
            PaymentProcessingService._settle_purchase_payment(payment)
            return payment

        sale = payment.sale

        # Update Payment Record
        payment.status = "PAID"
        payment.provider_transaction_id = provider_transaction_id
        payment.provider_reference = provider_reference
        payment.verified_at = timezone.now()
        payment.save(update_fields=["status", "provider_transaction_id", "provider_reference", "verified_at"])

        # Update Sale Record
        total_paid = sum(
            (p.amount for p in sale.payment_transactions.filter(status='PAID')),
            Decimal('0.00'),
        )
        sale.tender_amount = total_paid
        sale.received_amount = total_paid
        sale.change_amount = Decimal("0.00")
        if sale.payment_mode != 'SPLIT':
            sale.payment_mode = payment.payment_method
        sale.save(update_fields=["tender_amount", "received_amount", "change_amount", "payment_mode"])
        sale.update_payment_summary()

        # A pending invoice has no sale journal yet; post the invoice once.
        # An existing credit invoice needs a payment journal instead.
        if sale.journal_entry_id:
            AccountingService.post_sale_payment_journal_entry(payment)
        else:
            AccountingService.post_sale_journal_entry(sale)

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

        return payment