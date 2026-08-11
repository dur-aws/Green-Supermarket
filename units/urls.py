from django.urls import path
from . import views

urlpatterns=[
    path('', views.unit_list, name='unit_list'),
    path('add/', views.unit_add, name='unit_add'),
    path('<int:pk>/edit/', views.unit_edit, name='unit_edit'),
    path('<int:pk>/toggle-status/', views.unit_toggle_status, name='unit_toggle_status'),
]