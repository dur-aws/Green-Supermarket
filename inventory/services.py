from decimal import Decimal

from django.db import transaction
from django.db.models.aggregates import Sum
from django.utils import timezone

from .models import InventoryBatch, PurchaseReturn, StockAdjustment

from django.db import transaction
from .models import InventoryBatch, StockAdjustment
from products.models import ProductVariant

def create_inventory_batches_from_po(purchase_order):
    """
    Triggers when PO status turns to 'RECEIVED'. 
    Creates InventoryBatch records for all items in the purchase.
    """
    with transaction.atomic():
        for detail in purchase_order.purchasedetail_set.all():
            qty_received = detail.received_quantity if detail.received_quantity is not None else detail.ordered_quantity
            unit_cost = detail.actual_unit_price if detail.actual_unit_price is not None else detail.agreed_unit_price

            if not qty_received or qty_received <= Decimal('0.000'):
                continue
            if not isinstance(detail.variant, ProductVariant):
                raise ValueError(f"detail.variant is {type(detail.variant)}, expected ProductVariant")
            InventoryBatch.objects.create(
                variant=detail.variant,
                supplier=purchase_order.supplier,
                purchase_detail=detail,
                batch_number=f"BATCH-PO{purchase_order.purchase_id}-{detail.purchase_detail_id}",
                batch_no=getattr(detail, 'batch_no', None),
                manufacture_date=getattr(detail, 'manufacture_date', None),
                harvest_date=getattr(detail, 'harvest_date', None),
                expiry_date=detail.expiry_date,
                received_quantity=qty_received,
                current_quantity=qty_received,
                unit_cost_price=unit_cost or Decimal('0.00'),
                batch_status=InventoryBatch.BatchStatus.ACTIVE
            )
            # 2. Update and store cost_price directly on ProductVariant in Database
            variant = detail.variant
            variant.cost_price = unit_cost
            variant.save(update_fields=['cost_price'])

        from accounting.services import AccountingService
        AccountingService.post_purchase_receipt_journal_entry(
            purchase_order, created_by=purchase_order.received_by_user
        )



from django.core.exceptions import ValidationError



def reconcile_po_inventory(purchase_order, user, default_warehouse_id=1):
    """
    Reconciles InventoryBatches when a Purchase Order or its line items are updated.
    Updates existing batch cost, quantity, and expiry date, or logs stock adjustments if stock was already consumed.
    """
    with transaction.atomic():
        for detail in purchase_order.purchasedetail_set.all():
            new_qty = detail.received_quantity if detail.received_quantity is not None else detail.ordered_quantity
            new_cost = detail.actual_unit_price if detail.actual_unit_price is not None else detail.agreed_unit_price

            if not new_qty:
                new_qty = Decimal('0.000')
            if not new_cost:
                new_cost = Decimal('0.00')

            # Look for existing batch linked to this Purchase Detail line item
            batch = InventoryBatch.objects.select_for_update().filter(
                purchase_detail=detail
            ).first()

            if batch:
                # Calculate quantity difference
                qty_diff = new_qty - batch.received_quantity

                # Ensure reduction doesn't make current stock negative if sales occurred
                if batch.current_quantity + qty_diff < Decimal('0.000'):
                    raise ValidationError(
                        f"Cannot update line item for {detail.variant}. "
                        f"Stock has already been consumed ({batch.current_quantity} remaining)."
                    )

                # 1. Update batch attributes
                batch.received_quantity = new_qty
                batch.current_quantity += qty_diff
                batch.unit_cost_price = new_cost
                if hasattr(detail, 'expiry_date') and detail.expiry_date:
                    batch.expiry_date = detail.expiry_date

                # Update batch status
                if batch.current_quantity <= Decimal('0.000'):
                    batch.batch_status = 'EXHAUSTED'
                else:
                    batch.batch_status = 'ACTIVE'

                batch.save()

                # 2. Sync updated cost price back to ProductVariant
                variant = detail.variant
                variant.cost_price = new_cost
                variant.save(update_fields=['cost_price'])

                # 3. Log Audit Trail if quantity changed
                if qty_diff != Decimal('0.000'):
                    StockAdjustment.objects.create(
                        batch=batch,
                        adjusted_by_user=user,
                        quantity_change=qty_diff,
                        reason_code='CORRECTION',
                        loss_value=abs(qty_diff) * new_cost if qty_diff < 0 else Decimal('0.00'),
                        notes=f"Automatic correction from PO #{purchase_order.purchase_id} update."
                    )
            else:
                # If no batch exists yet and status is RECEIVED, create it
                if purchase_order.order_status == 'RECEIVED' and new_qty > Decimal('0.000'):
                    InventoryBatch.objects.create(
                        variant=detail.variant,
                        supplier=purchase_order.supplier,
                        purchase_detail=detail,
                        batch_number=f"BATCH-PO{purchase_order.purchase_id}-{detail.purchase_detail_id}",
                        batch_no=getattr(detail, 'batch_no', None),
                        manufacture_date=getattr(detail, 'manufacture_date', None),
                        harvest_date=getattr(detail, 'harvest_date', None),
                        expiry_date=getattr(detail, 'expiry_date', None),
                        received_quantity=new_qty,
                        current_quantity=new_qty,
                        unit_cost_price=new_cost,
                        batch_status=InventoryBatch.BatchStatus.ACTIVE
                    )
