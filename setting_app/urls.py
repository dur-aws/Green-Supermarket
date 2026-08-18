
from django.urls import path
from .views import LogActivityListView
urlpatterns = [
   
    path('', LogActivityListView.as_view(), name='activity-log'),
]