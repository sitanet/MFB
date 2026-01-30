# ninepsb/urls.py
from django.urls import path
from . import views

app_name = 'ninepsb'

urlpatterns = [
    path("test-account/", views.test_virtual_account, name="test_virtual_account"),
    
    # 9PSB WAAS Operations
    path("wallet-enquiry/", views.wallet_enquiry_view, name="wallet_enquiry"),
    path("wallet-status/", views.wallet_status_view, name="wallet_status"),
    path("change-wallet-status/", views.change_wallet_status_view, name="change_wallet_status"),
    path("wallet-transactions/", views.wallet_transactions_view, name="wallet_transactions"),
    path("get-banks/", views.api_get_banks, name="get_banks"),  # JSON API for mobile app
    path("get-banks-admin/", views.get_banks_view, name="get_banks_admin"),  # HTML view for admin
    path("other-bank-enquiry/", views.other_bank_enquiry_view, name="other_bank_enquiry"),
    
    # 9PSB Webhook (for inflow notifications)
    path("webhook/", views.psb_webhook_handler, name="webhook"),
]
