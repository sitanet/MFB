from django.urls import path
from . import views
from .views import LoginView, ActivateView, ChangePasswordView, ForgotPasswordView, LogoutView, CustomerAccountsAPIView, AccountDetailsAPIView, TransactionHistoryAPIView, BalanceEnquiryAPIView, DepositPostingAPIView, DepositHistoryAPIView

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name="login"),
    path('auth/activate/', ActivateView.as_view(), name="activate"),
    path('auth/change-password/', ChangePasswordView.as_view(), name="change-password"),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name="forgot-password"),
    path('auth/logout/', LogoutView.as_view(), name="logout"),
    path('profile/', views.CustomerProfileView.as_view(), name='customer-profile'),
    path('profile/update/', views.CustomerUpdateView.as_view(), name='customer-update'),
    path('kyc/upload/', views.KYCDocumentUploadView.as_view(), name='kyc-upload'),
    path('customer-accounts/', CustomerAccountsAPIView.as_view(), name='customer-accounts'),
    path('account-details/', AccountDetailsAPIView.as_view(), name='account-details'),
    path('transaction-history/', TransactionHistoryAPIView.as_view(), name='transaction-history'),
    path('balance-enquiry/', BalanceEnquiryAPIView.as_view(), name='balance-enquiry'),
    path('deposit/', DepositPostingAPIView.as_view(), name='deposit-posting'),
    path('deposits/', DepositHistoryAPIView.as_view(), name='deposit-history'),
]
