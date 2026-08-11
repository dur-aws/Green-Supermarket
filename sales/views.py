
# Create your views here.

from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q
import json
from decimal import Decimal, InvalidOperation

from products.models import Product, Customer
from .models import Sale
from .services import SaleService, SaleCancelService
from .exceptions import (
    SaleError, InsufficientStockError, InvalidQuantityError,
    InvalidDiscountError, PaymentMismatchError,
)
import bikram_sambat


WALKIN_CUSTOMER_ID = 1


@login_required
def sales_invoice(request):
    """New Sale / POS screen."""
    return render(request, 'sales/sales_invoice.html')

def sales_invoice_view(request):
    #using Nepali Date (BS):
    today_date = bikram_sambat.date.today().strftime('%Y-%m-%d')
    
    context = {
        'today_date': today_date,
    }
    return render(request, 'sales_invoice.html', context)

@login_required
def product_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    products = Product.objects.filter(
        Q(name__icontains=query) | Q(barcode__icontains=query)
    ).select_related('inventory')[:10]

    results = [{
        'product_id': p.product_id,
        'product_name': p.product_name,
        'unit': p.unit.name if p.unit else '',
        'price': str(p.price),
        'tax_percent': str(getattr(p, 'tax_percent', 0)),
        'stock': str(p.inventory.quantity) if hasattr(p, 'inventory') else '0',
        'reorder_level': str(getattr(p, 'reorder_level', 0)),
    } for p in products]

    return JsonResponse({'results': results})


@login_required
def customer_search_api(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    customers = Customer.objects.filter(
        Q(name__icontains=query) | Q(phone__icontains=query)
    ).exclude(id=WALKIN_CUSTOMER_ID)[:10]

    results = [{'id': c.id, 'name': c.name, 'phone': c.phone} for c in customers]
    return JsonResponse({'results': results})
@login_required
@require_http_methods(["POST"])
@csrf_protect
def checkout_view(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request format'}, status=400) #[cite: 3]

    idempotency_key = payload.get('idempotency_key')
    if not idempotency_key:
        return JsonResponse({'error': 'Missing idempotency key'}, status=400) #[cite: 3]

    customer_id = payload.get('customer_id') or WALKIN_CUSTOMER_ID #[cite: 3]
    items_data = payload.get('items', []) #[cite: 3]
    payments_data = payload.get('payments', []) #[cite: 3]
    narration = payload.get('narration', '') #[cite: 3]
    
    date_bs = payload.get('date_bs', '') # Nepali BS Date from client
    fiscal_year = payload.get('fiscal_year', '2081/82') # Fiscal year identifier

    try:
        sale, created = SaleService.create_sale(
            customer_id=customer_id,
            items_data=items_data,
            payments_data=payments_data,
            cashier=request.user,
            idempotency_key=idempotency_key,
            narration=narration,
            date_bs=date_bs,
            fiscal_year=fiscal_year
        )
    except InsufficientStockError as e:
        return JsonResponse({'error': str(e)}, status=409) #[cite: 3]
    except (InvalidQuantityError, InvalidDiscountError) as e:
        return JsonResponse({'error': str(e)}, status=400) #[cite: 3]
    except PaymentMismatchError as e:
        return JsonResponse({'error': str(e)}, status=402) #[cite: 3]
    except SaleError as e:
        return JsonResponse({'error': str(e)}, status=400) #[cite: 3]
    except Exception as e:
        return JsonResponse({'error': 'An error occurred during billing'}, status=400)

    status_code = 201 if created else 200 #[cite: 3]
    return JsonResponse({
        'sale_id': sale.id, #[cite: 3]
        'invoice_no': sale.invoice_no, #[cite: 3]
        'grand_total': str(sale.grand_total), #[cite: 3]
    }, status=status_code)


@login_required
def sale_history_view(request):
    """Cashier sees own sales; Admin sees all — enforced here, not just hidden in template."""
    if request.user.role == 'ADMIN':
        sales = Sale.objects.all()
    else:
        sales = Sale.objects.filter(cashier=request.user)

    sales = sales.select_related('customer', 'cashier')[:200]
    return render(request, 'sales/sale_history.html', {'sales': sales})


@login_required
def sale_detail_view(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('customer', 'cashier'), pk=pk)

    if request.user.role != 'ADMIN' and sale.cashier_id != request.user.id:
        return render(request, '403.html', status=403)

    return render(request, 'sales/sale_detail.html', {'sale': sale})


@login_required
def invoice_print_view(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('customer', 'cashier').prefetch_related('items', 'payments'), pk=pk)

    if request.user.role != 'ADMIN' and sale.cashier_id != request.user.id:
        return render(request, '403.html', status=403)

    return render(request, 'sales/invoice_print.html', {'sale': sale})


@login_required
@permission_required('sales.can_cancel_sale', raise_exception=True)
@require_http_methods(["POST"])
def sale_cancel_view(request, pk):
    """Admin-only — enforced via Django permission, not just hidden button (per our security design)."""
    try:
        sale = SaleCancelService.cancel_sale(pk, cancelled_by=request.user)
    except SaleError as e:
        return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'status': 'cancelled', 'sale_id': sale.id})
