from django.urls import path
from .views import CategoryListView, CategoryCreateView, CategoryUpdateView, CategorySearchView, CategoryToggleStatusView

urlpatterns = [
    path('', CategoryListView.as_view(), name='category_list'),
    path('search/', CategorySearchView.as_view(), name='category_search'),
    path('add/',CategoryCreateView.as_view(), name='category_add'),
    path('<int:pk>/edit/',CategoryUpdateView.as_view(), name='category_edit'),
    path('<int:pk>/status/',CategoryToggleStatusView.as_view(), name='category_status'),
]