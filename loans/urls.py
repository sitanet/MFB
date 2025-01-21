# chartofaccounts/urls.py
from django.urls import path
from . import views


urlpatterns = [
  
    path('loans/', views.loans, name='loans'),
    # path('loans_application/', views.loans_application, name='loans_application'),
    path('choose_to_apply_loan/', views.choose_to_apply_loan, name='choose_to_apply_loan'),
    path('loan_application/<int:id>/', views.loan_application, name='loan_application'),
    path('choose_to_modify_loan/', views.choose_to_modify_loan, name='choose_to_modify_loan'),
    path('loan_modification/<int:id>/', views.loan_modification, name='loan_modification'),
    path('choose_loan_approval/', views.choose_loan_approval, name='choose_loan_approval'),
    path('loan_approval/<int:id>/', views.loan_approval, name='loan_approval'),
    path('reject_loan/<int:id>/', views.reject_loan, name='reject_loan'),
    path('choose_approved_loan/', views.choose_approved_loan, name='choose_approved_loan'),
    path('reverse_loan_approval/<int:id>/', views.reverse_loan_approval, name='reverse_loan_approval'),
    path('loan_schedule/<int:loan_id>/', views.loan_schedule_view, name='loan_schedule'),
    path('loan_schedule_demo/', views.loan_schedule_demo, name='loan_schedule_demo'),
    path('choose_to_disburse/', views.choose_to_disburse, name='choose_to_disburse'),
    # path('choose_to_disburse_reversal/', views.choose_to_disburse_reversal, name='choose_to_disburse_reversal'),
    path('display_loan_disbursements/', views.display_loan_disbursements, name='display_loan_disbursements'),
    # path('delete_transactions/<int:loan_id>/', views.delete_transactions, name='delete_transactions'),
    path('delete_loan_transactions/<str:trx_no>/<int:id>/', views.delete_loan_transactions, name='delete_loan_transactions'),
    path('loan_disbursement/<int:id>/', views.loan_disbursement, name='loan_disbursement'),
    path('loan_disbursement_reversal/<int:id>/', views.loan_disbursement_reversal, name='loan_disbursement_reversal'),
    path('choose_loan_repayment/', views.choose_loan_repayment, name='choose_loan_repayment'),  
    path('loan_repayment/<int:id>/', views.loan_repayment, name='loan_repayment'),
    path('loan_due/', views.loan_due, name='loan_due'),
    
    path('display_loans/', views.display_loans, name='display_loans'),
    path('choose_loan_written_off/', views.choose_loan_written_off, name='choose_loan_written_off'),  
    path('loan_written_off/<int:id>/', views.loan_written_off, name='loan_written_off'),
    path('loan_repayment_reversal/', views.loan_repayment_reversal, name='loan_repayment_reversal'),
    path('loan_history/<int:loan_id>/', views.loan_history, name='loan_history'),
    path('delete_loan_history/<int:loan_hist_id>/<int:loan_id>/', views.delete_loan_history, name='delete_loan_history'),
    path('due-loans/', views.due_loans, name='due_loans'),
    path('process-repayments/', views.process_repayments, name='process_repayments'),
    path('eop_loans/', views.eop_loans, name='eop_loans'),
    path('choose_to_apply_simple_loan/', views.choose_to_apply_simple_loan, name='choose_to_apply_simple_loan'),
    path('loan_application_and_approval/<int:id>/', views.loan_application_and_approval, name='loan_application_and_approval'),

    path('choose_simple_disburse/', views.choose_simple_disburse, name='choose_simple_disburse'),
    path('simple_loan_disbursement/<int:id>/', views.simple_loan_disbursement, name='simple_loan_disbursement'),
    
   
]
    
   
