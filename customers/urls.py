from django.urls import path
from . import views

urlpatterns = [
    path('', views.CustomerListView.as_view(), name='customer_list'),
    path('add/', views.CustomerCreateView.as_view(), name='customer_add'),
    path('<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),
    path('<int:pk>/deactivate/', views.CustomerDeactivateView.as_view(), name='customer_deactivate'),
    path('<int:pk>/profile/', views.CustomerProfileView.as_view(), name='customer_profile'),
    path('<int:pk>/purchases/', views.CustomerPurchaseHistoryView.as_view(), name='customer_purchase_history'),
    path('<int:pk>/payments/', views.CustomerPaymentHistoryView.as_view(), name='customer_payment_history'),
    path('dashboard/', views.CRMDashboardView.as_view(), name='crm_dashboard'),
    path('reports/', views.CRMReportsView.as_view(), name='crm_reports'),

    path('<int:customer_id>/membership/add/', views.MembershipCreateView.as_view(), name='membership_add'),
    path('membership/<int:pk>/status/<str:new_status>/', views.MembershipStatusView.as_view(), name='membership_update_status'),

    path('api/search/', views.CustomerSearchAPIView.as_view(), name='customer_search_api'),
    path('api/quick-add/', views.CustomerQuickAddView.as_view(), name='customer_quick_add'),
]