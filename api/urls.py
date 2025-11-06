from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from .views import (
    RoleViewSet, UserViewSet, UserProfileViewSet,
    CompanyViewSet, BranchViewSet, AccountOfficerViewSet,
    CustomerViewSet, KYCDocumentViewSet,
    LoansViewSet, LoanHistViewSet,
    MemtransViewSet, DashboardView, PreLoginView, ActivateView, ChangePasswordView, 
    TransferToFinanceFlexView, CustomerLookupView, PinStatusView, PinSetView, PinVerifyView,
    CardsPrimaryView, CardsPrimaryTransactionsView,
    CardsApplyView, CardsApproveView, CardsFundView, CardsRevealView, 
    CardsTransactionsView, CardsWithdrawView, 
    # FIXED: Import the class-based transaction views
    TransactionsView, LoanTransactionsView, RegularTransactionsView,         VerifyAccountAPIView,
    SendOTPAPIView,
    VerifyOTPAPIView,
    RegisterUserAPIView,
    SetupPINAPIView,
    ResendOTPAPIView,
    DebugOTPStatusAPIView,
    get_bank_list,
    verify_account,
    # initiate_transfer,
    # check_transfer_status,
    # ninepsb_health_check
)

router = DefaultRouter()
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'users', UserViewSet, basename='user')
router.register(r'user-profiles', UserProfileViewSet, basename='userprofile')
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'account-officers', AccountOfficerViewSet, basename='accountofficer')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'kyc-documents', KYCDocumentViewSet, basename='kycdocument')
router.register(r'loans', LoansViewSet, basename='loan')
router.register(r'loan-hist', LoanHistViewSet, basename='loanhist')

urlpatterns = [
    # Browsable API auth
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),

    # App endpoints
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # FIXED: Transaction endpoints - Remove /api/v1/ prefix since it's already included at higher level
    path('transactions/', TransactionsView.as_view(), name='get_transactions'),
    path('transactions/loan/', LoanTransactionsView.as_view(), name='get_loan_transactions'),
    path('transactions/regular/', RegularTransactionsView.as_view(), name='get_regular_transactions'),
    
    path('auth/prelogin/', PreLoginView.as_view(), name='prelogin'),
    path('auth/activate/', ActivateView.as_view(), name='activate'),

    # JWT endpoints
    path('jwt/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('jwt/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path("change-password/", ChangePasswordView.as_view(), name="change-password"),

    path('transfers/financeflex/', TransferToFinanceFlexView.as_view(), name='transfer_financeflex'),

    path('customers/lookup/', CustomerLookupView.as_view(), name='customer-lookup'),

    path('security/pin/status/', PinStatusView.as_view(), name="pin-status"),
    path('security/pin/set/', PinSetView.as_view(), name="pin-set"),
    path('security/pin/verify/', PinVerifyView.as_view(), name="pin-verify"),

    # Cards endpoints
    path("cards/primary/", CardsPrimaryView.as_view(), name="cards-primary"),
    path("cards/primary/transactions/", CardsPrimaryTransactionsView.as_view(), name="cards-primary-transactions"),
    path("cards/apply/", CardsApplyView.as_view(), name="cards-apply"),
    path("cards/<uuid:card_id>/approve/", CardsApproveView.as_view(), name="cards-approve"),
    path("cards/fund/", CardsFundView.as_view(), name="cards-fund"),
    path("cards/withdraw/", CardsWithdrawView.as_view(), name="cards-withdraw"),
    path("cards/reveal/", CardsRevealView.as_view(), name="cards-reveal"),
    path("cards/transactions/", CardsTransactionsView.as_view(), name="cards-transactions"),






    path('auth/verify-account/', VerifyAccountAPIView.as_view(), name='verify-account'),
    path('auth/send-otp/', SendOTPAPIView.as_view(), name='send-otp'),
    path('auth/verify-otp/', VerifyOTPAPIView.as_view(), name='verify-otp'),
    path('auth/resend-otp/', ResendOTPAPIView.as_view(), name='resend-otp'),  # Add this
    path('auth/register/', RegisterUserAPIView.as_view(), name='register'),
    path('auth/setup-pin/', SetupPINAPIView.as_view(), name='setup-pin'),


        # Debug endpoint (only works in DEBUG mode)
    path('auth/debug-otp-status/', DebugOTPStatusAPIView.as_view(), name='debug-otp-status'),

    


    # Dashboard
    path('dashboard/', views.dashboard_api_view, name='dashboard'),
    
    # Wallet endpoints
    path('wallet/details/', views.WalletDetailsAPIView.as_view(), name='wallet-details'),
    path('wallet/details-by-account/', views.wallet_details_by_account_api_view, name='wallet-details-by-account'),





    path('ninepsb/banks/', views.get_bank_list, name='ninepsb-banks'),
    path('ninepsb/verify-account/', views.verify_account, name='ninepsb-verify-account'),
    path('ninepsb/transfer/', views.initiate_transfer, name='ninepsb-transfer'),
    path('ninepsb/health/', views.ninepsb_health_check, name='ninepsb-health'),

    # Router (include at the end)
    path('', include(router.urls)),




  
]