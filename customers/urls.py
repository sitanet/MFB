# chartofaccounts/urls.py
from django.urls import path
from . import views


urlpatterns = [
    path('customers/', views.customers, name='customers'),
    path('new_accounts/', views.new_accounts, name='new_accounts'),
    path('internal_accounts/', views.internal_accounts, name='internal_accounts'),
    path('customer_list_account/', views.customer_list_account, name='customer_list_account'),
    path('edit_customer/edit/<int:id>/', views.edit_customer, name='edit_customer'),
    # path('customer/edit/<int:pk>/', views.edit_customer, name='edit_customer'),
    path('customer/delete/<int:id>/', views.delete_customer, name='delete_customer'),
    




    path('internal_list/', views.internal_list, name='internal_list'),
    path('edit_internal_account/<int:id>/', views.edit_internal_account, name='edit_internal_account'),
    path('delete_internal_account/<int:id>/', views.delete_internal_account, name='delete_internal_account'),
    path('choose_to_create_loan/', views.choose_to_create_loan, name='choose_to_create_loan'),
    path('create_loan/<int:id>/', views.create_loan, name='create_loan'),
    path('choose_create_another_account/', views.choose_create_another_account, name='choose_create_another_account'),
    path('create_another_account/<int:id>/', views.create_another_account, name='create_another_account'),
    path('manage_customer/', views.manage_customer, name='manage_customer'),
   
    path('customer_list/', views.customer_list, name='customer_list'),
    
    # URL for the customer detail view
    path('customer/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('transactions/<str:gl_no>/<str:ac_no>/', views.transaction_list, name='transaction_list'),


]
   

