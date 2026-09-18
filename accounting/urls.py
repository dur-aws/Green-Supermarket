from django.urls import path
from . import views
from .views import JournalListView 
urlpatterns = [
    path('fiscal-years/', views.fiscal_year_list, name='fiscal_year_list'),
    path('fiscal-years/create/', views.fiscal_year_create, name='fiscal_year_create'),
    path('fiscal-years/<int:pk>/activate/', views.fiscal_year_activate, name='fiscal_year_activate'),
    path('fiscal-years/<int:pk>/close/', views.fiscal_year_toggle_close, name='fiscal_year_toggle_close'),
    path('journal/', JournalListView.as_view(), name='journal_view'),
]

