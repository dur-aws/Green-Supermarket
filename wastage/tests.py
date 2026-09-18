from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from .forms import WastageForm


class WastageFormTests(SimpleTestCase):
	def test_accepts_raw_wastage_data_within_stock(self):
		batch = SimpleNamespace(current_quantity=Decimal('5.000'))
		form = WastageForm(
			{'quantity': '1.250', 'reason': 'SPOILED', 'notes': 'Raw data test'},
			batch=batch,
		)
		self.assertTrue(form.is_valid())
		self.assertEqual(form.cleaned_data['quantity'], Decimal('1.250'))

	def test_rejects_wastage_above_available_stock(self):
		batch = SimpleNamespace(current_quantity=Decimal('5.000'))
		form = WastageForm(
			{'quantity': '5.001', 'reason': 'Spoiled', 'notes': ''},
			batch=batch,
		)
		self.assertFalse(form.is_valid())
		self.assertIn('exceed', str(form.errors['quantity']))
