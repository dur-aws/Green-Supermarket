import json
import csv
from decimal import Decimal
from datetime import datetime
from django.db import models, transaction
from django.db.models import Q, Sum, F, DecimalField, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, DetailView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import nepali_datetime

from products.models import Product, ProductVariant
from inventory.models import InventoryBatch
from sales.exceptions import SaleError
from sales.services import InvoiceNumberService, SaleCancelService, SaleService
from sales.models import Sale, SaleItem
from accounts.mixins import RBACPermissionMixin


class SalesInvoiceView(RBACPermissionMixin, LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Renders the Sales Invoice POS Interface."""
    template_name = 'sales/sales_invoice.html'
    permission_required = 'sales.add_sale'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today_date'] = timezone.now().strftime('%Y-%m-%d')
        return context


@login_required
@permission_required('sales.add_sale', raise_exception=True)
def get_next_invoice_no(request):
    next_no = InvoiceNumberService.generate_next_number()
    now = timezone.now()
    return JsonResponse({
        'invoice_no': next_no,
        'ad_date': now.strftime('%Y-%m-%d'),
        'bs_date': str(nepali_datetime.date.today()),
        'time': now.strftime('%H:%M:%S')
    })


@login_required
@permission_required('sales.view_sale', raise_exception=True)
def product_search_api(request):
    """
    FEFO Product & Expiry-Aware Batch Search API.
    Returns active, unexpired inventory batches with current_quantity > 0,
    sorted by expiry date ascending.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    today = timezone.now().date()

    # Query Active, Non-Expired Inventory Batches ordered by Expiry (FEFO)
    batches = InventoryBatch.objects.filter(
        Q(variant__product__product_name__icontains=query) |
        Q(variant__barcode__icontains=query) |
        Q(variant__sku__icontains=query) |
        Q(batch_number__icontains=query),
        batch_status=InventoryBatch.BatchStatus.ACTIVE,
        current_quantity__gt=Decimal('0.000'),
        expiry_date__gte=today  # Prevents expired stock from appearing in POS
    ).select_related('variant', 'variant__product').order_by('expiry_date')[:15]

    results = []
    for b in batches:
        v = b.variant
        days_left = (b.expiry_date - today).days
        
        # Determine Urgency Level based on ABC Criteria
        urgency_tag = 'CRITICAL' if days_left <= 15 else ('WARNING' if days_left <= 60 else 'OK')

        results.append({
            'batch_id': b.batch_id,
            'batch_number': b.batch_number,
            'id': v.product.product_id,
            'variant_id': v.variant_id,
            'name': v.product.product_name,
            'variant': v.variant_name,
            'barcode': v.barcode,
            'price': str(v.selling_price),
            'stock': str(b.current_quantity),
            'unit': getattr(v.primary_uom, 'unit_name', 'Pcs') if hasattr(v, 'primary_uom') else 'Pcs',
            'vat': v.vat_status,
            'expiry_date': b.expiry_date.strftime('%Y-%m-%d'),
            'exp_date': b.expiry_date.strftime('%Y-%m-%d'),
            'days_left': days_left,
            'urgency_tag': urgency_tag
        })

    return JsonResponse({'results': results})


@login_required
@permission_required('sales.add_sale', raise_exception=True)
@require_http_methods(["POST"])
def checkout_api(request):
    try:
        data = json.loads(request.body)

        idempotency_key = data.get('idempotency_key', '')
        fiscal_year = data.get('fiscal_year', '')
        customer_id = data.get('customer_id', 1)
        narration = data.get('narration', '')
        bs_date = data.get('bs_date', '')
        
        tender_amount = data.get('tender_amount', '0.00')
        received_amount = data.get('received_amount', '0.00')
        change_amount = data.get('change_amount', '0.00')
        
        items_data = data.get('items', [])
        payments_data = data.get('payments', [])
        
        overall_discount_amount = Decimal(str(data.get('overall_discount_amount', '0.00')))
        overall_discount_percent = Decimal(str(data.get('overall_discount_percent', '0.00')))

        # Execute transaction via SaleService
        sale, created = SaleService.create_sale(
            customer_id=customer_id,
            items_data=items_data,
            payments_data=payments_data,
            cashier=request.user,
            idempotency_key=idempotency_key,
            narration=narration,
            tender_amount=tender_amount,
            received_amount=received_amount,
            change_amount=change_amount,
            bs_date=bs_date,
            fiscal_year=fiscal_year,
            overall_discount_amount=overall_discount_amount,  
            overall_discount_percent=overall_discount_percent,
        )

        return JsonResponse({
            'status': 'success',
            'invoice_no': sale.invoice_no,
            'sales_id': sale.sales_id,
            'grand_total': str(sale.grand_total)
        }, status=200 if not created else 201)

    except SaleError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f"Internal server error: {str(e)}"}, status=500)


