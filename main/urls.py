from django.urls import path
from .views import statistics, index


urlpatterns = [
    path('', index, name='index'), 
    path("api/statistics/", statistics, name="statistics"),
]
