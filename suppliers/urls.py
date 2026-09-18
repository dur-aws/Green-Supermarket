from django.urls import path
from .views import (
    SupplierListView, SupplierCreateView, SupplierUpdateView, SupplierToggleStatusView,
    SupplierSearchView, SupplierPurchaseOrderListView, SupplierPayablesSummaryView,
    SupplierPurchaseOrderActionView,
    SupplierPurchaseDetailResponseView, SupplierVendorReceiptView,
)

urlpatterns = [
    path('orders/', SupplierPurchaseOrderListView.as_view(), name='supplier_po_list'),
    path('payables/', SupplierPayablesSummaryView.as_view(), name='supplier_payables'),
    path('orders/<int:pk>/<str:action>/', SupplierPurchaseOrderActionView.as_view(), name='supplier_po_action'),
    path('orders/<int:pk>/items/<int:detail_id>/<str:response>/', SupplierPurchaseDetailResponseView.as_view(), name='supplier_po_item_response'),
    path('orders/<int:pk>/receipt/', SupplierVendorReceiptView.as_view(), name='supplier_vendor_receipt'),

    path('', SupplierListView.as_view(), name='supplier_list'),
    path('search/', SupplierSearchView.as_view(), name='supplier_search'),
    path('add/',SupplierCreateView.as_view(), name='supplier_add'),
    path('<int:pk>/edit/',SupplierUpdateView.as_view(), name='supplier_edit'),
    path('<int:pk>/status/',SupplierToggleStatusView.as_view(), name='supplier_status'),
]