@login_required
@permission_required('inventory.view_inventorybatch', raise_exception=True)
def expiry_report_view(request):
    """
    Dedicated view for Expiry Reports and Alerts.
    """
    today = timezone.now().date()
    
    batches = InventoryBatch.objects.select_related('variant', 'variant__product', 'supplier').filter(
        current_quantity__gt=Decimal('0.000')
    )

    status = request.GET.get('status')
    if status == 'EXPIRED':
        batches = batches.filter(expiry_date__lt=today)
    elif status == 'CRITICAL':  # Class A (<= 15 days)
        batches = batches.filter(expiry_date__gte=today, expiry_date__lte=today + timezone.timedelta(days=15))
    elif status == 'WARNING':   # Class B (16 to 60 days)
        batches = batches.filter(expiry_date__gt=today + timezone.timedelta(days=15), expiry_date__lte=today + timezone.timedelta(days=60))

    expired_count = InventoryBatch.objects.filter(expiry_date__lt=today, current_quantity__gt=0).count()
    critical_count = InventoryBatch.objects.filter(
        expiry_date__gte=today, 
        expiry_date__lte=today + timezone.timedelta(days=15), 
        current_quantity__gt=0
    ).count()

    context = {
        'batches': batches.order_by('expiry_date'),
        'today': today,
        'expired_count': expired_count,
        'critical_count': critical_count,
    }
    return render(request, 'inventory/expiry_report.html', context)


@login_required
def print_invoice(request, sales_id):
    sale = get_object_or_404(Sale.objects.prefetch_related('items__variant'), pk=sales_id)
    return render(request, 'sales/sales_receipt.html', {'sale': sale})


@login_required
@permission_required('sales.delete_sale', raise_exception=True)
@require_http_methods(["POST"])
def cancel_sale_api(request, sales_id):
    try:
        sale = SaleCancelService.cancel_sale(sales_id=sales_id, cancelled_by=request.user)
        return JsonResponse({'status': 'success', 'message': f"Invoice #{sale.invoice_no} cancelled successfully."})
    except SaleError as e:
        return JsonResponse({'error': str(e)}, status=400)


class SalesInvoiceDetailView(RBACPermissionMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Sale
    template_name = 'sales/invoice_detail.html'
    context_object_name = 'sale'
    pk_url_kwarg = 'pk'
    permission_required = 'sales.view_sale'


class SalesHistoryView(RBACPermissionMixin, LoginRequiredMixin, ListView):
    model = Sale
    permission_required = 'sales.view_sale'
    template_name = 'sales_list.html'
    context_object_name = 'sales'
    paginate_by = 15

    def get_queryset(self):
        queryset = Sale.objects.select_related('customer', 'user').prefetch_related('items').order_by('-sale_date', '-invoice_no')

        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(invoice_no__icontains=q) |
                Q(buyer_name__icontains=q) |
                Q(customer__name__icontains=q)
            )

        from_date_str = self.request.GET.get('from_date')
        to_date_str = self.request.GET.get('to_date')

        if from_date_str:
            try:
                from_date = datetime.strptime(from_date_str.replace('/', '-'), '%Y-%m-%d').date()
                queryset = queryset.filter(sale_date__gte=from_date)
            except ValueError:
                pass

        if to_date_str:
            try:
                to_date = datetime.strptime(to_date_str.replace('/', '-'), '%Y-%m-%d').date()
                queryset = queryset.filter(sale_date__lte=to_date)
            except ValueError:
                pass

        status = self.request.GET.get('payment_status')
        if status:
            queryset = queryset.filter(payment_status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtered_qs = self.get_queryset()
        
        totals = filtered_qs.aggregate(
            grand_total=Coalesce(Sum('grand_total'), Value(0.00), output_field=DecimalField()),
            tender_amount=Coalesce(Sum('tender_amount'), Value(0.00), output_field=DecimalField()),
        )
        totals['pending_amount'] = totals['grand_total'] - totals['tender_amount']
        
        context['totals'] = totals
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('export') == 'excel':
            return self.export_to_csv(self.get_queryset())
        return super().render_to_response(context, **response_kwargs)

    def export_to_csv(self, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Sales_Report.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Invoice No', 'Date', 'Party Name', 'Items Count', 
            'Sub Total', 'vat', 'Grand Total', 'Received Amount', 'Status', 'User'
        ])

        for sale in queryset:
            party_name = sale.buyer_name or (sale.customer.name if sale.customer else 'Walk-in Customer')
            writer.writerow([
                f"{sale.fiscal_year}/{sale.invoice_no}",
                sale.sale_date.strftime('%Y-%m-%d'),
                party_name,
                sale.items.count(),
                sale.subtotal,
                sale.amount,
                sale.grand_total,
                sale.tender_amount,
                sale.payment_status,
                sale.user.username if sale.user else ''
            ])

        return response