# =============================================================
# dashboard/views.py  --  ADD these to your existing file
# =============================================================
# These sit alongside your existing dashboard_view / today_sales /
# total_products / invoices_today / net_profit / top_categories.
#
# ⚠️ Field names below (e.g. Sales.grand_total, Product.reorder_level,
# PurchaseOrder.status) are my best guess from your model/app list.
# Swap any field name that doesn't match your actual models.py —
# everything else (structure, aggregation logic, JSON shape) will
# still work once names line up.
# =============================================================

from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View

# from .models import Sales, Category, Product, SalesDetail, Inventory, Expense
from customers.models import Customer
from purchases.models import PurchaseOrder
from accounts.mixins import RBACPermissionMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from products.models import ProductVariant
from sales.models import Sale



@login_required
def dashboard_view(request):
    return render(request, 'dashboard.html')

# def _today_range():
#     now = timezone.localtime()
#     start = now.replace(hour=0, minute=0, second=0, microsecond=0)
#     return start, start + timedelta(days=1)


# def _pct_change(today_val, yesterday_val):
#     today_val = float(today_val or 0)
#     yesterday_val = float(yesterday_val or 0)
#     if yesterday_val == 0:
#         return None if today_val == 0 else 100.0
#     return round(((today_val - yesterday_val) / yesterday_val) * 100, 1)


# # -------------------------------------------------------------
# # 1) KPI STRIP  ->  GET /dashboard/api/kpis/
# # -------------------------------------------------------------
# @login_required
# def dashboard_kpis(request):
#     today_start, today_end = _today_range()
#     yesterday_start = today_start - timedelta(days=1)

#     today_sales_qs = Sales.objects.filter(sale_date__gte=today_start, sale_date__lt=today_end)
#     yesterday_sales_qs = Sales.objects.filter(sale_date__gte=yesterday_start, sale_date__lt=today_start)

#     today_sales_total = today_sales_qs.aggregate(t=Sum("grand_total"))["t"] or Decimal("0")
#     yesterday_sales_total = yesterday_sales_qs.aggregate(t=Sum("grand_total"))["t"] or Decimal("0")

#     invoices_today = today_sales_qs.count()
#     invoices_yesterday = yesterday_sales_qs.count()

#     # Net profit today = today's sales total - today's cost of goods sold - today's expenses.
#     # Adjust field names (cost_price, unit_cost, etc.) to match your schema.
#     cogs_today = (
#         SalesDetail.objects.filter(sale__sale_date__gte=today_start, sale__sale_date__lt=today_end)
#         .aggregate(t=Sum(F("quantity") * F("product__cost_price")))["t"]
#         or Decimal("0")
#     )
#     expenses_today = (
#         Expense.objects.filter(sale_date__gte=today_start, sale_date__lt=today_end)
#         .aggregate(t=Sum("amount"))["t"]
#         or Decimal("0")
#     )
#     net_profit_today = today_sales_total - cogs_today - expenses_today

#     cogs_yesterday = (
#         SalesDetail.objects.filter(sale__sale_date__gte=yesterday_start, sale__sale_date__lt=today_start)
#         .aggregate(t=Sum(F("quantity") * F("product__cost_price")))["t"]
#         or Decimal("0")
#     )
#     expenses_yesterday = (
#         Expense.objects.filter(sale_date__gte=yesterday_start, sale_date__lt=today_start)
#         .aggregate(t=Sum("amount"))["t"]
#         or Decimal("0")
#     )
#     net_profit_yesterday = yesterday_sales_total - cogs_yesterday - expenses_yesterday

#     total_products = Product.objects.filter(is_active=True).count()

#     # Low stock = current stock at/under each product's reorder level.
#     low_stock_count = Inventory.objects.filter(
#         quantity_in_stock__lte=F("product__reorder_level")
#     ).count()

#     total_customers = Customer.objects.filter(is_active=True).count()

