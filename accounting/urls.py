from django.urls import path
from . import views
from .views import (
    ChartOfAccountsView, GeneralLedgerPDFView, GeneralLedgerView, JournalListView,
    TrialBalancePDFView, TrialBalanceView,
    journal_create, journal_delete, journal_edit, journal_post, journal_reverse,
)
urlpatterns = [
    path('fiscal-years/', views.fiscal_year_list, name='fiscal_year_list'),
    path('fiscal-years/create/', views.fiscal_year_create, name='fiscal_year_create'),
    path('fiscal-years/<int:pk>/activate/', views.fiscal_year_activate, name='fiscal_year_activate'),
    path('fiscal-years/<int:pk>/close/', views.fiscal_year_toggle_close, name='fiscal_year_toggle_close'),
    path('journal/', JournalListView.as_view(), name='journal_view'),
    path('journal/new/', journal_create, name='journal_create'),
    path('journal/<int:pk>/edit/', journal_edit, name='journal_edit'),
    path('journal/<int:pk>/post/', journal_post, name='journal_post'),
    path('journal/<int:pk>/reverse/', journal_reverse, name='journal_reverse'),
    path('journal/<int:pk>/delete/', journal_delete, name='journal_delete'),
    path('chart-of-accounts/', ChartOfAccountsView.as_view(), name='chart_of_accounts'),
    path('general-ledger/', GeneralLedgerView.as_view(), name='general_ledger'),
    path('general-ledger/pdf/', GeneralLedgerPDFView.as_view(), name='general_ledger_pdf'),
    path('trial-balance/', TrialBalanceView.as_view(), name='trial_balance'),
    path('trial-balance/pdf/', TrialBalancePDFView.as_view(), name='trial_balance_pdf'),
]

