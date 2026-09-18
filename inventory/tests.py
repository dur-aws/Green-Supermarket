from decimal import Decimal
from datetime import date, timedelta
from types import SimpleNamespace

from django.test import SimpleTestCase

from .forms import StockAdjustmentForm
from .models import InventoryBatch


class InventoryBatchStatusTests(SimpleTestCase):
    def test_zero_quantity_before_expiry_is_exhausted(self):
        status = InventoryBatch.resolve_status(
            Decimal('0.000'), date.today() + timedelta(days=1), today=date.today()
        )

        self.assertEqual(status, InventoryBatch.BatchStatus.EXHAUSTED)

    def test_zero_quantity_takes_precedence_over_expiry(self):
        status = InventoryBatch.resolve_status(
            Decimal('0.000'), date.today() - timedelta(days=1), today=date.today()
        )

        self.assertEqual(status, InventoryBatch.BatchStatus.EXHAUSTED)

    def test_positive_expired_quantity_is_expired(self):
        status = InventoryBatch.resolve_status(
            Decimal('1.000'), date.today() - timedelta(days=1), today=date.today()
        )

        self.assertEqual(status, InventoryBatch.BatchStatus.EXPIRED)

    def test_positive_unexpired_quantity_is_active(self):
        status = InventoryBatch.resolve_status(
            Decimal('1.000'), date.today() + timedelta(days=1), today=date.today()
        )

        self.assertEqual(status, InventoryBatch.BatchStatus.ACTIVE)


class StockAdjustmentFormTests(SimpleTestCase):
    def test_rejects_zero_change(self):
        form = StockAdjustmentForm({'reason_code': 'CORRECTION', 'quantity_change': '0', 'notes': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('zero', str(form.errors['quantity_change']))

    def test_rejects_change_below_available_stock(self):
        batch = SimpleNamespace(current_quantity=Decimal('2.000'))
        form = StockAdjustmentForm(
            {'reason_code': 'WASTAGE', 'quantity_change': '-2.001', 'notes': ''},
            batch=batch,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('negative', str(form.errors['quantity_change']))
