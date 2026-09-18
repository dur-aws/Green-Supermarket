from django.urls import path
from .views import (PurchaseOrderSearchView, PurchaseOrderListView, PurchaseOrderCreateView, 
                    PurchaseOrderUpdateView, PurchaseOrderDetailView, PurchaseOrderCalculateView,
                    PurchaseReturnListView, PurchaseReturnCreateView, PurchasePaymentCreateView)

urlpatterns = [
    path('', PurchaseOrderListView.as_view(), name='po_list'),
    path('search/', PurchaseOrderSearchView.as_view(), name='po_search'),
    path('create/', PurchaseOrderCreateView.as_view(), name='po_create'),
    path('calculate/', PurchaseOrderCalculateView.as_view(), name='po_calculate'),
    path('returns/', PurchaseReturnListView.as_view(), name='purchase_return_list'),
    path('returns/batch/<int:batch_id>/record/', PurchaseReturnCreateView.as_view(), name='purchase_return_create'),
    path('returns/<int:return_id>/edit/', PurchaseReturnCreateView.as_view(), name='purchase_return_edit'),
    path('<int:pk>/edit/', PurchaseOrderUpdateView.as_view(), name='po_update'),
    path('<int:pk>/payments/create/', PurchasePaymentCreateView.as_view(), name='purchase_payment_create'),
    path('<int:pk>/', PurchaseOrderDetailView.as_view(), name='po_detail'),
]