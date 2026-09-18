from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from .services import notify_batch_state, notify_stock_transition


class NotificationEventTests(SimpleTestCase):
	def setUp(self):
		self.user = SimpleNamespace(pk=10)
		self.batch = SimpleNamespace(
			pk=22,
			batch_no='B001',
			batch_number='BATCH-22',
			current_quantity=Decimal('5.000'),
			expiry_date=(timezone.now() + timedelta(days=5)).date(),
			expiry_at=timezone.now() + timedelta(days=5),
			variant=SimpleNamespace(product=SimpleNamespace(product_name='Tomato')),
		)

	@patch('dashboard.services._create_once')
	@patch('dashboard.services._internal_users')
	def test_expiry_warning_at_five_days(self, internal_users, create_once):
		internal_users.return_value = [self.user]
		expiry_at = datetime(2026, 9, 18, 14, 35)
		self.batch.expiry_at = expiry_at
		notify_batch_state(self.batch, expiry_at - timedelta(days=5))
		self.assertEqual(create_once.call_args.kwargs['event_key'], 'batch:22:expiry-warning')
		self.assertIn('will expire in 5 days', create_once.call_args.kwargs['message'])

	@patch('dashboard.services._create_once')
	@patch('dashboard.services._internal_users')
	def test_expired_notification_at_exact_time(self, internal_users, create_once):
		internal_users.return_value = [self.user]
		expiry_at = datetime(2026, 9, 18, 14, 35)
		self.batch.expiry_at = expiry_at
		notify_batch_state(self.batch, expiry_at)
		self.assertEqual(create_once.call_args.kwargs['event_key'], 'batch:22:expired')
		self.assertIn('has expired', create_once.call_args.kwargs['message'])

	@patch('dashboard.services._create_once')
	@patch('dashboard.services._internal_users')
	def test_stock_zero_event_records_transition_event(self, internal_users, create_once):
		internal_users.return_value = [self.user]
		self.batch.current_quantity = Decimal('0.000')
		notify_stock_transition(self.batch, Decimal('1.000'))
		self.assertIn('out of stock', create_once.call_args.kwargs['message'])
		self.assertIn('out-of-stock', create_once.call_args.kwargs['event_key'])
