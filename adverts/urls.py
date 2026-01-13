# adverts/urls.py
from django.urls import path
from . import views

app_name = 'adverts'

urlpatterns = [
    # API endpoints for mobile app
    path('api/', views.AdvertListAPIView.as_view(), name='api_advert_list'),
    path('api/<uuid:uuid>/view/', views.AdvertViewAPIView.as_view(), name='api_advert_view'),
]