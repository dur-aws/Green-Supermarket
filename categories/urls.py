from django.urls import path
from .views import CategoryListView, CategoryCreateView, CategoryUpdateView, CategoryDeleteView, CategorySearchView

urlpatterns = [
    path('', CategoryListView.as_view(), name='category_list'),
    path('search/', CategorySearchView.as_view(), name='category_search'),
    path('add/',CategoryCreateView.as_view(), name='category_add'),
    path('<int:pk>/edit/',CategoryUpdateView.as_view(), name='category_edit'),
    path('<int:pk>/deactive/',CategoryDeleteView.as_view(), name='category_deactive'),
]