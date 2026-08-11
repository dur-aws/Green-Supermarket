from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('search/', views.product_search, name='product_search'),
    path('add/', views.product_add, name='product_add'),
    path('<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('<int:pk>/deactivate/', views.product_deactivate, name='product_deactivate'),
    path('<int:pk>/toggle-status/', views.product_toggle_status, name='product_toggle_status'),
]