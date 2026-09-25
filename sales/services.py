from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
import nepali_datetime

from accounting.models import Account, FiscalYear
from payments.models import Payment
from payments.choices import PAYMENT_METHOD_CHOICES
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
    def generate_next_number(fiscal_year: FiscalYear):
        """
        Generates sequential invoice numbers scoped to a Fiscal Year.
        Format: <FY Code>-<Sequence>
        Example: 2083/84-001, 2083/84-002
        """
        with transaction.atomic():
            locked_fy = FiscalYear.objects.select_for_update().get(pk=fiscal_year.pk)
            qs = Sale.objects.filter(fiscal_year=locked_fy)

            last_sale = qs.order_by('-invoice_no').first()

            if last_sale and last_sale.invoice_no:
                # Extract sequence part after the dash
                try:
                    last_seq = int(last_sale.invoice_no.split('-')[-1])
                except ValueError:
                    last_seq = 0
                next_seq = last_seq + 1
            else:
                next_seq = 1

            # Format with leading zeros (e.g., 001, 002)
            return f"{fiscal_year.name}-{next_seq:03d}"

class SaleService:

    @staticmethod
    @transaction.atomic
    def create_sale(
        customer_id, 
        items_data, 
        payments_data, 
        cashier, 
        fiscal_year=None,
        idempotency_key=None, 
        narration='', 
        tender_amount='', 
        received_amount='', 
        change_amount='', 
        
        bs_date='', 
        overall_discount_amount=Decimal('0.00'),
        overall_discount_percent=Decimal('0.00')
    ):
        if idempotency_key:
            existing = Sale.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing, False

        if not items_data:
            raise InvalidQuantityError("Cart is empty")
        
        # --- 1. DYNAMICALLY RESOLVE & VALIDATE FISCAL YEAR ---
        active_fy = None
        if isinstance(fiscal_year, FiscalYear):
            active_fy = fiscal_year
        elif fiscal_year:
            if str(fiscal_year).isdigit():
                active_fy = FiscalYear.objects.filter(pk=int(fiscal_year)).first()
            else:
                active_fy = FiscalYear.objects.filter(name=str(fiscal_year)).first()

        if not active_fy:
            if bs_date:
                try:
                    # Clean bs_date string if it contains extra characters
                    clean_bs_date = bs_date.split(' ')[0]
                    np_date = nepali_datetime.date.from_str(clean_bs_date)
                    year, month = np_date.year, np_date.month
                    if month >= 4:
                        start_year, end_year = year, year + 1
                    else:
                        start_year, end_year = year - 1, year
                    fy_code = f"{start_year}/{str(end_year)[-2:]}"
                    active_fy = FiscalYear.objects.filter(name=fy_code).first()
                except Exception:
                    pass

        if not active_fy:
            active_fy = FiscalYear.objects.filter(is_active=True).first()

        if not active_fy:
            raise SaleError("No active Fiscal Year configured in the system.")

        if getattr(active_fy, 'is_closed', False):
            raise SaleError(f"Cannot record sale: Fiscal Year {active_fy.name} is closed.")

        customer = Customer.objects.get(pk=customer_id)
        scheme = customer.current_scheme
        if scheme and overall_discount_amount == Decimal('0.00') and overall_discount_percent == Decimal('0.00'):
            if scheme.discount_type == 'PERCENT':
                overall_discount_percent = scheme.discount_value
            else:
                overall_discount_amount = scheme.discount_value
        today_ad = timezone.now().date()

        subtotal = Decimal('0.00')
        item_discount_total = Decimal('0.00')
        taxable_amount = Decimal('0.00')
        non_taxable_amount = Decimal('0.00')
        vat_total = Decimal('0.00')
        validated_items = []

        for item in items_data:
            quantity = Decimal(str(item['quantity']))
            discount = Decimal(str(item.get('discount', '0.00')))
            
            if quantity <= Decimal('0.000'):
                raise InvalidQuantityError("Quantity must be greater than zero")
            if discount < Decimal('0.00'):
                raise InvalidDiscountError("Discount cannot be negative")

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
                    f"Insufficient stock for {variant.product.product_name} {variant.variant_name}. Available: {available_stock}"
                )

            line_gross = (unit_price * quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            max_allowed_discount = (line_gross * MAX_DISCOUNT_PERCENT / Decimal('100.00')).quantize(Decimal('0.01'))
            if discount > max_allowed_discount:
                raise InvalidDiscountError(f"Discount exceeds maximum allowed limit on {variant.variant_name}")

            line_after_discount = line_gross - discount
            
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
            item_discount_total += discount

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

        # --- CALCULATE OVERALL BILL DISCOUNT ---
        overall_disc = Decimal(str(overall_discount_amount or '0.00'))
        overall_pct = Decimal(str(overall_discount_percent or '0.00'))

        if overall_disc < Decimal('0.00'):
            raise InvalidDiscountError("Bill discount cannot be negative")
        if overall_pct < Decimal('0.00') or overall_pct > MAX_DISCOUNT_PERCENT:
            raise InvalidDiscountError(
                f"Bill discount percentage must be between 0 and {MAX_DISCOUNT_PERCENT}%"
            )
        
        if overall_pct > Decimal('0.00'):
            net_before_bill_discount = taxable_amount + non_taxable_amount
            overall_disc = (net_before_bill_discount * overall_pct / Decimal('100.00')).quantize(Decimal('0.01'))

        if overall_disc > taxable_amount + non_taxable_amount:
            raise InvalidDiscountError("Bill discount cannot exceed the bill value")

        total_final_discount = (item_discount_total + overall_disc).quantize(Decimal('0.01'))
        if overall_disc > Decimal('0.00'):
            net_before_bill_discount = taxable_amount + non_taxable_amount
            if net_before_bill_discount > Decimal('0.00'):
                discount_ratio = overall_disc / net_before_bill_discount
                taxable_amount = (taxable_amount * (Decimal('1.00') - discount_ratio)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                non_taxable_amount = (non_taxable_amount * (Decimal('1.00') - discount_ratio)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                vat_total = sum(
                    (
                        item['net_subtotal'] * (Decimal('1.00') - discount_ratio)
                        * item['vat_percent'] / Decimal('100.00')
                    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    for item in validated_items if item['is_vatable']
                )
                for item in validated_items:
                    item['net_subtotal'] = (
                        item['net_subtotal'] * (Decimal('1.00') - discount_ratio)
                    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    item['line_total'] = (
                        item['net_subtotal']
                        + (item['net_subtotal'] * item['vat_percent'] / Decimal('100.00'))
                    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        raw_grand_total = taxable_amount + non_taxable_amount + vat_total
        grand_total = raw_grand_total.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        round_off = (grand_total - raw_grand_total).quantize(Decimal('0.01'))

        
        # --- 2. GENERATE INVOICE NUMBER BASED ON ACTIVE FY ---
        invoice_no = InvoiceNumberService.generate_next_number(fiscal_year=active_fy)

        # --- PAYMENT VALIDATION / SALE PAYMENT STATE ---
        tender_val = Decimal(str(tender_amount or '0.00'))
        received_val = Decimal(str(received_amount or '0.00'))
        if received_val == Decimal('0.00') and tender_val > Decimal('0.00'):
            received_val = tender_val

        valid_payment_methods = {choice[0] for choice in PAYMENT_METHOD_CHOICES}
        normalized_payments = []
        for raw_payment in payments_data or []:
            method = str(raw_payment.get('method', '')).upper().strip()
            if method not in valid_payment_methods:
                raise SaleError(f'Unsupported payment method: {method or "(empty)"}')
            try:
                amount = Decimal(str(raw_payment.get('amount', '0.00'))).quantize(Decimal('0.01'))
            except Exception as exc:
                raise SaleError('Payment amount must be a valid number.') from exc
            if amount < Decimal('0.00'):
                raise SaleError('Payment amount cannot be negative.')
            # CREDIT describes the unpaid portion; it is not an actual
            # settlement account and must never create a CREDIT Payment row.
            if method == 'CREDIT' and amount > Decimal('0.00'):
                
                method = 'CASH'
            normalized_payments.append({**raw_payment, 'method': method, 'amount': amount})

        payments_data = normalized_payments
        pending_methods = {'FONEPAY'}
        has_pending_payment = any(p['method'] in pending_methods and p['amount'] > 0 for p in payments_data)

        # Ignore zero-value CREDIT markers. Actual settlement rows only contain
        # CASH/CARD/BANK_TRANSFER/FONEPAY/etc.
        settlement_payments = [p for p in payments_data if p['method'] != 'CREDIT' and p['amount'] > 0]
        paid_sum = sum((p['amount'] for p in settlement_payments if p['method'] not in pending_methods), Decimal('0.00'))

        if paid_sum > grand_total:
            raise PaymentMismatchError(
                f'Payment received ({paid_sum}) cannot exceed grand total ({grand_total}).'
            )

        if len(settlement_payments) > 1:
            payment_mode = 'SPLIT'
        elif settlement_payments:
            payment_mode = settlement_payments[0]['method']
        else:
            payment_mode = 'CREDIT'

        if len(settlement_payments) > 1:
            methods = [p['method'] for p in settlement_payments]
            if methods.count('CASH') != 1:
                raise SaleError('Split payment must contain exactly one Cash payment.')

        default_sales_ac = Account.objects.filter(account_code='4100').first()
        if not default_sales_ac:
            from accounting.services import ChartOfAccountsService
            accounts = ChartOfAccountsService.ensure_default_accounts()
            default_sales_ac = accounts.get('4100')
        if not default_sales_ac:
            raise SaleError('Sales revenue account 4100 is not configured.')

        if has_pending_payment:
            sale_status = 'PENDING'
            payment_status = 'PENDING'
        elif paid_sum < grand_total:
            # A single actual settlement with an outstanding balance is a
            # partial credit sale. The accounting service will debit the
            # received account and customer A/R for the unpaid balance.
            sale_status = 'COMPLETED'
            payment_status = 'PARTIAL' if paid_sum > Decimal('0.00') else 'PENDING'
            if len(settlement_payments) <= 1:
                payment_mode = 'CREDIT'
        else:
            sale_status = 'COMPLETED'
            payment_status = 'PAID'

        # For a full cash payment, tender may be greater than the invoice and
        # the difference is change. For credit/partial sales, no change exists.
        if payment_mode == 'CREDIT':
            change_val = Decimal('0.00')
            received_val = paid_sum
        else:
            change_val = max(Decimal('0.00'), (received_val - grand_total).quantize(Decimal('0.01')))

        sale = Sale.objects.create(
            invoice_no=invoice_no,
            fiscal_year=active_fy,
            customer=customer,
            buyer_name=getattr(customer, 'customer_name'),
            user=cashier,
            bs_date=bs_date,
            taxable_amount=taxable_amount,
            non_taxable_amount=non_taxable_amount,
            subtotal=subtotal,
            discount_total=total_final_discount,
            vat_total=vat_total,
            round_off=round_off,
            grand_total=grand_total,
            tender_amount=tender_val,
            received_amount=received_val,
            change_amount=change_val,
            payment_mode=payment_mode,
            payment_status=payment_status,
            sale_status=sale_status,
            sales_ac=default_sales_ac,
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

                previous_quantity = batch.current_quantity
                deduct = min(batch.current_quantity, qty_needed)
                batch.current_quantity -= deduct
                if batch.current_quantity == Decimal('0.000'):
                    batch.batch_status = 'EXHAUSTED'
                batch.save()
                from dashboard.services import notify_stock_transition
                notify_stock_transition(batch, previous_quantity)
                qty_needed -= deduct

            SaleItem.objects.create(
                sale=sale,
                variant=vi['variant'],
                batch=primary_batch,
                quantity=vi['quantity'],
                unit_price=vi['unit_price'],
                discount_amount=vi['discount'],
                vat_percent=vi['vat_percent'],
                vat_amount=(vi['line_total'] - vi['net_subtotal']).quantize(Decimal('0.01')),
                net_subtotal=vi['net_subtotal'],
                line_total=vi['line_total'],
            )

        # Create only real settlement payments. A CREDIT balance is represented
        # by Sale.due_amount/customer A/R, never by a fake CREDIT payment row.
        for p in settlement_payments:
            Payment.objects.create(
                sale=sale,
                payment_method=p['method'],
                amount=p['amount'],
                provider_reference=p.get('reference_no', ''),
                status='PENDING' if p['method'] in pending_methods else 'PAID',
            )

        sale.paid_amount = paid_sum
        sale.due_amount = max(Decimal('0.00'), grand_total - paid_sum)
        if payment_mode == 'CREDIT':
            sale.received_amount = paid_sum
            sale.change_amount = Decimal('0.00')
            sale.payment_status = 'PAID' if sale.due_amount == 0 else (
                'PARTIAL' if paid_sum > Decimal('0.00') else 'PENDING'
            )
        sale.save(update_fields=[
            'paid_amount', 'due_amount', 'received_amount',
            'change_amount', 'payment_status'
        ])

        if not has_pending_payment and paid_sum != grand_total and payment_mode not in {'CREDIT', 'SPLIT'}:
            raise PaymentMismatchError(
                f'Payment received ({paid_sum}) does not equal grand total ({grand_total}).'
            )

        if sale.sale_status == 'COMPLETED':
            from accounting.services import AccountingService
            journal_entry = AccountingService.post_sale_journal_entry(sale)
            if sale.journal_entry_id != journal_entry.entry_id:
                sale.journal_entry = journal_entry
                sale.save(update_fields=['journal_entry'])


        return sale, True

class SaleCancelService:

    @staticmethod
    @transaction.atomic
    def cancel_sale(sales_id, cancelled_by):
        """
        Reverses stock deduction on original inventory batches and records CANCELLED status.
        Never deletes rows to maintain full audit trails.
        """
        sale = Sale.objects.select_for_update().get(pk=sales_id)

        if sale.sale_status != 'COMPLETED':
            raise SaleError(f"Cannot cancel a sale with status {sale.sale_status}")

        for item in sale.items.select_related('variant', 'batch').all():
            if item.batch:
                item.batch.current_quantity += item.quantity
                if item.batch.batch_status == 'EXHAUSTED':
                    item.batch.batch_status = 'ACTIVE'
                item.batch.save()

        sale.sale_status = 'CANCELLED'
        sale.save(update_fields=['sale_status'])
        return sale