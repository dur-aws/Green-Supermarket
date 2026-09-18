from django.core.management.base import BaseCommand

from inventory.models import InventoryBatch
from dashboard.services import notify_batch_state


class Command(BaseCommand):
    help = 'Generate idempotent batch expiry notifications for the current time.'

    def handle(self, *args, **options):
        batches = InventoryBatch.objects.select_related('variant__product').all()
        for batch in batches:
            notify_batch_state(batch)
        self.stdout.write(self.style.SUCCESS(f'Processed {batches.count()} inventory batches.'))
