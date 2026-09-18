from decimal import Decimal

from django.test import SimpleTestCase

from .models import InventoryReturnItem, SalesReturn
from .returns import money


class SalesReturnWorkflowTests(SimpleTestCase):
    def test_money_is_decimal_and_quantized(self):
        self.assertEqual(money('12.345'), Decimal('12.35'))
        self.assertIsInstance(money('12.00'), Decimal)

    def test_return_conditions_are_limited_to_supported_dispositions(self):
        self.assertEqual(
            set(InventoryReturnItem.Condition.values),
            {'RESALABLE', 'DAMAGED', 'EXPIRED'},
        )

    def test_rma_status_starts_as_draft(self):
        self.assertEqual(SalesReturn.Status.DRAFT, 'DRAFT')
