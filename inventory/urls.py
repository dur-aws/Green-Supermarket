from django.urls import path
from .views import InventoryStockListView, InventoryStockSearchView, StockAdjustmentCreateView, StockAdjustmentHistoryListView 

urlpatterns = [
    path('', InventoryStockListView.as_view(), name='stock_list'),
    path('search/', InventoryStockSearchView.as_view(), name='inventory_search'),
    path('batch/<int:batch_id>/adjust/', StockAdjustmentCreateView.as_view(), name='adjust_stock'),
    path('adjustments/history/', StockAdjustmentHistoryListView.as_view(), name='adjustment_history'),
]
