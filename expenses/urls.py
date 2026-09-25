from django.urls import path

from .views import ExpenseCreateView, ExpenseListView


urlpatterns = [
    path('', ExpenseListView.as_view(), name='expense_list'),
    path('create/', ExpenseCreateView.as_view(), name='expense_create'),
]