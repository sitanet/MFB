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
    path("get-banks/", views.get_banks_view, name="get_banks"),
    path("other-bank-enquiry/", views.other_bank_enquiry_view, name="other_bank_enquiry"),
]
