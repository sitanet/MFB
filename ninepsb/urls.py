# ninepsb/urls.py
from django.urls import path
from . import views
# from .views import test_bank_fetch_view, test_account_validation_view

urlpatterns = [
    # path("test-bank-fetch/", test_bank_fetch_view, name="test_bank_fetch"),
    # path("test-account-validation/", test_account_validation_view, name="test_account_validation"),
    # path("test/virtual-account/<int:customer_id>/", views.test_virtual_account_create, name="test_virtual_account_create"),
    # path("fund-transfer/", views.fund_transfer_view, name="fund_transfer"),
    # path("account-enquiry/", views.account_enquiry_view, name="account_enquiry"),

    path("test-account/", views.test_virtual_account, name="test_virtual_account"),
]
