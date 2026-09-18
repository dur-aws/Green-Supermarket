from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from .models import Notification

User = get_user_model()


def _event_time(value=None):
    value = value or timezone.now()
    if timezone.is_naive(value):
        return value
    return timezone.localtime(value)


def _create_once(*, user, event_key, title, message, notification_type='info', link=''):
    if not user:
        return None
    try:
        with transaction.atomic():
            return Notification.objects.create(
                user=user,
                event_key=f'{event_key}:user:{user.pk}',
                title=title,
                message=message,
                type=notification_type,
                link=link,
            )
    except IntegrityError:
        return Notification.objects.filter(
            event_key=f'{event_key}:user:{user.pk}'
        ).first()


def _internal_users():
    return User.objects.filter(
        Q(is_superuser=True)
        | Q(is_staff=True)
        | Q(role__permissions__module_name='purchases', role__permissions__can_view=True)
    ).exclude(role__role_name=Role.SUPPLIER).distinct()


def notify_purchase_event(purchase, event, actor=None):
    """Notify the assigned supplier and authorized internal purchase viewers."""
    if event == 'created':
        title = f'Purchase PO-{purchase.pk} created'
        message = f'Purchase PO-{purchase.pk} has been assigned to {purchase.supplier.supplier_name}.'
        notification_type = 'info'
    elif event in ('delivered', 'received'):
        title = f'Purchase PO-{purchase.pk} {"delivered" if event == "delivered" else "received"}'
        message = (
            f'Purchase PO-{purchase.pk} from {purchase.supplier.supplier_name} '
            f'was {"delivered by the supplier" if event == "delivered" else "received"}.'
        )
        notification_type = 'success'
    else:
        raise ValueError(f'Unsupported purchase event: {event}')

    link = reverse('supplier_po_list') if event in ('created', 'delivered') else reverse('po_detail', args=[purchase.pk])
    base_key = f'purchase:{purchase.pk}:{event}'
    supplier_user = purchase.supplier.user
    _create_once(
        user=supplier_user,
        event_key=base_key,
        title=title,
        message=message,
        notification_type=notification_type,
        link=reverse('supplier_po_list'),
    )
    for user in _internal_users():
        _create_once(
            user=user,
            event_key=base_key,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
        )


def notify_batch_state(batch, now=None):
    """Create the five-day and exact-expiry events once per batch."""
    now = _event_time(now)
    expiry_at = batch.expiry_at
    if expiry_at is None and batch.expiry_date:
        expiry_at = datetime.combine(batch.expiry_date, time.min)
    if expiry_at is None:
        return
    if timezone.is_naive(expiry_at) != timezone.is_naive(now):
        if timezone.is_naive(expiry_at):
            expiry_at = timezone.make_aware(expiry_at)
        else:
            expiry_at = timezone.make_naive(expiry_at)

    product_name = batch.variant.product.product_name
    batch_name = batch.batch_no or batch.batch_number
    expiry_text = _event_time(expiry_at).strftime('%d %b %Y %H:%M')
    link = reverse('stock_list')
    if now >= expiry_at:
        for user in _internal_users():
            _create_once(
                user=user,
                event_key=f'batch:{batch.pk}:expired',
                title='Batch expired',
                message=f'{product_name} Batch {batch_name} has expired — Expiry: {expiry_text}.',
                notification_type='danger',
                link=link,
            )
    elif now >= expiry_at - timedelta(days=5):
        for user in _internal_users():
            _create_once(
                user=user,
                event_key=f'batch:{batch.pk}:expiry-warning',
                title='Batch expiry warning',
                message=f'{product_name} Batch {batch_name} will expire in 5 days — Expiry: {expiry_text}.',
                notification_type='warning',
                link=link,
            )


def notify_stock_transition(batch, previous_quantity):
    if Decimal(str(previous_quantity)) > Decimal('0.000') and batch.current_quantity == Decimal('0.000'):
        product_name = batch.variant.product.product_name
        batch_name = batch.batch_no or batch.batch_number
        reached_at = _event_time()
        message = (
            f'{product_name} Batch {batch_name} is out of stock — Stock reached 0 at '
            f'{reached_at.strftime("%H:%M, %d %b %Y")}.'
        )
        for user in _internal_users():
            _create_once(
                user=user,
                event_key=f'batch:{batch.pk}:out-of-stock:{reached_at.date().isoformat()}',
                title='Batch out of stock',
                message=message,
                notification_type='danger',
                link=reverse('stock_list'),
            )
