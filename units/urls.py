from django.urls import path
from .views import UnitOfMeasureListView, UnitOfMeasureCreateView, UnitOfMeasureUpdateView, UnitOfMeasureDeleteView, UnitOfMeasureSearchView

urlpatterns = [
    path('', UnitOfMeasureListView.as_view(), name='uom_list'),
    path('search/', UnitOfMeasureSearchView.as_view(), name='uom_search'),
    path('add/',UnitOfMeasureCreateView.as_view(), name='uom_add'),
    path('<int:pk>/edit/',UnitOfMeasureUpdateView.as_view(), name='uom_edit'),
    path('<int:pk>/deactive/',UnitOfMeasureDeleteView.as_view(), name='uom_deactive'),
]