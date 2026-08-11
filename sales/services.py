from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import F
from django.utils import timezone
import  bikram_sambat # Or use a local nepali_datetime converter

from products.models import Product, Customer, Inventory
from inventory.models import StockHistory
from .models import Sale, SaleItem, Payment
from .exceptions import (
    InsufficientStockError, InvalidQuantityError,
    InvalidDiscountError, PaymentMismatchError, SaleError
)

MAX_DISCOUNT_PERCENT = Decimal('30.00') #[cite: 2]

class InvoiceNumberService:
    @staticmethod
    def generate(fiscal_year):
        """
        Generate sequential invoice number scoped by Fiscal Year (e.g. INV-2081/82-000123)
        """
        prefix = f"INV-{fiscal_year}-"

        last_sale = Sale.objects.select_for_update().filter(
            invoice_no__startswith=prefix
        ).order_by('-id').first()

        if last_sale:
            last_number = int(last_sale.invoice_no.split('-')[-1])
            next_number = last_number + 1
        else:
            next_number = 1

        return f"{prefix}{next_number:06d}"

class SaleService:

    @staticmethod
    @transaction.atomic
    def create_sale(customer_id, items_data, payments_data, cashier, idempotency_key, narration='', date_bs='', fiscal_year=''):
        existing = Sale.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing, False

        if not items_data:
            raise InvalidQuantityError("Cart is empty") #[cite: 2]

        customer = Customer.objects.get(pk=customer_id) #[cite: 2]

        product_ids = [item['product_id'] for item in items_data] #[cite: 2]
        inventories = Inventory.objects.select_for_update().filter(
            product_id__in=product_ids
        ).order_by('product_id') #[cite: 2]
        inventory_map = {inv.product_id: inv for inv in inventories} #[cite: 2]

        subtotal = Decimal('0.00')
        discount_total = Decimal('0.00')
        taxable_amount = Decimal('0.00')
        non_taxable_amount = Decimal('0.00')
        vat_total = Decimal('0.00')
        validated_items = []

        for item in items_data:
            quantity = Decimal(str(item['quantity'])) #[cite: 2]
            discount = Decimal(str(item.get('discount', '0'))) #[cite: 2]
            
            if quantity <= 0:
                raise InvalidQuantityError("Quantity must be greater than zero") #[cite: 2]

            product = Product.objects.get(pk=item['product_id']) #[cite: 2]
            inv = inventory_map.get(product.id) #[cite: 2]

            if inv is None or inv.quantity < quantity: #[cite: 2]
                available = inv.quantity if inv else 0 #[cite: 2]
                raise InsufficientStockError(
                    f"Insufficient stock for {product.name}. Available: {available}"
                ) #[cite: 2]

            line_gross = (product.price * quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) #[cite: 2]
            max_allowed_discount = (line_gross * MAX_DISCOUNT_PERCENT / 100).quantize(Decimal('0.01')) #[cite: 2]
            if discount > max_allowed_discount:
                raise InvalidDiscountError(f"Discount exceeds maximum allowed on {product.name}") #[cite: 2]

            line_after_discount = line_gross - discount
            
            # Check VAT registration status on product (13% VAT or Exempt)
            is_vatable = getattr(product, 'is_vatable', True)
            if is_vatable:
                tax_percent = Decimal('13.00')
                line_vat = (line_after_discount * tax_percent / Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                taxable_amount += line_after_discount
                vat_total += line_vat
            else:
                tax_percent = Decimal('0.00')
                line_vat = Decimal('0.00')
                non_taxable_amount += line_after_discount

            line_total = line_after_discount + line_vat

            subtotal += line_gross
            discount_total += discount

            validated_items.append({
                'product': product,
                'quantity': quantity,
                'unit_price': product.price,
                'discount': discount,
                'tax_percent': tax_percent,
                'subtotal': line_after_discount,
                'line_total': line_total,
            })

        raw_grand_total = taxable_amount + non_taxable_amount + vat_total
        grand_total = raw_grand_total.quantize(Decimal('1'), rounding=ROUND_HALF_UP) #[cite: 2]
        round_off = (grand_total - raw_grand_total).quantize(Decimal('0.01')) #[cite: 2]

        # Enforce IRD Requirement: Transactions > NPR 5,000 need customer PAN or complete identity
        if grand_total > Decimal('5000.00') and customer.id == 1 and not customer.pan_number:
            raise SaleError("IRD Mandate: Customer PAN/Name is required for billing above NPR 5,000.")

        invoice_no = InvoiceNumberService.generate(fiscal_year)

        sale = Sale.objects.create(
            invoice_no=invoice_no,
            fiscal_year=fiscal_year,
            customer=customer,
            customer_pan=customer.pan_number,
            buyer_name=customer.name,
            cashier=cashier,
            sale_date_bs=date_bs,
            taxable_amount=taxable_amount,
            non_taxable_amount=non_taxable_amount,
            subtotal=subtotal,
            discount_total=discount_total,
            vat_total=vat_total,
            round_off=round_off,
            grand_total=grand_total,
            status='COMPLETED',
            narration=narration,
            idempotency_key=idempotency_key,
        )

        for vi in validated_items:
            SaleItem.objects.create(
                sale=sale,
                product=vi['product'],
                quantity=vi['quantity'],
                unit_price=vi['unit_price'],
                discount_amount=vi['discount'],
                tax_percent=vi['tax_percent'],
                subtotal=vi['subtotal'],
                line_total=vi['line_total'],
            )

            Inventory.objects.filter(product=vi['product']).update(
                quantity=F('quantity') - vi['quantity']
            ) #[cite: 2]

            StockHistory.objects.create(
                product=vi['product'],
                quantity=-vi['quantity'],
                reason='SALE',
                reference=invoice_no,
            ) #[cite: 2]

        paid_sum = Decimal('0.00')
        for p in payments_data:
            amount = Decimal(str(p['amount']))
            if amount <= 0:
                continue
            
            # Digital payment options require transaction/reference number alignment
            if p['method'] in ['ESEWA', 'KHALTI', 'BANK_TRANSFER', 'CONNECT_IPS'] and not p.get('reference_no'):
                raise SaleError(f"Reference/Transaction ID is required for {p['method']} payment.")

            Payment.objects.create(
                sale=sale,
                method=p['method'],
                amount=amount,
                reference_no=p.get('reference_no'),
            ) #[cite: 2]
            paid_sum += amount

        if paid_sum < grand_total:
            raise PaymentMismatchError(
                f"Payment received ({paid_sum}) is less than grand total ({grand_total})"
            ) #[cite: 2]

        return sale, True
    

class SaleCancelService:

    @staticmethod
    @transaction.atomic
    def cancel_sale(sale_id, cancelled_by):
        """Reverses stock deduction and marks sale CANCELLED.
        Never deletes the row — preserves audit trail (per our design)."""
        sale = Sale.objects.select_for_update().get(pk=sale_id)

        if sale.status != 'COMPLETED':
            raise SaleServiceError(f"Cannot cancel a sale with status {sale.status}")

        for item in sale.items.select_related('product').all():
            Inventory.objects.filter(product=item.product).update(
                quantity=F('quantity') + item.quantity
            )
            StockHistory.objects.create(
                product=item.product,
                quantity=item.quantity,   # positive — stock returning
                reason='SALE_CANCELLED',
                reference=sale.invoice_no,
            )

        sale.status = 'CANCELLED'
        sale.save(update_fields=['status'])
        return sale


from .exceptions import SaleError as SaleServiceError