import json
from decimal import Decimal
from django.db import models, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views.generic import TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
import nepali_datetime

from products.models import Product, ProductVariant
from inventory.models import InventoryBatch
from sales.exceptions import SaleError
from sales.services import InvoiceNumberService, SaleCancelService, SaleService
from .models import Sale, SaleItem
from django.views.generic import ListView
from django.db.models import Sum,  F, DecimalField, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from accounts.mixins import RBACPermissionMixin
import csv


class SalesInvoiceView(RBACPermissionMixin,LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Renders the Sales Invoice POS Interface.
    """
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
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    # Search in ProductVariant and join Product
    variants = ProductVariant.objects.filter(
        Q(product__product_name__icontains=query) |
        Q(barcode__icontains=query) |
        Q(sku__icontains=query)
    ).select_related('product')[:10]

    results = []
    for v in variants:
        results.append({
            'id': v.product.product_id,
            'name': v.product.product_name,
            'variant': v.variant_name,   # <-- include variant name
            'barcode': v.barcode,
            'price': v.selling_price,
            'stock': v.total_active_stock,
            'unit': v.primary_uom.unit_name,
            'vat':v.vat_status
        })
    
    return JsonResponse({'results': results})

import base64
@login_required
@permission_required('sales.add_sale', raise_exception=True)
def generate_fonepay_qr(request):
    """
    Generates dynamic Fonepay payment parameters/QR code string for the current bill amount.
    """
    amount = request.GET.get('amount', '0.00')
    invoice_no = request.GET.get('invoice_no', '')

    # Example Merchant Payload Structure (Adapt based on your official Fonepay credentials)
    merchant_code = "YOUR_MERCHANT_CODE"
    
    # Simple static QR rendering payload fallback or dynamic link generation
    qr_data = f"fonepay://pay?merchant={merchant_code}&amount={amount}&remarks={invoice_no}"
    
    # Return QR image source via Google Chart API or QR Generator
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={qr_data}"

    return JsonResponse({
        'status': 'success',
        'qr_url': qr_url,
        'amount': amount,
        'invoice_no': invoice_no
    })

@login_required
@permission_required('sales.add_sale', raise_exception=True)
@require_http_methods(["POST"])
def checkout_api(request):
    try:
        data = json.loads(request.body)
        sale, created = SaleService.create_sale(
            customer_id=data.get('customer_id', 1),
            items_data=data.get('items', []),
            payments_data=data.get('payments', []),
            cashier=request.user,
            idempotency_key=data.get('idempotency_key'),
            date_bs=data.get('bs_date'),
            fiscal_year=data.get('fiscal_year'),
            narration=data.get('narration', ''),
            tender_amount= data.get('tender_amount'),
            received_amount= data.get('received_amount'),
            change_amount= data.get('change_amount'),
        )
        return JsonResponse({'status': 'success', 'invoice_no': sale.invoice_no, 'sale_id': sale.sales_id}, status=201)
    except SaleError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f"Unexpected Error: {str(e)}"}, status=500)


@login_required
@permission_required('sales.delete_sale', raise_exception=True)
@require_http_methods(["POST"])
def cancel_sale_api(request, sale_id):
    try:
        sale = SaleCancelService.cancel_sale(sale_id=sale_id, cancelled_by=request.user)
        return JsonResponse({'status': 'success', 'message': f"Invoice #{sale.invoice_no} cancelled successfully."})
    except SaleError as e:
        return JsonResponse({'error': str(e)}, status=400)
class SalesInvoiceDetailView(RBACPermissionMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Renders the printable invoice.
    """
    model = Sale
    template_name = 'sales/invoice_detail.html'
    context_object_name = 'sale'
    pk_url_kwarg = 'sales_id'
    permission_required = 'sales.view_sale'




class SalesHistoryView(RBACPermissionMixin, LoginRequiredMixin, ListView):
    model = Sale
    template_name = 'sales_list.html'
    context_object_name = 'sales'
    paginate_by = 15

    def get_queryset(self):
        queryset = Sale.objects.select_related('customer', 'user').prefetch_related('items').order_by('-sale_date', '-invoice_no')

        # 1. Search Query (Invoice number or Party Name)
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(invoice_no__icontains=q) |
                Q(buyer_name__icontains=q) |
                Q(customer__name__icontains=q)
            )

        # 2. Date Range Filters
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')
        if from_date:
            queryset = queryset.filter(sale_date__gte=from_date)
        if to_date:
            queryset = queryset.filter(sale_date__lte=to_date)

        # 3. Payment Status Filter
        status = self.request.GET.get('Payment_status')
        if status:
            queryset = queryset.filter(payment_status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate summary metrics over filtered queryset (ignoring pagination limits)
        filtered_qs = self.get_queryset()
        
        totals = filtered_qs.aggregate(
            grand_total=Coalesce(Sum('grand_total'), Value(0.00), output_field=DecimalField()),
            tender_amount=Coalesce(Sum('tender_amount'), Value(0.00), output_field=DecimalField()),
        )
        
        # Calculate pending amount as (grand_total - tender_amount)
        totals['pending_amount'] = totals['grand_total'] - totals['tender_amount']
        
        context['totals'] = totals
        return context

    def render_to_response(self, context, **response_kwargs):
        # Handle Excel/CSV Export Request
        if self.request.GET.get('export') == 'excel':
            return self.export_to_csv(self.get_queryset())
        return super().render_to_response(context, **response_kwargs)

    def export_to_csv(self, queryset):
        """Generates and downloads a CSV report of the filtered sales list."""
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