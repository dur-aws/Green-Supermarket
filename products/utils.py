import random
from django.db import transaction
from .models import ProductVariant


def generate_sku(exclude=None):
    """
    Unique SKU in the form PD00001, PD00002, ...
    `exclude` = SKUs already placed in other unsaved rows on the
    same page, so two new rows never get handed the same code.
    """
    exclude = set(exclude or [])
    with transaction.atomic():
        last = (
            ProductVariant.objects
            .select_for_update()
            .filter(sku__regex=r'^PD\d{5}$')
            .order_by('-sku')
            .first()
        )
        next_number = int(last.sku[2:]) + 1 if last else 1
        sku = f"PD{next_number:05d}"
        while ProductVariant.objects.filter(sku=sku).exists() or sku in exclude:
            next_number += 1
            sku = f"PD{next_number:05d}"
        return sku


def generate_barcode(exclude=None):
    """Unique 9-digit numeric barcode."""
    exclude = set(exclude or [])
    while True:
        barcode = str(random.randint(100000000, 999999999))
        if barcode not in exclude and not ProductVariant.objects.filter(barcode=barcode).exists():
            return barcode