#     return JsonResponse(
#         {
#             "today_sales": float(today_sales_total),
#             "today_sales_change_pct": _pct_change(today_sales_total, yesterday_sales_total),
#             "invoices_today": invoices_today,
#             "invoices_change_pct": _pct_change(invoices_today, invoices_yesterday),
#             "net_profit": float(net_profit_today),
#             "net_profit_change_pct": _pct_change(net_profit_today, net_profit_yesterday),
#             "total_products": total_products,
#             "low_stock_count": low_stock_count,
#             "total_customers": total_customers,
#         }
#     )


# # -------------------------------------------------------------
# # 2) SALES TREND  ->  GET /dashboard/api/sales-trend/?period=weekly|monthly
# # -------------------------------------------------------------

from django.db.models.functions import Coalesce
from django.views.decorators.http import require_GET
import nepali_datetime

NEPALI_MONTHS = [
    "Baisakh", "Jeth", "Asaar", "Shrawan", "Bhadra", "Aswin",
    "Kartik", "Mangsir", "Poush", "Magh", "Falgun", "Chaitra"
]

@login_required
@require_GET
def sales_trend_api(request):
    period = request.GET.get('period', 'weekly').lower()

    if period == 'weekly':
        labels, values = get_weekly_sales()
    elif period == 'monthly':
        labels, values = get_monthly_sales()
    else:
        return JsonResponse({'error': 'Invalid period parameter.'}, status=400)

    return JsonResponse({
        'period': period,
        'labels': labels,
        'values': values
    })


def get_weekly_sales():
    today = timezone.now().date()
    start_date = today - timedelta(days=6)

    sales_query = (
        Sale.objects.filter(
            sale_date__date__gte=start_date,
            sale_date__date__lte=today,
            sale_status='COMPLETED'
        )
        .values('sale_date__date')
        .annotate(total=Coalesce(Sum('grand_total'), Decimal('0.00')))
    )

    sales_map = {item['sale_date__date']: float(item['total']) for item in sales_query}

    labels = []
    values = []

    for i in range(7):
        current_date = start_date + timedelta(days=i)
        
        # Convert AD Date to BS Date dynamically
        nepali_date = nepali_datetime.date.from_datetime_date(current_date)
        
        # Formats to "Bhadra 12"
        # month_name = NEPALI_MONTHS[nepali_date.month - 1]
        # day_label = f"{month_name} {nepali_date.day}"
        
        # Alternative "05-12" format:
        day_label = f"{nepali_date.month:02d}-{nepali_date.day:02d}"

        labels.append(day_label)
        values.append(sales_map.get(current_date, 0.00))

    return labels, values


def get_monthly_sales():
    """Generates monthly aggregated sales using Bikram Sambat months."""
    sales = Sale.objects.filter(sale_status='COMPLETED')
    monthly_map = {month: 0.00 for month in NEPALI_MONTHS}

    for sale in sales:
        if sale.bs_date:
            try:
                parts = str(sale.bs_date).split('-')
                if len(parts) >= 2:
                    month_num = int(parts[1])
                    if 1 <= month_num <= 12:
                        month_name = NEPALI_MONTHS[month_num - 1]
                        monthly_map[month_name] += float(sale.grand_total)
            except (ValueError, IndexError):
                continue

    return NEPALI_MONTHS, [monthly_map[m] for m in NEPALI_MONTHS]
# # -------------------------------------------------------------
# # 3) TOP CATEGORIES  ->  GET /dashboard/api/top-categories/
# # -------------------------------------------------------------
# @login_required
# def dashboard_top_categories(request):
#     start = timezone.localtime() - timedelta(days=30)

#     rows = (
#         SalesDetail.objects.filter(sale__sale_date__gte=start)
#         .values("product__category__name")
#         .annotate(total_sales=Sum(F("quantity") * F("unit_price")))
#         .order_by("-total_sales")[:6]
#     )

#     grand_total = sum((r["total_sales"] or 0) for r in rows) or 1

