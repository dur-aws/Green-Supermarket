from decimal import Decimal, ROUND_HALF_UP

VAT_RATE = Decimal('0.13')
TWO_PLACES = Decimal('0.01')


def calculate_po_totals(line_items, tds_rate=Decimal('1.50')):
    """
    line_items: list of dicts like [{'quantity': ..., 'unit_price': ...}, ...]
    Returns a dict of authoritative totals — the only place this math should happen.
    """
    # 1. Calculate Subtotal safely handling empty lists
    subtotal = sum(
        (Decimal(str(item['quantity'])) * Decimal(str(item['unit_price'])) for item in line_items),
        Decimal('0.00')
    ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    # 2. Compute VAT (13%)
    vat_amount = (subtotal * VAT_RATE).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    total_amount = (subtotal + vat_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    # 3. Compute TDS on Subtotal (Standard Accounting Norm)
    tds_rate = Decimal(str(tds_rate or '0'))
    tds_amount = (subtotal * (tds_rate / Decimal('100'))).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    # 4. Net Payable to Vendor = Gross Total - TDS Deducted
    net_payable = (total_amount - tds_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    return {
        'subtotal': subtotal,
        'vat_amount': vat_amount,
        'total_amount': total_amount,
        'tds_amount': tds_amount,
        'net_payable_amount': net_payable,
    }