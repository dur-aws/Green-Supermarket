from django.urls import path
from . import views

urlpatterns = [
   path('', views.dashborad_view, name='dashboard_view' ),
   path('today_sales/', views.today_sales, name = 'today_sales'),
   path('total_products/', views.total_products, name = 'total_products'),
   path('invoices_today/', views.invoices_today, name = 'invoices_todays'),
   path('top_categories/', views.top_categories, name = 'top_categories'),
   path('total_products/', views.total_products, name = 'total_products'),
]