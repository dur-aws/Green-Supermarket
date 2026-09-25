from django.urls import path
from .views import (
    SalesInvoiceView,
    SalesInvoiceDetailView,
    export_sales_record,
    get_next_invoice_no,
    product_search_api,
    checkout_api,
    SalesHistoryView,
    SaleSearchView,
    print_invoice,
    expiry_report_view,
    record_sale_payment,
    
)
from .returns_views import (
    CreditMemoView,
    InventoryReturnReceiptView,
    RefundConfirmView,
    RefundCreateView,
    ReturnReceiveView,
    SalesReturnCreateView,
    SalesReturnDetailView,
    SalesReturnListView,
)

urlpatterns = [
    path('invoice/', SalesInvoiceView.as_view(), name='sales_invoice'),
    
    path('report/',SalesHistoryView.as_view(), name='sales_list'),
    path('search/',SaleSearchView.as_view(), name='sales_search'),
    path('export/',export_sales_record, name='export_sales_record'),
    path('expiry-report/', expiry_report_view, name='expiry_report'),
    path('returns/', SalesReturnListView.as_view(), name='sales_return_list'),
    path('returns/new/', SalesReturnCreateView.as_view(), name='sales_return_create'),
    path('returns/<int:pk>/', SalesReturnDetailView.as_view(), name='sales_return_detail'),
    path('returns/<int:pk>/receive/', ReturnReceiveView.as_view(), name='sales_return_receive'),
    path('returns/receipt/<int:pk>/', InventoryReturnReceiptView.as_view(), name='inventory_return_receipt'),
    path('returns/credit-memo/<int:pk>/', CreditMemoView.as_view(), name='credit_memo'),
    path('returns/credit-memo/<int:pk>/refund/', RefundCreateView.as_view(), name='refund_create'),
    path('returns/credit-memo/<int:pk>/refund/confirm/', RefundConfirmView.as_view(), name='refund_confirm'),
    path('invoice/view/<int:pk>/', SalesInvoiceDetailView.as_view(), name='sale_detail_view'),
    path('invoice/<int:sales_id>/payment/', record_sale_payment, name='record_sale_payment'),
    # Internal JSON APIs consumed by saleinterface JavaScript
    path('api/next-invoice-no/', get_next_invoice_no, name='sales_next_invoice_no'),
    path('api/product-search/', product_search_api, name='sales_product_search'),
    # path('api/generate-fonepay-qr/', generate_fonepay_qr, name='fonepay_qr'),
    path('api/checkout/', checkout_api, name='sales_checkout'),

    path('invoice/<int:sales_id>/print/', print_invoice, name='sales_invoice_print'),
]