from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import F
from django.utils import timezone
import bikram_sambat

from products.models import ProductVariant
from customers.models import Customer
from inventory.models import InventoryBatch
from .models import Sale, SaleItem
from .exceptions import (
    InsufficientStockError, InvalidQuantityError,
    InvalidDiscountError, PaymentMismatchError, SaleError
)

MAX_DISCOUNT_PERCENT = Decimal('30.00')


class InvoiceNumberService:
    @staticmethod
    def generate_next_number():
        """Generates pure numeric sequential invoice sequence (1, 2, 3...)."""
        with transaction.atomic():  # 👈 required for select_for_update
            last_sale = Sale.objects.select_for_update().order_by('-invoice_no').first()
            return (last_sale.invoice_no + 1) if (last_sale and last_sale.invoice_no) else 1


class SaleService:

    @staticmethod
    @transaction.atomic
    def create_sale(customer_id, items_data, payments_data, cashier, idempotency_key, narration='', tender_amount='', received_amount='', change_amount='' , bs_date='', fiscal_year=''):
        if idempotency_key:
            existing = Sale.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing, False

        if not items_data:
            raise InvalidQuantityError("Cart is empty")

        customer = Customer.objects.get(pk=customer_id)
        today_ad = timezone.now().date()

        subtotal = Decimal('0.00')
        discount_total = Decimal('0.00')
        taxable_amount = Decimal('0.00')
        non_taxable_amount = Decimal('0.00')
        vat_total = Decimal('0.00')
        validated_items = []

        for item in items_data:
            quantity = Decimal(str(item['quantity']))
            discount = Decimal(str(item.get('discount', '0')))
            
            if quantity <= Decimal('0.000'):
                raise InvalidQuantityError("Quantity must be greater than zero")

            if 'variant_id' in item:
                variant = ProductVariant.objects.get(pk=item['variant_id'])
            elif 'product_id' in item:
                variant = ProductVariant.objects.filter(product_id=item['product_id']).first()
                if not variant:
                    raise SaleError("No variant found for product")
            else:
                raise SaleError("Item must include variant_id or product_id")

            unit_price = Decimal(str(item.get('price', getattr(variant, 'selling_price', getattr(variant, 'cost_price', '0')))))

            batches = InventoryBatch.objects.select_for_update().filter(
                variant=variant,
                batch_status='ACTIVE',
                expiry_date__gte=today_ad,
                current_quantity__gt=0
            ).order_by('expiry_date', 'batch_id')

            available_stock = sum(b.current_quantity for b in batches)
            if available_stock < quantity:
                raise InsufficientStockError(
                    f"Insufficient stock for {variant.variant_name}. Available: {available_stock}"
                )

            line_gross = (unit_price * quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            max_allowed_discount = (line_gross * MAX_DISCOUNT_PERCENT / Decimal('100.00')).quantize(Decimal('0.01'))
            if discount > max_allowed_discount:
                raise InvalidDiscountError(f"Discount exceeds maximum allowed limit on {variant.variant_name}")

            line_after_discount = line_gross - discount
            
            # --- Dynamic Item-Level VAT Logic ---
            # Retrieve VAT flag from payload or product variant model
            is_vatable = item.get('is_vatable', getattr(variant, 'is_vatable', getattr(variant.product, 'is_vatable', True)))
            
            if is_vatable:
                raw_vat = item.get('vat_percent', getattr(variant, 'vat_percent', getattr(variant.product, 'vat_percent', Decimal('13.00'))))
                vat_percent = Decimal(str(raw_vat if raw_vat is not None else '13.00'))
            else:
                vat_percent = Decimal('0.00')

            if is_vatable and vat_percent > Decimal('0.00'):
                line_vat = (line_after_discount * vat_percent / Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                taxable_amount += line_after_discount
                vat_total += line_vat
            else:
                line_vat = Decimal('0.00')
                non_taxable_amount += line_after_discount

            line_total = line_after_discount + line_vat
            subtotal += line_gross
            discount_total += discount

            validated_items.append({
                'variant': variant,
                'batches': batches,
                'quantity': quantity,
                'unit_price': unit_price,
                'discount': discount,
                'vat_percent': vat_percent,
                'is_vatable': is_vatable,
                'net_subtotal': line_after_discount,
                'line_total': line_total,
            })

        raw_grand_total = taxable_amount + non_taxable_amount + vat_total
        grand_total = raw_grand_total.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        round_off = (grand_total - raw_grand_total).quantize(Decimal('0.01'))

        if grand_total > Decimal('5000.00') and customer.pk == 1 and not getattr(customer, 'pan_number', None):
            raise SaleError("IRD Mandate: Customer PAN/Name is required for billing above NPR 5,000.")

        invoice_no = InvoiceNumberService.generate_next_number()

        # Calculate change dynamically on the backend
        tender_val = Decimal(str(tender_amount or '0.00'))
        received_val = Decimal(str(received_amount or '0.00'))
        
        # Received amount defaults to tender_amount if left blank
        if received_val == Decimal('0.00') and tender_val > Decimal('0.00'):
            received_val = tender_val

        change_val = max(Decimal('0.00'), (received_val - grand_total).quantize(Decimal('0.01')))

        sale = Sale.objects.create(
        invoice_no=invoice_no,
        fiscal_year=fiscal_year,
        customer=customer,
        customer_pan=getattr(customer, 'pan_number', None),
        buyer_name=getattr(customer, 'name', 'Walk-in Customer'),
        user=cashier,
        bs_date=bs_date,
        taxable_amount=taxable_amount,
        non_taxable_amount=non_taxable_amount,
        subtotal=subtotal,
        discount_total=discount_total,
        vat_total=vat_total,
        round_off=round_off,
        grand_total=grand_total,
        tender_amount=tender_amount,
        received_amount=received_amount,
        change_amount=change_amount,
        sale_status='COMPLETED',
        narration=narration,
        idempotency_key=idempotency_key,
    )

        for vi in validated_items:
            qty_needed = vi['quantity']
            primary_batch = None

            for batch in vi['batches']:
                if qty_needed <= 0:
                    break
                if primary_batch is None:
                    primary_batch = batch

                deduct = min(batch.current_quantity, qty_needed)
                batch.current_quantity -= deduct
                if batch.current_quantity == Decimal('0.000'):
                    batch.batch_status = 'EXHAUSTED'
                batch.save()
                qty_needed -= deduct

            SaleItem.objects.create(
                sale=sale,
                variant=vi['variant'],
                batch=primary_batch,
                quantity=vi['quantity'],
                unit_price=vi['unit_price'],
                discount_amount=vi['discount'],
                vat_percent=vi['vat_percent'],
                net_subtotal=vi['net_subtotal'],
                line_total=vi['line_total'],
            )

        

            # StockHistory.objects.create(
            #     variant=vi['variant'],
            #     quantity=-vi['quantity'],
            #     reason='SALE',
            #     reference=str(invoice_no),
            # )#[cite: 2]

        # # 5. Process Payments
        # paid_sum = Decimal('0.00')
        # for p in payments_data:
        #     amount = Decimal(str(p['amount']))
        #     if amount <= 0:
        #         continue
            
        #     if p['method'] in ['FONEPAY', 'ESEWA', 'KHALTI', 'BANK_TRANSFER', 'CONNECT_IPS'] and not p.get('reference_no'):
        #         raise SaleError(f"Reference/Transaction ID is required for {p['method']} payment.")

        #     Payment.objects.create(
        #         sale=sale,
        #         method=p['method'],
        #         amount=amount,
        #         reference_no=p.get('reference_no'),
        #     )#[cite: 2]
        #     paid_sum += amount

        # if paid_sum < grand_total:
        #     raise PaymentMismatchError(
        #         f"Payment received ({paid_sum}) is less than grand total ({grand_total})"
        #     )#[cite: 2]

        return sale, True


class SaleCancelService:

    @staticmethod
    @transaction.atomic
    def cancel_sale(sale_id, cancelled_by):
        """
        Reverses stock deduction on original inventory batches and records CANCELLED status.
        Never deletes rows to maintain full audit trails.
        """
        sale = Sale.objects.select_for_update().get(pk=sale_id)

        if sale.status != 'COMPLETED':
            raise SaleError(f"Cannot cancel a sale with status {sale.status}")

        for item in sale.items.select_related('variant', 'batch').all():
            if item.batch:
                item.batch.current_quantity += item.quantity
                if item.batch.batch_status == 'EXHAUSTED':
                    item.batch.batch_status = 'ACTIVE'
                item.batch.save()

            StockHistory.objects.create(
                variant=item.variant,
                quantity=item.quantity,  # Returning positive stock balance
                reason='SALE_CANCELLED',
                reference=str(sale.invoice_no),
            )

        sale.status = 'CANCELLED'
        sale.save(update_fields=['status'])
        return sale