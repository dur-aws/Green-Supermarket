# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.core.paginator import Paginator

from products.models import Product, Inventory
from .models import StockHistory
from .forms import StockInForm, StockOutForm, StockAdjustmentForm


@login_required
def stock_in(request):
    if request.method == 'POST':
        form = StockInForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            qty = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']

            with transaction.atomic():
                inventory, _ = Inventory.objects.get_or_create(
                    product=product, defaults={'quantity': 0, 'reorder_level': 0}
                )
                inventory.quantity = inventory.quantity + qty
                inventory.save()

                StockHistory.objects.create(
                    product=product, user=request.user,
                    transaction_type='IN', quantity=qty, reason=reason
                )

            messages.success(request, f'Added {qty} units to "{product.product_name}". New stock: {inventory.quantity}.')
            return redirect('stock_in')
    else:
        form = StockInForm()

    recent = StockHistory.objects.filter(transaction_type='IN').select_related('product', 'user')[:15]
    return render(request, 'inventory/stock_in.html', {'form': form, 'recent': recent})


@login_required
def stock_out(request):
    if request.method == 'POST':
        form = StockOutForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            qty = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']

            with transaction.atomic():
                inventory, _ = Inventory.objects.get_or_create(
                    product=product, defaults={'quantity': 0, 'reorder_level': 0}
                )
                inventory.quantity = inventory.quantity - qty
                inventory.save()

                StockHistory.objects.create(
                    product=product, user=request.user,
                    transaction_type='OUT', quantity=-qty, reason=reason
                )

            messages.success(request, f'Removed {qty} units from "{product.product_name}". New stock: {inventory.quantity}.')
            return redirect('stock_out')
    else:
        form = StockOutForm()

    recent = StockHistory.objects.filter(transaction_type='OUT').select_related('product', 'user')[:15]
    return render(request, 'inventory/stock_out.html', {'form': form, 'recent': recent})


@login_required
def stock_adjustment(request):
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            adj_type = form.cleaned_data['adjustment_type']
            qty = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']

            with transaction.atomic():
                inventory, _ = Inventory.objects.get_or_create(
                    product=product, defaults={'quantity': 0, 'reorder_level': 0}
                )
                old_qty = inventory.quantity

                if adj_type == 'increase':
                    inventory.quantity = old_qty + qty
                    log_qty = qty
                elif adj_type == 'decrease':
                    inventory.quantity = old_qty - qty
                    log_qty = -qty
                else:  # 'set'
                    inventory.quantity = qty
                    log_qty = qty - old_qty
                    if log_qty == 0:
                        messages.info(request, 'No change — quantity already at that value.')
                        return redirect('stock_adjustment')

                inventory.save()
                StockHistory.objects.create(
                    product=product, user=request.user,
                    transaction_type='ADJUSTMENT', quantity=log_qty, reason=reason
                )

            messages.success(request, f'Stock adjusted for "{product.product_name}": {old_qty} \u2192 {inventory.quantity}.')
            return redirect('stock_adjustment')
    else:
        form = StockAdjustmentForm()

    recent = StockHistory.objects.filter(transaction_type='ADJUSTMENT').select_related('product', 'user')[:15]
    return render(request, 'inventory/stock_adjustment.html', {'form': form, 'recent': recent})


@login_required
def stock_history(request):
    entries = StockHistory.objects.select_related('product', 'user').all()

    transaction_type = request.GET.get('type', '')
    if transaction_type:
        entries = entries.filter(transaction_type=transaction_type)

    query = request.GET.get('q', '')
    if query:
        entries = entries.filter(product__product_name__icontains=query)

    paginator = Paginator(entries, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'inventory/stock_history.html', {
        'page_obj': page_obj,
        'query': query,
        'selected_type': transaction_type,
    })


@login_required
def low_stock_alerts(request):
    products = (
        Product.objects
        .select_related('category', 'unit', 'inventory')
        .filter(inventory__quantity__lte=F('inventory__reorder_level'))
        .order_by('inventory__quantity')
    )
    return render(request, 'inventory/low_stock_alerts.html', {'products': products, 'total': products.count()})