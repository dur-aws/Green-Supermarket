from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Customer, Membership


class CustomerCRMTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_user(
			username='crm-test', email='crm@example.com', password='test-password'
		)
		self.user.is_superuser = True
		self.user.save(update_fields=['is_superuser'])
		self.client.force_login(self.user)
		self.customer = Customer.objects.create(
			customer_code='CUST-TEST',
			customer_name='Test Buyer',
			customer_type=Customer.TYPE_REGISTERED,
			phone='9800000000',
			email='buyer@example.com',
		)

	def test_search_matches_email(self):
		response = self.client.get(reverse('customer_search_api'), {'q': 'buyer@example.com'})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['results'][0]['id'], self.customer.pk)

	def test_quick_registration_creates_unique_customer(self):
		response = self.client.post(reverse('customer_quick_add'), {
			'customer_name': 'Quick Buyer',
			'phone': '9811111111',
			'email': 'quick@example.com',
		})
		self.assertEqual(response.status_code, 201)
		self.assertEqual(Customer.objects.filter(phone='9811111111').count(), 1)
		self.assertTrue(response.json()['code'].startswith('CUST-'))

	def test_membership_history_is_protected(self):
		membership = Membership.objects.create(
			customer=self.customer,
			membership_type='Gold',
			start_date=date.today(),
			expiry_date=date.today() + timedelta(days=365),
			membership_fee='100.00',
		)
		self.customer.delete()
		self.customer.refresh_from_db()
		self.assertEqual(self.customer.status, 'INACTIVE')
		self.assertTrue(Membership.objects.filter(pk=membership.pk).exists())
