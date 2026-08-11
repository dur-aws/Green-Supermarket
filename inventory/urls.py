from django.urls import path
from . import views
 
urlpatterns = [
    path('stock-in/', views.stock_in, name='stock_in'),
    path('stock-out/', views.stock_out, name='stock_out'),
    path('stock-adjustment/', views.stock_adjustment, name='stock_adjustment'),
    path('stock-history/', views.stock_history, name='stock_history'),
    path('low-stock/', views.low_stock_alerts, name='low_stock_alerts'),
]
 