# def sync_variant_average_cost(variant):
#     """Calculates weighted average cost from active stock and updates ProductVariant.cost_price."""
#     today = timezone.now().date()
    
#     active_batches = variant.batches.filter(
#         batch_status='ACTIVE',
#         expiry_date__gte=today,
#         current_quantity__gt=0
#     )
    
#     total_qty = active_batches.aggregate(total=Sum('current_quantity'))['total'] or Decimal('0')
    
#     if total_qty > 0:
#         total_val = sum(b.current_quantity * b.unit_cost_price for b in active_batches)
#         variant.cost_price = total_val / total_qty
#         variant.save(update_fields=['cost_price'])

def process_stock_adjustment(batch_id, user, quantity_change, reason_code, notes=""):
    """
    Adjusts batch stock quantity and logs the audit trail in StockAdjustment.
    """
    with transaction.atomic():
        batch = InventoryBatch.objects.select_for_update().get(pk=batch_id)
        change = Decimal(str(quantity_change))

        if change == Decimal('0.000'):
            raise ValidationError("Adjustment quantity cannot be zero.")
        if change < Decimal('0.000') and batch.current_quantity <= Decimal('0.000'):
            raise ValidationError("This batch has no active stock available for adjustment.")
        if batch.current_quantity + change < Decimal('0.000'):
            raise ValidationError(
                f"Adjustment would make stock negative. Available: {batch.current_quantity}."
            )

        # Update available quantity
        previous_quantity = batch.current_quantity
        batch.current_quantity += change
        batch.save()  # Auto-sets EXHAUSTED if 0 via model save()
        from dashboard.services import notify_stock_transition
        notify_stock_transition(batch, previous_quantity)

        # Calculate loss value if it's a reduction
        loss_val = Decimal('0.00')
        if change < 0:
            loss_val = abs(change) * batch.unit_cost_price

        # Record adjustment
        adjustment = StockAdjustment.objects.create(
            batch=batch,
            adjusted_by_user=user,
            quantity_change=change,
            reason_code=reason_code,
            loss_value=loss_val,
            notes=notes
        )
        if reason_code == StockAdjustment.ReasonCode.WASTAGE and change < 0:
            from wastage.models import Wastages
            from accounting.services import AccountingService
            Wastages.objects.create(
                batch=batch,
                quantity=abs(change),
                unit_cost=batch.unit_cost_price,
                total_value=loss_val,
                reason=notes or 'Inventory wastage adjustment',
                recorded_by=user,
                stock_adjustment=adjustment,
            )
            entry = AccountingService.post_inventory_loss_journal_entry(
                entry_date=timezone.now().date(),
                reference_id=adjustment.pk,
                amount=loss_val,
                description=f"Inventory wastage adjustment #{adjustment.pk}",
                created_by=user,
            )
            batch.journal_entry = entry
            batch.save(update_fields=['journal_entry'])
        return adjustment


