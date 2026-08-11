from django.urls import path
from . import views

urlpatterns = [
    path('', views.sales_invoice, name='sales_invoice'),
    # path('product-search/', views.product_search, name='product_search'),
    path('api/customer-search/', views.customer_search_api, name='sale_customer_search'),
    path('checkout/', views.checkout_view, name='sale_checkout'),
    path('history/', views.sale_history_view, name='sale_history'),
    path('<int:pk>/', views.sale_detail_view, name='sale_detail'),
    path('<int:pk>/invoice/', views.invoice_print_view, name='sale_invoice_print'),
    path('<int:pk>/cancel/', views.sale_cancel_view, name='sale_cancel'),
]