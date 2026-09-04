# =============================================================
# dashboard/urls.py  --  MERGE with your existing file
# =============================================================
# Your current file has a couple of small bugs worth fixing while
# you're in here:
#   1. "total_products" is registered twice — remove the duplicate.
#   2. "invoices_todays" (typo) should be "invoices_today" so it
#      matches the view name / what the template expects.
# =============================================================

from django.urls import path
from .views import (dashboard_view, LowStockView, sales_trend_api, dashboard_expiry_alerts_api, dashboard_expiry_rows,
                    recent_notifications_api, notification_history)

urlpatterns = [
    path("", dashboard_view, name="dashboard"),

#     # existing partial endpoints (kept, typo fixed)
#     path("today_sales/", views.today_sales, name="today_sales"),
#     path("total_products/", views.total_products, name="total_products"),
#     path("invoices_today/", views.invoices_today, name="invoices_today"),
#     path("net_profit/", views.net_profit, name="net_profit"),
#     path("top_categories/", views.top_categories, name="top_categories"),

#     # --- NEW: widget endpoints used by dashboard.js ---
#     path("api/kpis/", views.dashboard_kpis, name="dashboard_kpis"),
    path("api/sales-trend/", sales_trend_api, name="dashboard_sales_trend"),
#     path("api/top-categories/", views.dashboard_top_categories, name="dashboard_top_categories"),
#     path("api/top-products/", views.dashboard_top_products, name="dashboard_top_products"),
    #  path("api/recent-sales/", dashboard_recent_sales, name="dashboard_recent_sales"),
    path("api/expiry-alerts/", dashboard_expiry_alerts_api, name="dashboard-expiry-alerts"),
    path("api/expiry-rows/", dashboard_expiry_rows, name="dashboard-expiry-alert"),
    path("api/low-stock/", LowStockView.as_view(), name="dashboard_low_stock"),
#     path("api/pending-po/", views.dashboard_pending_po, name="dashboard_pending_po"),

    
    path('notifications/api/recent/', recent_notifications_api, name='recent_notifications_api'),
    path('notifications/history/', notification_history, name='notification_history'),
]


# =============================================================
# Also needed for the "View all" quick-links to work:
# =============================================================
# 1) sales/urls.py does not exist yet in your project — create it:
#
#    from django.urls import path
#    from . import views
#
#    urlpatterns = [
#        path("invoice/", views.sales_invoice, name="sales_invoice"),
#        path("history/", views.sale_history_view, name="sale_history_view"),
#        path("<int:pk>/", views.sale_detail_view, name="sale_detail_view"),
#        path("<int:pk>/print/", views.invoice_print_view, name="invoice_print_view"),
#        path("<int:pk>/cancel/", views.sale_cancel_view, name="sale_cancel_view"),
#        path("product-search/", views.product_search, name="sales_product_search"),
#        path("customer-search/", views.customer_search_api, name="sales_customer_search_api"),
#        path("checkout/", views.checkout_view, name="checkout_view"),
#    ]
#
#    ...then add  path("sales/", include("sales.urls"))  to gsms/urls.py
#
# 2) inventory/urls.py only wires up stock_list right now. Add:
#
#    path("in/", views.stock_in, name="stock_in"),
#    path("out/", views.stock_out, name="stock_out"),
#    path("adjustment/", views.stock_adjustment, name="stock_adjustment"),
#    path("history/", views.stock_history, name="stock_history"),
#    path("low-stock/", views.low_stock_alerts, name="low_stock_alerts"),