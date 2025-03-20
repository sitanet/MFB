from django.urls import path
from . import views
# from .views import asset_list, asset_detail, add_asset, edit_asset, dispose_asset, transfer_asset

urlpatterns = [
    # path("get-fixed-deposit-details/", views.get_fixed_deposit_details, name="get_fixed_deposit_details"),
    path("register-fixed-deposit/", views.register_fixed_deposit, name="register_fixed_deposit"),
    path("fixed-deposit/withdraw/<int:deposit_id>/", views.withdraw_fixed_deposit, name="withdraw_fixed_deposit"),
    path("fixed-deposit/", views.fixed_dep, name="fixed_dep"),
    path("fixed-deposit-list/", views.display_customers_with_fixed_deposit, name="display_customers_with_fixed_deposit"),
    path("running-fixed-deposits/", views.running_fixed_deposits, name="running_fixed_deposits"),

    path("display-customers-for-fixed-deposit-withdrawal/", views.display_customers_for_fixed_deposit_withdrawal, name="display_customers_for_fixed_deposit_withdrawal"),
    path("reversal/<int:deposit_id>/", views.reversal_for_fixed_deposit, name="reversal_for_fixed_deposit"),
    path("reversal-fixed-deposit-list/", views.reversal_fixed_deposit_list, name="reversal_fixed_deposit_list"),
]

