from django.shortcuts import render
from django.db import models
# Create your views here.

from datetime import date, timedelta
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from .models import Sales, SalesDetail, Product, Inventory, Category, Expense


@login_required(login_url='login')
def dashborad_view(request):
    return render(request, '/dashboard/dashboard.html')



@login_required
def today_sales(request):
    today = date.today()
    yesterday = today - timedelta(days=1)

    today_total = Sales.objects.filter(sale_date=today).aggregate(total=Sum('total_amount'))['total'] or 0
    yesterday_total = Sales.objects.filter(sale_date=yesterday).aggregate(total=Sum('total_amount'))['total'] or 0

    change_pct = 0
    if yesterday_total:
        change_pct = round(((today_total - yesterday_total) / yesterday_total) * 100, 1)

    return JsonResponse({
        "value": f"Rs {today_total:,.0f}",
        "sub": f"{change_pct:+}% vs yesterday"
    })


@login_required
def total_products(request):
    total = Product.objects.filter(status=1).count()
    low_stock = Inventory.objects.filter(quantity__lte=models.F('reorder_level')).count()

    return JsonResponse({
        "value": f"{total:,}",
        "sub": f"{low_stock} low stock alerts"
    })


@login_required
def invoices_today(request):
    today = date.today()
    count = Sales.objects.filter(sale_date=today).count()

    return JsonResponse({
        "value": str(count),
        "sub": f"{count} invoices today"
    })


@login_required
def net_profit(request):
    first_of_month = date.today().replace(day=1)

    sales_total = Sales.objects.filter(sale_date__gte=first_of_month).aggregate(
        total=Sum('total_amount'))['total'] or 0
    expense_total = Expense.objects.filter(expense_date__gte=first_of_month).aggregate(
        total=Sum('amount'))['total'] or 0

    profit = sales_total - expense_total

    return JsonResponse({
        "value": f"₹ {profit:,.0f}",
        "sub": "This month"
    })


@login_required
def top_categories(request):
    data = (
        SalesDetail.objects
        .values('product__category__category_name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:5]
    )

    max_sold = data[0]['total_sold'] if data else 1
    items = [
        {
            "name": row['product__category__category_name'],
            "count": row['total_sold'],
            "pct": round((row['total_sold'] / max_sold) * 100)
        }
        for row in data
    ]

    return JsonResponse({"items": items})