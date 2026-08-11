
# Create your views here.
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, ProtectedError, F
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.http import JsonResponse
from .models import Product, Category, Unit
from .forms import ProductForm

 
def generate_barcode():
    while True:
        code = ''.join([str(random.randint(0, 9)) for _ in range(9)])
        if not Product.objects.filter(barcode=code).exists():
            return code
 
def _filtered_products(request):
    """Shared filter logic used by both the initial page load and the
    live search API, so the two never drift out of sync."""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    stock_status = request.GET.get('stock_status', '')
 
    products = Product.objects.select_related('category', 'unit', 'inventory').order_by('product_name')
 
    if query:
        products = products.filter(
            Q(product_name__icontains=query) |
            Q(barcode__icontains=query) |
            Q(brand__icontains=query)
        )
    if category_id:
        products = products.filter(category_id=category_id)
 
    if stock_status == 'out-of-stock':
        products = products.filter(inventory__quantity=0)
    elif stock_status == 'low-stock':
        products = products.filter(inventory__quantity__gt=0, inventory__quantity__lte=F('inventory__reorder_level'))
    elif stock_status in ['active']:
        products = products.filter(status=1, inventory__quantity__gt=F('inventory__reorder_level'))
    elif stock_status in ['disabled']:
        products = products.filter(status=0)
    return products, query, category_id, stock_status
 
 
def _stats():
    all_products = Product.objects.select_related('inventory')
    return {
        'total': all_products.count(),
        'active': all_products.filter(inventory__quantity__gt=F('inventory__reorder_level')).count(),
        'low_stock': all_products.filter(inventory__quantity__gt=0, inventory__quantity__lte=F('inventory__reorder_level')).count(),
        'out_of_stock': all_products.filter(inventory__quantity=0).count(),
    }
 
 
@login_required
def product_search(request):
    try:
        products, query, category_id, stock_status = _filtered_products(request)
        total_filtered = products.count()
        products_page = products[:100]

        rows_html = render_to_string('products/product_rows.html', {'products': products_page}, request=request)

        return JsonResponse({
            'rows_html': rows_html,
            'total_filtered': total_filtered,
            'showing_count': min(total_filtered, 100),
        })
    except Exception as e:
        # Fallback to prevent JS undefined crash if a backend error occurs
        return JsonResponse({'rows_html': f'<tr><td colspan="12" class="text-center text-danger">Error filtering products: {str(e)}</td></tr>', 'total_filtered': 0, 'showing_count': 0}, status=400)
 
@login_required
def product_list(request):
    """Initial page load — renders the full page (extends base.html)
    with real data from the database. Subsequent search/filter
    interactions happen live via product_search, no reload."""
    products, query, category_id, stock_status = _filtered_products(request)
 
    return render(request, 'products/product_list.html', {
        'products': products[:100],  # cap initial render; live search handles the rest
        'categories': Category.objects.all(),
        'query': query,
        'selected_category': category_id,
        'selected_stock_status': stock_status,
        'total_filtered': products.count(),
        'stats': _stats(),
    })
 



@login_required
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            if not product.barcode:
                product.barcode = generate_barcode()
            product.save()
            messages.success(request, f'Product "{product.product_name}" added successfully.')
            return redirect('product_list')
    else:
        form = ProductForm(initial={'barcode': generate_barcode()})
 
    return render(request, 'products/product_form.html', {'form': form, 'title': 'Add Product'})
 
 
@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.product_name}" updated successfully.')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
 
    return render(request, 'products/product_form.html', {'form': form, 'title': 'Edit Product'})
 
 
# ---------- Deactivate (soft delete — keeps Sales history intact) ----------
@login_required
def product_deactivate(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.status = 0 if product.status == 1 else 1
    product.save()
    messages.success(request, f"Product {product.code} status changed to {product.stock_status}.")
 
    return redirect('product_list')
 
 
@login_required
def product_toggle_status(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.status = 0 if product.status == 1 else 1
    product.save()
    state = "active" if product.status == 1 else "desable"
    messages.success(request, f'Product "{product.product_name}" {state}.')
    return redirect('product_list')
 