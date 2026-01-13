from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path("fixed-deposit/", views.fixed_dep, name="fixed_dep"),

    # Basic FD Operations
    path("fixed-deposit-list/", views.display_customers_with_fixed_deposit, name="display_customers_with_fixed_deposit"),
    path("display-customers-for-fixed-deposit-withdrawal/", views.display_customers_for_fixed_deposit_withdrawal, name="display_customers_for_fixed_deposit_withdrawal"),
    path("register-fixed-deposit/", views.register_fixed_deposit, name="register_fixed_deposit"),
    path("fixed-deposit/withdraw/<uuid:uuid>/", views.withdraw_fixed_deposit, name="withdraw_fixed_deposit"),
    path("running-fixed-deposits/", views.running_fixed_deposits, name="running_fixed_deposits"),
    
    # Reversal
    path("reversal/<uuid:uuid>/", views.reversal_for_fixed_deposit, name="reversal_for_fixed_deposit"),
    path("reverse-fixed-deposit-withdrawal/<uuid:uuid>/", views.reverse_fixed_deposit_withdrawal, name="reverse_fixed_deposit_withdrawal"),
    path("reversal-fixed-deposit-list/", views.reversal_fixed_deposit_list, name="reversal_fixed_deposit_list"),
    path("fixed-deposit-withdrawals/", views.list_fixed_deposit_withdrawals, name="list_fixed_deposit_withdrawals"),

    # NEW: Renewal
    path("fixed-deposit/renew/<uuid:uuid>/", views.renew_fixed_deposit, name="renew_fixed_deposit"),
    path("fixed-deposit/auto-renew/", views.auto_renew_matured_fds, name="auto_renew_matured_fds"),
    
    # NEW: Premature Withdrawal with Penalty
    path("fixed-deposit/premature-withdrawal/<uuid:uuid>/", views.premature_withdrawal, name="premature_withdrawal"),
    
    # NEW: Certificate Generation
    path("fixed-deposit/certificate/<uuid:uuid>/", views.generate_fd_certificate, name="generate_fd_certificate"),
    
    # NEW: Lien Marking
    path("fixed-deposit/lien/<uuid:uuid>/", views.mark_lien, name="mark_lien"),
    
    # NEW: FD Products Management
    path("fd-products/", views.fd_product_list, name="fd_product_list"),
    path("fd-products/create/", views.fd_product_create, name="fd_product_create"),
    path("fd-products/edit/<uuid:uuid>/", views.fd_product_edit, name="fd_product_edit"),
    
    # NEW: Interest Accrual
    path("fd-interest-accrual/", views.fd_interest_accrual_report, name="fd_interest_accrual_report"),
    path("fd-interest-accrual/run/", views.run_daily_interest_accrual, name="run_daily_interest_accrual"),
    
    # NEW: Maturity Report
    path("fd-maturity-report/", views.fd_maturity_report, name="fd_maturity_report"),
]