def process_purchase_return(batch_id, user, quantity, notes='', reason='Supplier return'):
    """Return active stock from its originating purchase order to the supplier."""
    from accounting.services import AccountingService

    quantity = Decimal(str(quantity))
    if quantity <= Decimal('0.000'):
        raise ValidationError("Return quantity must be greater than zero.")

    with transaction.atomic():
        batch = InventoryBatch.objects.select_for_update().select_related(
            'purchase_detail__purchase'
        ).get(pk=batch_id)
        if batch.current_quantity <= Decimal('0.000'):
            raise ValidationError("This batch has no active stock available for return.")
        if quantity > batch.current_quantity:
            raise ValidationError(
                f"Return quantity cannot exceed available stock ({batch.current_quantity})."
            )
        if not batch.purchase_detail_id:
            raise ValidationError("This batch is not linked to a purchase order.")

        unit_cost = batch.unit_cost_price
        previous_quantity = batch.current_quantity
        total_value = (quantity * unit_cost).quantize(Decimal('0.01'))
        batch.current_quantity -= quantity
        batch.save()
        from dashboard.services import notify_stock_transition
        notify_stock_transition(batch, previous_quantity)
        adjustment = StockAdjustment.objects.create(
            batch=batch,
            adjusted_by_user=user,
            quantity_change=-quantity,
            reason_code=StockAdjustment.ReasonCode.RETURN,
            loss_value=total_value,
            notes=notes or reason,
        )
        purchase_return = PurchaseReturn.objects.create(
            batch=batch,
            purchase_order=batch.purchase_detail.purchase,
            quantity=quantity,
            unit_cost=unit_cost,
            total_value=total_value,
            reason=reason,
            notes=notes,
            returned_by=user,
            stock_adjustment=adjustment,
        )
        entry = AccountingService.post_purchase_return_journal_entry(
            entry_date=timezone.now().date(),
            reference_id=purchase_return.pk,
            amount=total_value,
            description=f"Purchase return #{purchase_return.pk}",
            created_by=user,
        )
        purchase_return.journal_entry = entry
        purchase_return.save(update_fields=['journal_entry'])
        purchase_return.purchase_order.update_payment_summary()
        return purchase_return


def update_purchase_return(return_id, user, quantity, notes='', reason='Supplier return'):
    """Edit a supplier return and propagate its quantity change to stock and payable balance."""
    from accounting.models import JournalItem
    from accounting.services import AccountingService

    quantity = Decimal(str(quantity)).quantize(Decimal('0.001'))
    if quantity <= Decimal('0.000'):
        raise ValidationError('Return quantity must be greater than zero.')

    with transaction.atomic():
        purchase_return = PurchaseReturn.objects.select_for_update().select_related(
            'batch__purchase_detail__purchase', 'stock_adjustment', 'journal_entry'
        ).get(pk=return_id)
        batch = InventoryBatch.objects.select_for_update().get(pk=purchase_return.batch_id)
        old_quantity = purchase_return.quantity
        delta = quantity - old_quantity

        if batch.current_quantity - delta < Decimal('0.000'):
            raise ValidationError(
                f'Return quantity cannot exceed available stock ({batch.current_quantity + old_quantity}).'
            )

        total_value = (quantity * batch.unit_cost_price).quantize(Decimal('0.01'))
        batch.current_quantity -= delta
        batch.save()

        adjustment = purchase_return.stock_adjustment
        adjustment.quantity_change = -quantity
        adjustment.loss_value = total_value
        adjustment.notes = notes or reason
        adjustment.save(update_fields=['quantity_change', 'loss_value', 'notes'])

        purchase_return.quantity = quantity
        purchase_return.unit_cost = batch.unit_cost_price
        purchase_return.total_value = total_value
        purchase_return.reason = reason
        purchase_return.notes = notes
        purchase_return.save(update_fields=['quantity', 'unit_cost', 'total_value', 'reason', 'notes'])

        entry = purchase_return.journal_entry
        if entry:
            for item in entry.items.select_related('account'):
                if item.account.account_code == '2010':
                    item.debit = total_value
                    item.credit = Decimal('0.00')
                elif item.account.account_code == '1200':
                    item.debit = Decimal('0.00')
                    item.credit = total_value
                item.save(update_fields=['debit', 'credit'])
        else:
            entry = AccountingService.post_purchase_return_journal_entry(
                entry_date=timezone.now().date(),
                reference_id=purchase_return.pk,
                amount=total_value,
                description=f'Purchase return #{purchase_return.pk}',
                created_by=user,
            )
            purchase_return.journal_entry = entry
            purchase_return.save(update_fields=['journal_entry'])

        purchase_return.purchase_order.update_payment_summary()
        return purchase_return