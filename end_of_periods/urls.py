# chartofaccounts/urls.py
from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [
   
 
    path('calculate-interest/', views.calculate_interest, name='calculate_interest'),
 
    path('success/', views.success, name='success'),

    path('end_of_periods/', views.end_of_periods, name='end_of_periods'),
   
  

]