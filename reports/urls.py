# chartofaccounts/urls.py
from django.urls import path
from . import views



urlpatterns = [
  
   
    path('generate_pdf/<int:id>/', views.generate_pdf, name='generate_pdf'),
    path('generate_doc/<int:id>/generate_doc/', views.generate_doc, name='generate_doc'),
    path('generate_excel/<int:id>/generate_excel/', views.generate_excel, name='generate_excel'),
    path('generate_csv/<int:id>/generate_csv/', views.generate_csv, name='generate_csv'),

    path('generate-statement/', views.generate_statement_view, name='generate_statement'),
    path('front_office_report/', views.front_office_report, name='front_office_report'),
    path('back_office_report/', views.back_office_report, name='back_office_report'),
    # path('generate_trial_balance/', views.generate_trial_balance, name='generate_trial_balance'),
    path('trial_balance/', views.trial_balance, name='trial_balance'),
    path('financial_report/', views.financial_report, name='financial_report'),
    path('savings_report/', views.savings_report, name='savings_report'),
    path('balance_sheet/', views.balance_sheet, name='balance_sheet'),
    path('profit_and_loss/', views.profit_and_loss, name='profit_and_loss'),
    path('loan_report/', views.loan_report, name='loan_report'),
    path('loan_hist/', views.loan_hist, name='loan_hist'),
    
    path('transaction-sequence-by-ses_date/', views.transaction_sequence_by_ses_date, name='transaction_sequence_by_ses_date'),
    path('transaction-sequence-by-trx_date/', views.transaction_sequence_by_trx_date, name='transaction_sequence_by_trx_date'),
    path('transaction-journal-listing-by-ses-date/', views.transaction_journal_listing_by_ses_date, name='transaction_journal_listing_by_ses_date'),
    path('transaction-journal-listing-by-trx-date/', views.transaction_journal_listing_by_trx_date, name='transaction_journal_listing_by_trx_date'),
    path('transaction-day-sheet-by-session-date/', views.transaction_day_sheet_by_session_date, name='transaction_day_sheet_by_session_date'),
    path('transaction-day-sheet-by-trx-date/', views.transaction_day_sheet_by_trx_date, name='transaction_day_sheet_by_trx_date'),
    path('general-trx-register-by-session-date/', views.general_trx_register_by_session_date, name='general_trx_register_by_session_date'),
    path('general-trx-register-by-trx-date/', views.general_trx_register_by_trx_date, name='general_trx_register_by_trx_date'),
    path('cashier-teller-cash-status-by-session-date/', views.cashier_teller_cash_status_by_session_date, name='cashier_teller_cash_status_by_session_date'),
    path('cashier-teller-cash-status-by-trx-date/', views.cashier_teller_cash_status_by_trx_date, name='cashier_teller_cash_status_by_trx_date'),

    path('account-statement/', views.account_statement, name='account_statement'),
    path('account_balance_report/', views.all_customers_account_balances, name='all_customers_account_balances'),

    path('savings-transaction-report/', views.savings_transaction_report, name='savings_transaction_report'),
    path('savings-accounts-listing/', views.savings_account_listing, name='savings_account_listing'),
    path('savings-account-status/', views.savings_account_status, name='savings_account_status'),
    path('savings-account-with-zero-balance/', views.savings_account_with_zero_balance, name='savings_account_with_zero_balance'),
    path('savings-overdrawn-account-status/', views.savings_overdrawn_account_status, name='savings_overdrawn_account_status'),
    path('savings_account_overdrawn/', views.savings_account_overdrawn, name='savings_account_overdrawn'),
    path('reports/savings-interest-paid/', views.savings_interest_paid, name='savings_interest_paid'),
    path('savings-account-credit-balance/', views.savings_account_credit_balance, name='savings_account_credit_balance'),

    path('loan/<int:loan_id>/ledger/', views.loan_ledger_card_view, name='loan_ledger_card'),
    path('loan_ledger_card/', views.loan_ledger_card_view, name='loan_ledger_card'),
    path('loan_repayment_schedule/', views.loan_repayment_schedule, name='loan_repayment_schedule'),
    path('loan_disbursement_report/', views.loan_disbursement_report, name='loan_disbursement_report'),
    path('loan_repayment_report/', views.loan_repayment_report, name='loan_repayment_report'),
    path('repayment-since-disbursement/', views.repayment_since_disbursement_report, name='repayment_since_disbursement_report'),

    path('repayment_since_disbursement_report/', views.repayment_since_disbursement_report, name='repayment_since_disbursement_report'),
    path('loan_outstanding_balance/', views.loan_outstanding_balance, name='loan_outstanding_balance'),
    path('expected_repayment/', views.expected_repayment, name='expected_repayment'),
    path('active_loans_by_officer/', views.active_loans_by_officer, name='active_loans_by_officer'),
    path('loan_till_sheet/', views.loan_till_sheet, name='loan_till_sheet'),
    path('loan_due_vs_repayment_report/', views.loan_due_vs_repayment_report, name='loan_due_vs_repayment_report'),
    

    path('portfolio_at_risk_report_view/', views.portfolio_at_risk_report_view, name='portfolio_at_risk_report_view'),
]
