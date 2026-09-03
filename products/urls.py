from django.urls import path
from .views import ProductListView, ProductCreateView, ProductSearchView, ProductUpdateView, ProductToggleStatusView, generate_variant_codes

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('search/', ProductSearchView.as_view(), name='product_search'),
    path('create/', ProductCreateView.as_view(), name='product_add'),
    path('<int:pk>/edit/', ProductUpdateView.as_view(), name='product_edit'),
    path('<int:pk>/status/', ProductToggleStatusView.as_view(), name='product_toggle_status'),

    path('generate-codes/', generate_variant_codes, name='generate_variant_codes'),
]