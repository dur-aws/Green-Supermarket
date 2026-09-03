from decimal import Decimal, ROUND_HALF_UP


TWO_PLACES = Decimal('0.01')


def calculate_po_totals(line_items, tds_rate=Decimal('0.00')):
    """
    line_items: list of dicts like [{'quantity': ..., 'unit_price': ..., 'vat_percent': ...}, ...].
    VAT is determined by the product/variant taxability and defaults to 0 when not taxable.
    TDS is optional and applied only when the supplier is VAT/PAN registered.
    """
    subtotal = Decimal('0.00')
    vat_amount = Decimal('0.00')

    for item in line_items:
        quantity = Decimal(str(item.get('quantity', '0') or '0'))
        unit_price = Decimal(str(item.get('unit_price', '0') or '0'))
        item_subtotal = (quantity * unit_price).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        subtotal += item_subtotal

        vat_percent = Decimal(str(item.get('vat_percent') or '0'))
        if vat_percent < 0:
            vat_percent = Decimal('0.00')
        item_vat = (item_subtotal * (vat_percent / Decimal('100'))).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        vat_amount += item_vat

    subtotal = subtotal.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    vat_amount = vat_amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    total_amount = (subtotal + vat_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    tds_rate = Decimal(str(tds_rate or '0'))
    tds_amount = Decimal('0.00')
    if tds_rate > 0:
        tds_amount = (subtotal * (tds_rate / Decimal('100'))).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    net_payable = (total_amount - tds_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    return {
        'subtotal': subtotal,
        'vat_amount': vat_amount,
        'total_amount': total_amount,
        'tds_amount': tds_amount,
        'net_payable_amount': net_payable,
    }