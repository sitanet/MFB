# chartofaccounts/urls.py
from django.urls import path
from . import views 


urlpatterns = [
    path('chart_of_accounts/', views.chart_of_accounts, name='chart_of_accounts'),
    path('success/', views.success_view, name='success_view'),
    path('update_chart_of_account/<uuid:uuid>/', views.update_chart_of_account, name='update_chart_of_account'),
    path('delete_chart_of_account/<uuid:uuid>/delete', views.delete_chart_of_account, name='delete_chart_of_account'),
    path('cannot_delete/', views.cannot_delete, name='cannot_delete'),
    path('account_settings/', views.account_settings, name='account_settings'),
    path('software_reg/', views.software_reg, name='software_reg'),
    path('user_define/', views.user_define, name='user_define'),


    path('account_officer_list/', views.account_officer_list, name='account_officer_list'),
    path('create_account_officer/', views.create_account_officer, name='create_account_officer'),
    path('update_account_officer/update/<uuid:uuid>/', views.update_account_officer, name='update_account_officer'),
    path('<uuid:uuid>/delete/', views.account_officer_delete, name='account_officer_delete'),



    path('region_list/', views.region_list, name='region_list'),
    path('create_region/', views.create_region, name='create_region'),
    path('update_region/update/<uuid:uuid>/', views.update_region, name='update_region'),
    path('region/<uuid:uuid>/delete/', views.region_delete, name='region_delete'),
   



    path('category_list/', views.category_list, name='category_list'),
    path('create_category/', views.create_category, name='create_category'),
    path('update_category/update/<uuid:uuid>/', views.update_category, name='update_category'),
    path('category/<uuid:uuid>/delete/', views.category_delete, name='category_delete'),




    path('id_type_list/', views.id_type_list, name='id_type_list'),
    path('create_id_type/', views.create_id_type, name='create_id_type'),
    path('update_id_type/update/<uuid:uuid>/', views.update_id_type, name='update_id_type'),
    path('id_type/<uuid:uuid>/delete/', views.id_type_delete, name='id_type_delete'),

    path('create_bus_sector/', views.create_bus_sector, name='create_bus_sector'),       
    path('bus_sec_list/', views.bus_sec_list, name='bus_sec_list'),
    path('update_bus_sector/update/<uuid:uuid>/', views.update_bus_sector, name='update_bus_sector'),
    path('bus_sec/<uuid:uuid>/delete/', views.bus_sec_delete, name='bus_sec_delete'),
    path('product_settings/', views.product_settings, name='product_settings'),
   
    path('create_product_type/', views.create_product_type, name='create_product_type'),
    path('update_product_type/', views.update_product_type, name='update_product_type'),
    # path('update_account/', views.update_account, name='update_account'),
    path('account_list/', views.account_list, name='account_list'),
    path('update_account/edit/<uuid:uuid>/', views.update_account, name='update_account'),
    path('account/delete/<uuid:uuid>/', views.delete_account, name='delete_account'),
    path('utilities/', views.utilities, name='utilities'),
    path('add_interest_rate/', views.add_interest_rate, name='add_interest_rate'),
   
    
    path('add/', views.add_loan_provision, name='add_loan_provision'),
    path('list/', views.loan_provision_list, name='loan_provision_list'),
    path('edit/<uuid:uuid>/', views.edit_loan_provision, name='edit_loan_provision'),  # Edit loan provision
    path('delete/<uuid:uuid>/', views.delete_loan_provision, name='delete_loan_provision'),  # Delete loan provision
    
    # Customer Account Type Management
    path('customer-account-types/', views.customer_account_type_list, name='customer_account_type_list'),
    path('customer-account-types/create/', views.customer_account_type_create, name='customer_account_type_create'),
    path('customer-account-types/edit/<uuid:uuid>/', views.customer_account_type_edit, name='customer_account_type_edit'),
    path('customer-account-types/delete/<uuid:uuid>/', views.customer_account_type_delete, name='customer_account_type_delete'),
    path('customer-account-types/toggle/<uuid:uuid>/', views.customer_account_type_toggle, name='customer_account_type_toggle'),
    
    # Loan Auto Repayment Settings
    path('loan-auto-repayment/', views.loan_auto_repayment_list, name='loan_auto_repayment_list'),
    path('loan-auto-repayment/toggle/<uuid:uuid>/', views.loan_auto_repayment_toggle, name='loan_auto_repayment_toggle'),
]
