from . import views
from django.urls import path

urlpatterns=[
    path('', views.category_list, name='category_list'),
    path('add/', views.category_add, name='category_add'),
    path('<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('<int:pk>/toggle-status/', views.category_toggle_status, name='category_toggle_status'),
]