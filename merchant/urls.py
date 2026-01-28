from django.urls import path
from . import views

app_name = 'merchant'

urlpatterns = [
    # ==============================================================================
    # FINANCEFLEX ADMIN URLS - For managing merchants
    # ==============================================================================
    
    # Merchant Management
    path('', views.merchant_list, name='merchant_list'),
    path('create/', views.merchant_create, name='merchant_create'),
    path('<int:merchant_id>/', views.merchant_detail, name='merchant_detail'),
    path('<int:merchant_id>/update/', views.merchant_update, name='merchant_update'),
    path('<int:merchant_id>/activate/', views.merchant_activate, name='merchant_activate'),
    path('<int:merchant_id>/suspend/', views.merchant_suspend, name='merchant_suspend'),
    path('<int:merchant_id>/transactions/', views.merchant_transactions_admin, name='merchant_transactions_admin'),
    path('<int:merchant_id>/activity/', views.merchant_activity_admin, name='merchant_activity_admin'),
    
    # All Merchants Transactions & Reports
    path('transactions/all/', views.all_merchant_transactions, name='all_transactions'),
    path('reports/', views.merchant_reports_admin, name='reports_admin'),
    path('service-config/', views.merchant_service_config, name='service_config'),
    
    # ==============================================================================
    # MERCHANT PORTAL URLS - For merchant's own interface
    # ==============================================================================
    
    # Authentication
    path('portal/login/', views.merchant_login, name='portal_login'),
    path('portal/logout/', views.merchant_logout, name='portal_logout'),
    
    # Dashboard
    path('portal/', views.portal_dashboard, name='portal_dashboard'),
    
    # Transactions
    path('portal/deposit/', views.portal_deposit, name='portal_deposit'),
    path('portal/withdrawal/', views.portal_withdrawal, name='portal_withdrawal'),
    path('portal/transfer/', views.portal_transfer, name='portal_transfer'),
    path('portal/internal-transfer/', views.portal_internal_transfer, name='portal_internal_transfer'),
    path('portal/airtime/', views.portal_airtime, name='portal_airtime'),
    path('portal/data/', views.portal_data, name='portal_data'),
    path('portal/bills/', views.portal_bills, name='portal_bills'),
    
    # Customer Registration
    path('portal/customer/register/', views.portal_customer_register, name='portal_customer_register'),
    
    # Transaction History
    path('portal/transactions/', views.portal_transactions, name='portal_transactions'),
    path('portal/transactions/<str:trx_ref>/', views.portal_transaction_detail, name='portal_transaction_detail'),
    
    # Reports
    path('portal/reports/', views.portal_reports, name='portal_reports'),
    
    # Profile
    path('portal/profile/', views.portal_profile, name='portal_profile'),
    path('portal/change-pin/', views.portal_change_pin, name='portal_change_pin'),
    
    # ==============================================================================
    # API ENDPOINTS
    # ==============================================================================
    path('api/validate-customer/', views.api_validate_customer, name='api_validate_customer'),
    path('api/float-balance/', views.api_get_float_balance, name='api_get_float_balance'),
]
