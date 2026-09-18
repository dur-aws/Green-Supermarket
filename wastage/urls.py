from django.urls import path

from .views import WastageCreateView, WastageListView


urlpatterns = [
    path('', WastageListView.as_view(), name='wastage_list'),
    path('batch/<int:batch_id>/record/', WastageCreateView.as_view(), name='wastage_create'),
]