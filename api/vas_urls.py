# api/vas_urls.py
from django.urls import path, include
from . import vas_views

urlpatterns = [
    # Network detection
    path('network/detect/', vas_views.detect_network, name='vas_detect_network'),
    
    # Airtime
    path('airtime/purchase/', vas_views.purchase_airtime, name='vas_purchase_airtime'),
    
    # Data
    path('data/plans/', vas_views.get_data_plans, name='vas_get_data_plans'),
    path('data/purchase/', vas_views.purchase_data, name='vas_purchase_data'),
    
    # Transactions
    path('transactions/', vas_views.get_transaction_history, name='vas_transaction_history'),
    path('transaction/status/<str:transaction_id>/', vas_views.get_transaction_status, name='vas_transaction_status'),
    
    # Bills Payment
    path('bills/categories/', vas_views.get_bills_categories, name='vas_bills_categories'),
    path('bills/billers/<int:category_id>/', vas_views.get_bills_billers, name='vas_bills_billers'),
    path('bills/validate/', vas_views.validate_bill_payment, name='vas_validate_bill'),
    path('bills/pay/', vas_views.pay_bill, name='vas_pay_bill'),
]