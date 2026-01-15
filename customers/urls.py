# chartofaccounts/urls.py
from django.urls import path
from . import views


urlpatterns = [
    path('customers/', views.customers, name='customers'),
    path('api/officers-by-region/', views.get_officers_by_region, name='get_officers_by_region'),
    path('new_accounts/', views.new_accounts, name='new_accounts'),
    path('internal_accounts/', views.internal_accounts, name='internal_accounts'),
    path('customer_list_account/', views.customer_list_account, name='customer_list_account'),
    path('edit_customer/edit/<uuid:uuid>/', views.edit_customer, name='edit_customer'),
    # path('customer/edit/<uuid:uuid>/', views.edit_customer, name='edit_customer'),
    path('customer/delete/<uuid:uuid>/', views.delete_customer, name='delete_customer'),
    




    path('internal_list/', views.internal_list, name='internal_list'),
    path('edit_internal_account/<uuid:uuid>/', views.edit_internal_account, name='edit_internal_account'),
    path('delete_internal_account/<uuid:uuid>/', views.delete_internal_account, name='delete_internal_account'),
    path('choose_to_create_loan/', views.choose_to_create_loan, name='choose_to_create_loan'),
    path('create_loan/<uuid:uuid>/', views.create_loan, name='create_loan'),
    path('choose_create_another_account/', views.choose_create_another_account, name='choose_create_another_account'),
    path('create_another_account/<uuid:uuid>/', views.create_another_account, name='create_another_account'),
    path('manage_customer/', views.manage_customer, name='manage_customer'),
   
    path('customer_list/', views.customer_list, name='customer_list'),
    
    # URL for the customer detail view
    path('customer/<uuid:uuid>/', views.customer_detail, name='customer_detail'),
    path('transactions/<str:gl_no>/<str:ac_no>/', views.transaction_list, name='transaction_list'),
    path("register-fixed-deposit-account/", views.register_fixed_deposit_account, name="register_fixed_deposit_account"),
    path("customer-sms-email-alert/", views.customer_sms_email_alert, name="customer_sms_email_alert"),

    path('register-customer/', views.company_reg, name='company_reg'),

    path('create-group/', views.create_group, name='create_group'),
    path('assign-customers/', views.assign_customers_to_group, name='assign_customers_to_group'),
    path('remove/<uuid:uuid>/', views.remove_from_group, name='remove_from_group'),
    path('group/<uuid:uuid>/', views.group_customers, name='group_customers'),

    path('groups/', views.group_list, name='group_list'),
    path('edit_customer/<uuid:uuid>/', views.edit_company_reg, name='edit_company_reg'),
    path('choose_to_create_company_loan/', views.choose_to_create_company_loan, name='choose_to_create_company_loan'),
    
]
   
