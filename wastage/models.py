from decimal import Decimal

from django.conf import settings
from django.db import models


class Wastages(models.Model):
	batch = models.ForeignKey(
		'inventory.InventoryBatch', on_delete=models.PROTECT, related_name='wastage_records'
	)
	quantity = models.DecimalField(max_digits=10, decimal_places=3)
	unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
	total_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
	reason = models.CharField(max_length=255, null=True, blank=True)
	notes = models.TextField(blank=True)
	recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
	stock_adjustment = models.OneToOneField(
		'inventory.StockAdjustment', on_delete=models.PROTECT,
		related_name='wastage_record', null=True, blank=True
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Wastage {self.batch.batch_number}: {self.quantity}"
