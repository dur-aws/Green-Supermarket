from django.urls import path
from .views import (PurchaseOrderSearchView, PurchaseOrderListView, PurchaseOrderCreateView, 
                    PurchaseOrderUpdateView, PurchaseOrderDetailView, PurchaseOrderCalculateView)

urlpatterns = [
    path('', PurchaseOrderListView.as_view(), name='po_list'),
    path('search/', PurchaseOrderSearchView.as_view(), name='po_search'),
    path('create/', PurchaseOrderCreateView.as_view(), name='po_create'),
    path('calculate/', PurchaseOrderCalculateView.as_view(), name='po_calculate'),
    path('<int:pk>/edit/', PurchaseOrderUpdateView.as_view(), name='po_update'),
    path('<int:pk>/', PurchaseOrderDetailView.as_view(), name='po_detail'),
]