#     data = [
#         {
#             "name": r["product__category__name"] or "Uncategorized",
#             "total_sales": float(r["total_sales"] or 0),
#             "pct": round(float(r["total_sales"] or 0) / float(grand_total) * 100, 1),
#         }
#         for r in rows
#     ]
#     return JsonResponse(data, safe=False)


# # -------------------------------------------------------------
# # 4) TOP SELLING PRODUCTS  ->  GET /dashboard/api/top-products/
# # -------------------------------------------------------------
# @login_required
# def dashboard_top_products(request):
#     start = timezone.localtime() - timedelta(days=30)

#     rows = (
#         SalesDetail.objects.filter(sale__sale_date__gte=start)
#         .values("product__name")
#         .annotate(units_sold=Sum("quantity"))
#         .order_by("-units_sold")[:6]
#     )

#     max_units = max((r["units_sold"] or 0) for r in rows) if rows else 1

#     data = [
#         {
#             "name": r["product__name"],
#             "units_sold": r["units_sold"],
#             "pct": round((r["units_sold"] or 0) / max_units * 100, 1),
#         }
#         for r in rows
#     ]
#     return JsonResponse(data, safe=False)


# # -------------------------------------------------------------
# # 5) RECENT SALES (HTML partial)  ->  GET /dashboard/api/recent-sales/
# # -------------------------------------------------------------
# @login_required
# def dashboard_recent_sales(request):
#     sales = Sales.objects.select_related("customer").order_by("-sale_date")[:8]
#     html = render_to_string("dashboard/_recent_sales_rows.html", {"sales": sales}, request=request)
#     return _html_response(html)


# # -------------------------------------------------------------
# # 6) LOW STOCK ROWS (HTML partial)  ->  GET /dashboard/api/low-stock/
# # -------------------------------------------------------------


class LowStockView(RBACPermissionMixin, LoginRequiredMixin, View):
    model = ProductVariant
    template_name = 'low_stock_rows.html'
    context_object_name = 'products'

    module_name = 'dashboard'
    required_permission = 'view'

    def get(self, request, *args, **kwargs):
        """Return JSON response of low/out-of-stock variants."""
        variants = ProductVariant.objects.all()
        low_stock = [v for v in variants if v.stock_status in ["low-stock", "out-of-stock"]]

        data = [
            {
                "id": v.variant_id,
                "product": v.product.product_name,
                "variant": v.variant_name,
                "stock_status": v.stock_status,
                "total_active_stock": str(v.total_active_stock),
                "reorder_level": str(v.reorder_level),
                "unit":v.primary_uom.notation
            }
            for v in low_stock
        ]

         # Render HTML component
        low_stock_html = render_to_string(
                    self.template_name,
                    {'items': variants, 'data': data},
                    request=request
                )
        
                # Return JSON if requested via AJAX/Fetch, else return the HTML string response
        # if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
            # return JsonResponse({'html': low_stock_html, 'data': data}, safe=False)
        
        return HttpResponse(low_stock_html)
# @login_required
# def dashboard_low_stock(request):
#     items = (
#         Inventory.objects.select_related("product")
#         .filter(quantity_in_stock__lte=F("product__reorder_level"))
#         .order_by("quantity_in_stock")[:8]
#     )
#     html = render_to_string("dashboard/_low_stock_rows.html", {"items": items}, request=request)
#     return _html_response(html)


# # -------------------------------------------------------------
# # 7) PENDING PURCHASE ORDERS (HTML partial)  ->  GET /dashboard/api/pending-po/
# # -------------------------------------------------------------
# @login_required
# def dashboard_pending_po(request):
#     orders = (
#         PurchaseOrder.objects.select_related("supplier")
#         .filter(status__iexact="pending")
#         .order_by("-sale_date")[:8]
#     )
#     html = render_to_string("dashboard/_pending_po_rows.html", {"orders": orders}, request=request)
#     return _html_response(html)


# def _html_response(html):
#     from django.http import HttpResponse
#     return HttpResponse(html, content_type="text/html")