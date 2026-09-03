from django.urls import path
from .views import (
    SalesInvoiceView,
    SalesInvoiceDetailView,
    generate_fonepay_qr,
    get_next_invoice_no,
    product_search_api,
    checkout_api,
    SalesHistoryView
)

urlpatterns = [
    path('invoice/', SalesInvoiceView.as_view(), name='sales_invoice'),
    path('invoice/<int:sales_id>/', SalesInvoiceDetailView.as_view(), name='sale_detail'),
    path('report/',SalesHistoryView.as_view(), name='sales_list'),
    
    # Internal JSON APIs consumed by saleinterface JavaScript
    path('api/next-invoice-no/', get_next_invoice_no, name='sales_next_invoice_no'),
    path('api/product-search/', product_search_api, name='sales_product_search'),
    path('api/generate-fonepay-qr/', generate_fonepay_qr, name='fonepay_qr'),
    path('api/checkout/', checkout_api, name='sales_checkout'),
]