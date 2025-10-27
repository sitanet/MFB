from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from .views import (
    RoleViewSet, UserViewSet, UserProfileViewSet,
    CompanyViewSet, BranchViewSet, AccountOfficerViewSet,
    CustomerViewSet, KYCDocumentViewSet,
    LoansViewSet, LoanHistViewSet,
    MemtransViewSet, DashboardView, PreLoginView, ActivateView, ChangePasswordView, TransferToFinanceFlexView, CustomerLookupView, PinStatusView, PinSetView, PinVerifyView,     CardsPrimaryView,
    CardsPrimaryTransactionsView,
    
 CardsApplyView, CardsApproveView, CardsFundView, CardsRevealView, CardsTransactionsView,
    CardsPrimaryView, 
     CardsWithdrawView,
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
router.register(r'memtrans', MemtransViewSet, basename='memtrans')

urlpatterns = [
    # Browsable API auth (keep ONCE)
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),

    # App endpoints
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('transactions/', views.get_transactions, name='get_transactions'),
    path('auth/prelogin/', PreLoginView.as_view(), name='prelogin'),
    path('auth/activate/', ActivateView.as_view(), name='activate'),

    # JWT endpoints (become /api/v1/jwt/token/ and /api/v1/jwt/refresh/)
    path('jwt/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('jwt/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path("change-password/", ChangePasswordView.as_view(), name="change-password"),

    path('transfers/financeflex/', TransferToFinanceFlexView.as_view(), name='transfer_financeflex'),

    path('customers/lookup/', CustomerLookupView.as_view(), name='customer-lookup'),

    path('security/pin/status/', PinStatusView.as_view(), name="pin-status"),
    path('security/pin/set/', PinSetView.as_view(), name="pin-set"),
    path('security/pin/verify/', PinVerifyView.as_view(), name="pin-verify"),




        # Cards
    path("cards/primary/", CardsPrimaryView.as_view(), name="cards-primary"),
    path("cards/primary/transactions/", CardsPrimaryTransactionsView.as_view(), name="cards-primary-transactions"),
    # path("cards/primary/fund/", CardFundView.as_view(), name="cards-fund"),
    # path("cards/primary/withdraw/", CardWithdrawView.as_view(), name="cards-withdraw"),


    path("cards/apply/", CardsApplyView.as_view(), name="cards-apply"),
    path("cards/<uuid:card_id>/approve/", CardsApproveView.as_view(), name="cards-approve"),
    path("cards/primary/", CardsPrimaryView.as_view(), name="cards-primary"),
    path("cards/fund/", CardsFundView.as_view(), name="cards-fund"),
    path("cards/withdraw/", CardsWithdrawView.as_view(), name="cards-withdraw"),
    path("cards/reveal/", CardsRevealView.as_view(), name="cards-reveal"),
    path("cards/transactions/", CardsTransactionsView.as_view(), name="cards-transactions"),
    # Router
    path('', include(router.urls)),
]