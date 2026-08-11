from django.urls import path
from . import views

urlpatterns = [
    path('', views.customer_list, name='customer_list'),
    path('add/', views.customer_add, name='customer_add'),
    path('<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('<int:pk>/deactivate/', views.customer_deactivate, name='customer_deactivate'),
    path('<int:pk>/profile/', views.customer_profile, name='customer_profile'),

    path('<int:customer_id>/membership/add/', views.membership_add, name='membership_add'),
    path('membership/<int:pk>/status/<str:new_status>/', views.membership_update_status, name='membership_update_status'),

    path('api/search/', views.customer_search_api, name='customer_search_api'),
]