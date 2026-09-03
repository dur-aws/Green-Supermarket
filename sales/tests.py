
# Create your tests here.
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from products.models import ProductVariant, Product
from customers.models import Customer
from inventory.models import InventoryBatch
from sales.models import Sale, SaleItem
from sales.services import SaleService, SaleError, InsufficientStockError

User = get_user_model()

class SaleServiceTests(TestCase):
    def setUp(self):
        # Create a test user (cashier)
        self.cashier = User.objects.create(username="cashier")

        # Create a test customer
        self.customer = Customer.objects.create(name="Test Customer")

        # Create a product + variant
        self.product = Product.objects.create(product_name="Test Product", is_vatable=True, vat_percent=13)
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="Default Variant",
            selling_price=Decimal("100.00"),
            is_vatable=True,
            vat_percent=13
        )

        # Create inventory batch
        self.batch = InventoryBatch.objects.create(
            variant=self.variant,
            batch_status="ACTIVE",
            expiry_date=timezone.now().date(),
            current_quantity=Decimal("10.000")
        )

    def test_create_sale_success(self):
        items_data = [
            {"variant_id": self.variant.pk, "quantity": 2, "price": "100.00"}
        ]
        payments_data = [{"method": "CASH", "amount": "200.00"}]

        sale, created = SaleService.create_sale(
            customer_id=self.customer.pk,
            items_data=items_data,
            payments_data=payments_data,
            cashier=self.cashier,
            idempotency_key="test123",
            narration="Test Sale"
        )

        self.assertTrue(created)
        self.assertEqual(sale.grand_total, Decimal("226"))  # 200 + 13% VAT
        self.assertEqual(SaleItem.objects.count(), 1)

    def test_insufficient_stock(self):
        items_data = [
            {"variant_id": self.variant.pk, "quantity": 20, "price": "100.00"}
        ]
        with self.assertRaises(InsufficientStockError):
            SaleService.create_sale(
                customer_id=self.customer.pk,
                items_data=items_data,
                payments_data=[],
                cashier=self.cashier,
                idempotency_key="test456"
            )

    def test_invalid_quantity(self):
        items_data = [
            {"variant_id": self.variant.pk, "quantity": 0, "price": "100.00"}
        ]
        with self.assertRaises(SaleError):
            SaleService.create_sale(
                customer_id=self.customer.pk,
                items_data=items_data,
                payments_data=[],
                cashier=self.cashier,
                idempotency_key="test789"
            )
