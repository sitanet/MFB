from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RoleViewSet, UserViewSet, UserProfileViewSet,
    CompanyViewSet, BranchViewSet, AccountOfficerViewSet,
    CustomerViewSet, KYCDocumentViewSet,
    LoansViewSet, LoanHistViewSet,
    MemtransViewSet, DashboardView, PreLoginView, ActivateView, ChangePasswordView, TransferToFinanceFlexView, CustomerLookupView, PinStatusView, PinSetView, PinVerifyView
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
    # Router
    path('', include(router.urls)),
]