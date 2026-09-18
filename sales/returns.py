from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounting.services import AccountingService, FiscalYearService
from inventory.models import InventoryBatch, StockAdjustment
from payments.models import Payment, PaymentRefund
from wastage.models import Wastages

from .models import (
    CreditMemo,
    InventoryReturnItem,
    InventoryReturnReceipt,
    SalesReturn,
    SalesReturnItem,
)

ZERO = Decimal('0.000')
MONEY_ZERO = Decimal('0.00')


def money(value):
    return Decimal(str(value or '0')).quantize(MONEY_ZERO, rounding=ROUND_HALF_UP)


def remaining_returnable_quantity(sale_item):
    returned = sale_item.return_items.exclude(
        rma__status=SalesReturn.Status.CANCELLED
    ).aggregate(total=Sum('quantity_requested'))['total'] or ZERO
    return sale_item.quantity - returned


@transaction.atomic
def create_rma(*, sale_id, items, user, reason=''):
    from .models import Sale

    sale = Sale.objects.select_for_update().get(pk=sale_id)
    if sale.sale_status == 'CANCELLED':
        raise ValidationError('Cancelled invoices cannot be returned.')
    if not items:
        raise ValidationError('Select at least one invoice item to return.')

    rma = SalesReturn.objects.create(
        sale=sale,
        customer=sale.customer,
        created_by=user,
        reason=reason,
    )
    for item_data in items:
        sale_item = sale.items.select_for_update().filter(
            pk=item_data['sale_item_id']
        ).first()
        if sale_item is None:
            raise ValidationError('The selected invoice item does not exist.')
        quantity = Decimal(str(item_data['quantity']))
        remaining = remaining_returnable_quantity(sale_item)
        if quantity <= ZERO or quantity > remaining:
            raise ValidationError(
                f'Return quantity for {sale_item.variant.variant_name} must be between 0 and {remaining}.'
            )
        unit_refund = money(sale_item.line_total / sale_item.quantity)
        SalesReturnItem.objects.create(
            rma=rma,
            sale_item=sale_item,
            quantity_requested=quantity,
            unit_refund_amount=unit_refund,
            source_batch=sale_item.batch,
        )
    return rma


def _return_cost(return_item):
    batch = return_item.source_batch
    if batch is not None:
        return money(batch.unit_cost_price)
    return money(return_item.sale_item.variant.cost_price)


def _find_resalable_batch(return_item, today):
    source = return_item.source_batch
    if (
        source is not None
        and source.expiry_date >= today
        and source.batch_status != InventoryBatch.BatchStatus.QUARANTINED
    ):
        return InventoryBatch.objects.select_for_update().get(pk=source.pk)
    return InventoryBatch.objects.select_for_update().filter(
        variant=return_item.sale_item.variant,
        batch_status=InventoryBatch.BatchStatus.ACTIVE,
        expiry_date__gte=today,
    ).order_by('expiry_date', 'batch_id').first()


@transaction.atomic
def receive_and_inspect_return(*, rma_id, inspections, user):
    rma = SalesReturn.objects.select_for_update().select_related('sale').get(pk=rma_id)
    if rma.status != SalesReturn.Status.DRAFT:
        raise ValidationError('This RMA has already been received or processed.')

    return_items = list(rma.items.select_for_update().select_related(
        'sale_item__variant', 'source_batch'
    ))
    if not inspections:
        raise ValidationError('Inspection details are required.')

    today = timezone.now().date()
    receipt = InventoryReturnReceipt.objects.create(
        rma=rma,
        received_by=user,
        inspected_by=user,
    )
    total_refund = MONEY_ZERO
    total_resalable_cost = MONEY_ZERO

    for return_item in return_items:
        data = inspections.get(str(return_item.pk), inspections.get(return_item.pk, {}))
        quantity = Decimal(str(data.get('quantity', return_item.quantity_requested)))
        condition = data.get('condition')
        if quantity <= ZERO or quantity > return_item.quantity_requested:
            raise ValidationError('Inspected quantity exceeds the requested return quantity.')
        if condition not in InventoryReturnItem.Condition.values:
            raise ValidationError('Every returned item must have a valid condition.')

        cost = _return_cost(return_item)
        target_batch = None
        if condition == InventoryReturnItem.Condition.RESALABLE:
            target_batch = _find_resalable_batch(return_item, today)
            if target_batch is None:
                raise ValidationError(
                    f'No active, unexpired batch is available for {return_item.sale_item.variant.variant_name}.'
                )
            target_batch.current_quantity += quantity
            target_batch.save()
            StockAdjustment.objects.create(
                batch=target_batch,
                adjusted_by_user=user,
                quantity_change=quantity,
                reason_code=StockAdjustment.ReasonCode.RETURN,
                loss_value=MONEY_ZERO,
                notes=f'Resalable customer return {rma.rma_number}.',
            )
            total_resalable_cost += money(cost * quantity)
        else:
            if return_item.source_batch is None:
                raise ValidationError(
                    f'No source inventory batch is recorded for {return_item.sale_item.variant.variant_name}.'
                )
            Wastages.objects.create(
                batch=return_item.source_batch,
                quantity=quantity,
                unit_cost=cost,
                total_value=money(cost * quantity),
                reason=f'Customer return - {condition.lower()}',
                notes=f'RMA {rma.rma_number}; removed from saleable stock.',
                recorded_by=user,
            )

        InventoryReturnItem.objects.create(
            receipt=receipt,
            return_item=return_item,
            condition=condition,
            quantity=quantity,
            unit_cost=cost,
            target_batch=target_batch,
            disposition_note=data.get('note', ''),
        )
        return_item.quantity_received = quantity
        return_item.save(update_fields=['quantity_received'])
        total_refund += money(return_item.unit_refund_amount * quantity)

    if total_resalable_cost > MONEY_ZERO:
        AccountingService.create_journal_entry(
            entry_date=today,
            bs_date=rma.sale.bs_date,
            description=f'Resale inventory received for {rma.rma_number}',
            reference_type='MANUAL',
            reference_id=rma.pk,
            fiscal_year=rma.sale.fiscal_year,
            items=[
                {'account_code': '1200', 'debit': total_resalable_cost, 'credit': MONEY_ZERO},
                {'account_code': '4010', 'debit': MONEY_ZERO, 'credit': total_resalable_cost},
            ],
            created_by=user,
        )

    credit_memo = CreditMemo.objects.create(
        sale=rma.sale,
        receipt=receipt,
        amount=total_refund,
        status=CreditMemo.Status.APPROVED,
        created_by=user,
    )
    memo_entry = AccountingService.create_journal_entry(
        entry_date=today,
        bs_date=rma.sale.bs_date,
        description=f'Credit Memo {credit_memo.memo_number} for Invoice #{rma.sale.invoice_no}',
        reference_type='MANUAL',
        reference_id=credit_memo.pk,
        fiscal_year=rma.sale.fiscal_year,
        items=[
            {'account_code': '3010', 'debit': total_refund, 'credit': MONEY_ZERO},
            {'account_code': '1110', 'debit': MONEY_ZERO, 'credit': total_refund},
        ],
        created_by=user,
    )
    credit_memo.journal_entry = memo_entry
    credit_memo.status = CreditMemo.Status.PENDING_REFUND
    credit_memo.save(update_fields=['journal_entry', 'status'])
    rma.status = SalesReturn.Status.CREDITED
    rma.received_at = timezone.now()
    rma.inspected_at = timezone.now()
    rma.save(update_fields=['status', 'received_at', 'inspected_at'])

    credited_total = rma.sale.credit_memos.exclude(status=CreditMemo.Status.COMPLETED).aggregate(
        total=Sum('amount')
    )['total'] or MONEY_ZERO
    if credited_total >= money(rma.sale.grand_total):
        rma.sale.sale_status = 'FULLY_CREDITED'
    else:
        rma.sale.sale_status = 'PARTIALLY_CREDITED'
    rma.sale.save(update_fields=['sale_status'])
    return receipt, credit_memo


