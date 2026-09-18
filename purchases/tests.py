from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from .forms import PurchaseOrderForm, PurchaseReturnForm
from .services import calculate_po_totals


class PurchaseReturnFormTests(SimpleTestCase):
	def test_calculated_fields_are_optional_and_freight_is_editable(self):
		form = PurchaseOrderForm()
		for field_name in ('subtotal', 'vat_amount', 'tds_amount', 'total_amount', 'net_payable_amount'):
			self.assertFalse(form.fields[field_name].required)
		self.assertFalse(form.fields['freight_charge'].required)
		self.assertEqual(form.fields['freight_charge'].widget.input_type, 'number')

	def test_totals_include_freight_before_tds(self):
		totals = calculate_po_totals(
			[{'quantity': '2', 'unit_price': '100', 'vat_percent': '13'}],
			tds_rate='1.5',
			freight_charge='25.00',
		)
		self.assertEqual(totals['subtotal'], Decimal('200.00'))
		self.assertEqual(totals['vat_amount'], Decimal('26.00'))
		self.assertEqual(totals['total_amount'], Decimal('251.00'))
		self.assertEqual(totals['tds_amount'], Decimal('3.00'))
		self.assertEqual(totals['net_payable_amount'], Decimal('248.00'))

	def test_negative_freight_is_clamped(self):
		totals = calculate_po_totals(
			[{'quantity': '1', 'unit_price': '10', 'vat_percent': '0'}],
			freight_charge='-5',
		)
		self.assertEqual(totals['freight_charge'], Decimal('0.00'))

	def test_accepts_return_within_active_stock(self):
		form = PurchaseReturnForm(
			{'quantity': '2.000', 'reason': 'Damaged packaging', 'notes': ''},
			batch=SimpleNamespace(current_quantity=Decimal('5.000')),
		)
		self.assertTrue(form.is_valid())

	def test_rejects_return_above_active_stock(self):
		form = PurchaseReturnForm(
			{'quantity': '5.001', 'reason': 'Damaged packaging', 'notes': ''},
			batch=SimpleNamespace(current_quantity=Decimal('5.000')),
		)
		self.assertFalse(form.is_valid())
		self.assertIn('exceed', str(form.errors['quantity']))

	def test_rejects_return_from_empty_batch(self):
		form = PurchaseReturnForm(
			{'quantity': '1.000', 'reason': 'Damaged packaging', 'notes': ''},
			batch=SimpleNamespace(current_quantity=Decimal('0.000')),
		)
		self.assertFalse(form.is_valid())
		self.assertIn('no active stock', str(form.errors['quantity']))

	def test_edit_return_can_use_its_original_quantity_again(self):
		return_record = SimpleNamespace(quantity=Decimal('2.000'))
		form = PurchaseReturnForm(
			{'quantity': '6.000', 'reason': 'Updated count', 'notes': ''},
			batch=SimpleNamespace(current_quantity=Decimal('5.000')),
			existing_return=return_record,
		)
		self.assertTrue(form.is_valid())
