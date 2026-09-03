from decimal import Decimal

from django.db import transaction
from django.db.models.aggregates import Sum
from django.utils import timezone

from .models import InventoryBatch, StockAdjustment

from decimal import Decimal
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

from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import InventoryBatch, StockAdjustment

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
                        reason_code='AUDIT',
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

        # Update available quantity
        batch.current_quantity += change
        batch.save()  # Auto-sets EXHAUSTED if 0 via model save()

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
        return adjustment