@transaction.atomic
def create_refund(*, credit_memo_id, method, user):
    credit_memo = CreditMemo.objects.select_for_update().select_related('sale').get(pk=credit_memo_id)
    if credit_memo.status not in (CreditMemo.Status.APPROVED, CreditMemo.Status.PENDING_REFUND):
        raise ValidationError('This credit memo cannot be refunded.')
    if hasattr(credit_memo, 'payment_refund'):
        raise ValidationError('A refund already exists for this credit memo.')
    if method not in {'CASH_ON_HAND', 'QR_BANK_ACCOUNT'}:
        raise ValidationError('Select a valid refund method.')

    payment = credit_memo.sale.payment_transactions.filter(status='PAID').order_by('transaction_id').first()
    if payment is None:
        raise ValidationError('The original invoice has no settled payment to refund.')
    refund = PaymentRefund.objects.create(
        payment=payment,
        credit_memo=credit_memo,
        amount=credit_memo.amount,
        refund_reference=f'REF-{credit_memo.memo_number}',
        refund_method=method,
        reason=f'Refund for {credit_memo.memo_number}',
        status='PENDING',
    )
    credit_memo.status = CreditMemo.Status.PENDING_REFUND
    credit_memo.save(update_fields=['status'])
    return refund


@transaction.atomic
def confirm_refund(*, refund_id, user):
    refund = PaymentRefund.objects.select_for_update().select_related('credit_memo__sale').get(pk=refund_id)
    if refund.status in {'PAID', 'COMPLETED'}:
        raise ValidationError('This refund has already been confirmed.')
    if refund.status != 'PENDING' or refund.credit_memo is None:
        raise ValidationError('Only pending credit memo refunds can be confirmed.')

    credit_memo = CreditMemo.objects.select_for_update().get(pk=refund.credit_memo_id)
    account_code = '1010' if refund.refund_method == 'CASH_ON_HAND' else '1030'
    entry = AccountingService.create_journal_entry(
        entry_date=timezone.now().date(),
        bs_date=credit_memo.sale.bs_date,
        description=f'Refund settlement for {credit_memo.memo_number}',
        reference_type='PAYMENT',
        reference_id=refund.pk,
        fiscal_year=credit_memo.sale.fiscal_year,
        items=[
            {'account_code': '1110', 'debit': refund.amount, 'credit': MONEY_ZERO},
            {'account_code': account_code, 'debit': MONEY_ZERO, 'credit': refund.amount},
        ],
        created_by=user,
    )
    refund.status = 'PAID'
    refund.confirmed_by = user
    refund.confirmed_at = timezone.now()
    refund.journal_entry = entry
    refund.save(update_fields=['status', 'confirmed_by', 'confirmed_at', 'journal_entry'])
    credit_memo.status = CreditMemo.Status.COMPLETED
    credit_memo.save(update_fields=['status'])
    refund.credit_memo.receipt.rma.status = SalesReturn.Status.REFUNDED
    refund.credit_memo.receipt.rma.save(update_fields=['status'])
    return refund
