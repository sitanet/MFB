# api/views.py

from decimal import Decimal
import uuid
import random

from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, DecimalField, Value
from django.db.models.functions import Coalesce

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

# Serializers
from .serializers import (
    RoleSerializer, UserSerializer, UserWriteSerializer, UserProfileSerializer,
    CompanySerializer, BranchSerializer, RegionSerializer, AccountOfficerSerializer,
    CustomerSerializer, KYCDocumentSerializer, LoansSerializer, LoanHistSerializer,
    MemtransSerializer,
    CardFundSerializer, CardWithdrawSerializer,
    ChangePasswordSerializer,
    TransferToFinanceFlexSerializer,
    VirtualCardApplySerializer, VirtualCardApproveSerializer, VirtualCardSerializer,
    PinSetSerializer, PinVerifySerializer,  # ✅ removed CardsFundView
)

# Helpers
from .helpers import (
    normalize_account,
    _user_customer,
    _owns_source_account,
    _balance,
    _gen_trx_no,
)

# Models
from accounts.models import Role, User as AccountsUser, UserProfile
from company.models import Company, Branch
from accounts_admin.models import Account_Officer, Region
from customers.models import Customer, KYCDocument, VirtualCard
from loans.models import Loans, LoanHist
from transactions.models import Memtrans
from api.models import Beneficiary


# ---------------------------------------------------------------------------
# Base model viewset and admin-ish viewsets
# ---------------------------------------------------------------------------

class BaseModelViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering_fields = '__all__'
    ordering = ['-id']


class RoleViewSet(BaseModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    search_fields = ['name']
    filterset_fields = ['name']


class UserViewSet(BaseModelViewSet):
    queryset = AccountsUser.objects.select_related('branch', 'customer').all()
    search_fields = ['email', 'username', 'first_name', 'last_name', 'phone_number', 'activation_code']
    filterset_fields = ['role', 'branch', 'is_active', 'is_admin', 'is_staff', 'is_superadmin', 'verified', 'customer']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserWriteSerializer
        return UserSerializer

    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        user = self.get_object()
        password = request.data.get('password')
        if not password:
            return Response({'detail': 'Password required'}, status=400)
        user.set_password(password)
        user.save(update_fields=['password'])
        return Response({'detail': 'Password updated'})


class UserProfileViewSet(BaseModelViewSet):
    queryset = UserProfile.objects.select_related('user').all()
    serializer_class = UserProfileSerializer
    search_fields = ['address', 'country', 'state', 'city', 'user__email', 'user__username']
    filterset_fields = ['user']


class CompanyViewSet(BaseModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    search_fields = ['company_name', 'contact_person', 'email', 'license_key']
    filterset_fields = ['session_status']


class BranchViewSet(BaseModelViewSet):
    queryset = Branch.objects.select_related('company').all()
    serializer_class = BranchSerializer
    search_fields = ['branch_code', 'branch_name', 'company_name', 'company__company_name', 'phone_number']
    filterset_fields = ['company', 'plan', 'head_office', 'phone_verified', 'session_status']


class RegionViewSet(BaseModelViewSet):
    queryset = Region.objects.select_related('branch').all()
    serializer_class = RegionSerializer
    search_fields = ['region_name', 'branch__branch_name']
    filterset_fields = ['branch', 'region_name']


class AccountOfficerViewSet(BaseModelViewSet):
    queryset = Account_Officer.objects.select_related('branch', 'region').all()
    serializer_class = AccountOfficerSerializer
    search_fields = ['user', 'branch__branch_name', 'region__region_name']
    filterset_fields = ['branch', 'region']


class CustomerViewSet(BaseModelViewSet):
    queryset = Customer.objects.select_related('branch', 'region', 'credit_officer').all()
    serializer_class = CustomerSerializer
    search_fields = [
        'first_name', 'middle_name', 'last_name', 'registration_number', 'email',
        'phone_no', 'mobile', 'wallet_account', 'bvn', 'nin', 'ac_no', 'gl_no'
    ]
    filterset_fields = ['branch', 'status', 'is_company', 'sms', 'email_alert', 'region', 'credit_officer']


class KYCDocumentViewSet(BaseModelViewSet):
    queryset = KYCDocument.objects.select_related('customer', 'verified_by').all()
    serializer_class = KYCDocumentSerializer
    search_fields = ['document_type', 'customer__first_name', 'customer__last_name']
    filterset_fields = ['customer', 'document_type', 'verified']


class LoansViewSet(BaseModelViewSet):
    queryset = Loans.objects.select_related('customer', 'branch', 'loan_officer').all()
    serializer_class = LoansSerializer
    search_fields = ['gl_no', 'ac_no', 'cust_gl_no', 'trx_type', 'reason']
    filterset_fields = ['branch', 'customer', 'approval_status', 'disb_status', 'payment_freq', 'interest_calculation_method']


class LoanHistViewSet(BaseModelViewSet):
    queryset = LoanHist.objects.select_related('branch').all()
    serializer_class = LoanHistSerializer
    search_fields = ['gl_no', 'ac_no', 'trx_no', 'trx_type', 'trx_naration']
    filterset_fields = ['branch', 'gl_no', 'ac_no', 'trx_date', 'period']


class MemtransViewSet(BaseModelViewSet):
    queryset = Memtrans.objects.select_related('branch', 'cust_branch', 'customer', 'user').all()
    serializer_class = MemtransSerializer
    search_fields = ['trx_no', 'gl_no', 'ac_no', 'description', 'trx_type', 'code']
    filterset_fields = ['branch', 'cust_branch', 'customer', 'ses_date', 'app_date', 'sys_date', 'error', 'type', 'account_type', 'user']


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return Response({"detail": "Customer profile not linked to user."}, status=404)

        gl_no = (customer.gl_no or '').strip()
        ac_no = (customer.ac_no or '').strip()
        if not gl_no or not ac_no:
            return Response({
                "customer": {
                    "last_name": (customer.last_name or ""),
                    "first_name": (getattr(customer, "first_name", "") or ""),
                    "full_name": f"{getattr(customer, 'first_name', '')} {getattr(customer, 'last_name', '')}".strip(),
                    "gl_no": gl_no,
                    "ac_no": ac_no,
                },
                "balance": 0.0,
                "accounts": [],
                "transactions": [],
            })

        per_accounts = (
            Memtrans.objects
            .filter(ac_no=ac_no)
            .values('gl_no', 'ac_no')
            .annotate(
                balance=Coalesce(
                    Sum('amount'),
                    Value(0, output_field=DecimalField(max_digits=18, decimal_places=2))
                )
            )
            .order_by('gl_no')
        )

        primary_balance = Decimal('0')
        for r in per_accounts:
            if (r['gl_no'] or '').strip() == gl_no:
                primary_balance = r['balance'] or Decimal('0')
                break

        recent = (
            Memtrans.objects
            .filter(gl_no=gl_no, ac_no=ac_no)
            .order_by('-sys_date')[:20]
        )
        data = MemtransSerializer(recent, many=True).data

        return Response({
            "customer": {
                "last_name": (customer.last_name or ""),
                "first_name": (getattr(customer, "first_name", "") or ""),
                "full_name": f"{getattr(customer, 'first_name', '')} {getattr(customer, 'last_name', '')}".strip(),
                "gl_no": gl_no,
                "ac_no": ac_no,
            },
            "primary_gl_no": gl_no,
            "primary_ac_no": ac_no,
            "balance": float(primary_balance),
            "accounts": [
                {
                    "gl_no": r["gl_no"],
                    "ac_no": r["ac_no"],
                    "balance": float(r["balance"] or 0),
                }
                for r in per_accounts
            ],
            "transactions": data,
        })








from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator
from transactions.models import Memtrans  # Import from transactions app
from .serializers import MemtransSerializer  # Import from current api app
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transactions(request):
    """
    GET /api/v1/transactions/?page=1&limit=5
    Returns paginated user transactions from Memtrans model
    """
    try:
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 5))
        
        # Validate parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 50:
            limit = 5
        
        # Get user's transactions - filter by customer relationship
        user_transactions = Memtrans.objects.filter(
            customer=request.user.customer,  # Filter by customer relationship
            # Alternative: user=request.user,  # Or filter by user directly if needed
        ).order_by('-sys_date')  # Order by system date, newest first
        
        # Apply pagination
        paginator = Paginator(user_transactions, limit)
        
        try:
            transactions_page = paginator.page(page)
        except:
            # If page is out of range, return empty results
            return Response({
                'data': [],
                'page': page,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': False,
            })
        
        # Serialize the data
        serializer = MemtransSerializer(transactions_page, many=True)
        
        # Return response in the format expected by mobile app
        return Response({
            'data': serializer.data,
            'page': page,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': transactions_page.has_next(),
            'has_previous': transactions_page.has_previous(),
        })
        
    except ValueError as e:
        logger.error(f"Invalid parameter in transactions API: {e}")
        return Response(
            {'error': 'Invalid page or limit parameter'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except AttributeError as e:
        logger.error(f"User has no customer relationship: {e}")
        return Response(
            {'error': 'User account not properly configured'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error in transactions API: {e}")
        return Response(
            {'error': 'Failed to fetch transactions'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ---------------------------------------------------------------------------
# Pre-login and activation
# ---------------------------------------------------------------------------

UserModel = get_user_model()

def _find_user_by_username_or_email(value: str):
    try:
        return UserModel.objects.get(username=value)
    except UserModel.DoesNotExist:
        try:
            return UserModel.objects.get(email__iexact=value)
        except UserModel.DoesNotExist:
            return None


class PreLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        if not username or not password:
            return Response({"detail": "username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = _find_user_by_username_or_email(username)
        if not user or not user.check_password(password):
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        if getattr(user, "verified", False):
            return Response({"can_login": True}, status=status.HTTP_200_OK)

        return Response({"activation_required": True, "username": user.username}, status=status.HTTP_202_ACCEPTED)


class ActivateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        code = (request.data.get('activation_code') or '').strip()
        if not username or not password or not code:
            return Response({"detail": "username, password and activation_code are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = _find_user_by_username_or_email(username)
        if not user or not user.check_password(password):
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.activation_code or user.activation_code != code:
            return Response({"detail": "Invalid or missing activation code"}, status=status.HTTP_400_BAD_REQUEST)

        user.verified = True
        user.save(update_fields=["verified"])

        return Response({"activated": True}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_password = serializer.validated_data["new_password"]
        user.set_password(new_password)
        user.save()

        # Optional: revoke tokens if blacklist is installed
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            for token in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=token)
        except Exception:
            pass

        return Response({"detail": "Password changed successfully. Please log in again."}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Transfer to FinanceFlex (signed amounts; double-entry)
# ---------------------------------------------------------------------------

class TransferToFinanceFlexView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        ser = TransferToFinanceFlexSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        user = request.user
        src_cust = _user_customer(request)
        if not src_cust:
            return Response({"detail": "Customer profile not found for user."}, status=404)

        from_gl = data["from_gl_no"]
        from_ac = data["from_ac_no"]
        to_gl = data["to_gl_no"]
        to_ac = data["to_ac_no"]
        amount = data["amount"]
        narr = data.get("narration") or "FinanceFlex transfer"

        norm_from_gl, norm_from_ac = normalize_account(from_gl, from_ac)
        norm_to_gl, norm_to_ac = normalize_account(to_gl, to_ac)

        if not _owns_source_account(src_cust, norm_from_gl, norm_from_ac):
            return Response({"detail": "Source account not found for this user."}, status=404)

        dest_cust = Customer.objects.filter(gl_no=norm_to_gl, ac_no=norm_to_ac).first()
        if not dest_cust:
            return Response({"detail": "Destination account not found."}, status=404)

        cur_bal = _balance(norm_from_gl, norm_from_ac)
        if cur_bal < amount:
            return Response({"detail": f"Insufficient funds. Available: {cur_bal}, Requested: {amount}"}, status=400)

        now = timezone.now()
        today = timezone.localdate()
        trx_no = _gen_trx_no()

        # CR destination (+)
        Memtrans.objects.create(
            branch=dest_cust.branch,
            cust_branch=dest_cust.branch,
            customer=dest_cust,
            gl_no=norm_to_gl,
            ac_no=norm_to_ac,
            trx_no=trx_no,
            ses_date=today,
            app_date=today,
            sys_date=now,
            amount=amount,
            description=narr,
            error="A",
            type="T",
            account_type="C",
            code="",
            user=user,
            trx_type="TRANSFER",
        )
        # DR source (-)
        Memtrans.objects.create(
            branch=src_cust.branch,
            cust_branch=src_cust.branch,
            customer=src_cust,
            gl_no=norm_from_gl,
            ac_no=norm_from_ac,
            trx_no=trx_no,
            ses_date=today,
            app_date=today,
            sys_date=now,
            amount=-amount,
            description=narr,
            error="A",
            type="T",
            account_type="C",
            code="",
            user=user,
            trx_type="TRANSFER",
        )

        new_src_bal = _balance(norm_from_gl, norm_from_ac)
        new_dst_bal = _balance(norm_to_gl, norm_to_ac)

        return Response(
            {
                "status": True,
                "reference": trx_no,
                "amount": str(amount),
                "narration": narr,
                "timestamp": now.isoformat(),
                "from": {
                    "gl_no": norm_from_gl,
                    "ac_no": norm_from_ac,
                    "customer_id": src_cust.id,
                    "balance": str(new_src_bal),
                },
                "to": {
                    "gl_no": norm_to_gl,
                    "ac_no": norm_to_ac,
                    "customer_id": dest_cust.id,
                    "balance": str(new_dst_bal),
                },
            },
            status=201,
        )


# ---------------------------------------------------------------------------
# Customer lookup (by 10-digit or gl/ac)
# ---------------------------------------------------------------------------

class CustomerLookupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        account = request.query_params.get('account')
        gl_no = request.query_params.get('gl_no')
        ac_no = request.query_params.get('ac_no')

        if account:
            digits = ''.join(ch for ch in str(account) if ch.isdigit())
            if len(digits) != 10:
                return Response({'detail': 'account must be 10 digits'}, status=status.HTTP_400_BAD_REQUEST)
            gl_no, ac_no = digits[:5], digits[5:]
        if not gl_no or not ac_no:
            return Response({'detail': 'gl_no and ac_no are required'}, status=status.HTTP_400_BAD_REQUEST)

        cust = Customer.objects.filter(gl_no=str(gl_no), ac_no=str(ac_no)).first()
        if not cust:
            return Response({'exists': False}, status=status.HTTP_404_NOT_FOUND)

        first_name = getattr(cust, 'first_name', None) or getattr(getattr(cust, 'user', None), 'first_name', '') or ''
        last_name = getattr(cust, 'last_name', None) or getattr(getattr(cust, 'user', None), 'last_name', '') or ''

        return Response({
            'exists': True,
            'gl_no': str(gl_no),
            'ac_no': str(ac_no),
            'account': f'{str(gl_no)}{str(ac_no)}',
            'first_name': first_name,
            'last_name': last_name,
            'full_name': f'{first_name} {last_name}'.strip(),
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Beneficiaries (serializer colocated here per your snippet)
# ---------------------------------------------------------------------------

from rest_framework import serializers

class BeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Beneficiary
        fields = [
            'id',
            'name',
            'bank_name',
            'account_number',
            'phone_number',
            'nickname',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        user = self.context['request'].user
        return Beneficiary.objects.create(user=user, **validated_data)


# ---------------------------------------------------------------------------
# PIN endpoints (server-managed)
# ---------------------------------------------------------------------------

class PinStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        has_pin = bool(getattr(user, "transaction_pin", None))
        return Response({"has_pin": has_pin}, status=status.HTTP_200_OK)


class PinSetView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = PinSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_pin = serializer.validated_data.get("current_pin")
        new_pin = serializer.validated_data["pin"]

        if user.transaction_pin:
            if not current_pin or not user.check_transaction_pin(current_pin):
                return Response({"detail": "Current PIN is incorrect."}, status=status.HTTP_403_FORBIDDEN)

        user.set_transaction_pin(new_pin)
        user.save(update_fields=["transaction_pin"])
        return Response({"detail": "Transaction PIN set successfully."}, status=status.HTTP_200_OK)


class PinVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = PinVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pin = serializer.validated_data["pin"]
        if not user.transaction_pin or not user.check_transaction_pin(pin):
            return Response({"detail": "Invalid PIN."}, status=status.HTTP_403_FORBIDDEN)

        return Response({"ok": True}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Virtual Cards
# ---------------------------------------------------------------------------

CARD_GL = "20501"
CARD_AC_LEN = 5

def _generate_unique_card_ac_no():
    for _ in range(500):
        n = str(random.randint(0, 10**CARD_AC_LEN - 1)).zfill(CARD_AC_LEN)
        if not VirtualCard.objects.filter(gl_no=CARD_GL, ac_no=n).exists():
            return n
    raise RuntimeError("Unable to generate unique card AC")

def _sync_customer_gl_ac(customer, gl_no: str, ac_no: str):
    touched = []
    if getattr(customer, "gl_no", None) != gl_no:
        customer.gl_no = gl_no
        touched.append("gl_no")
    if getattr(customer, "ac_no", None) != ac_no:
        customer.ac_no = ac_no
        touched.append("ac_no")
    if touched:
        customer.save(update_fields=touched)


class CardsApplyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        cust = _user_customer(request)
        if not cust:
            return Response({"detail": "No customer profile linked to user."}, status=404)

        existing = VirtualCard.objects.filter(customer=cust, status__in=["pending", "active"]).first()
        if existing:
            return Response({"detail": f"A card already exists with status '{existing.status}'."}, status=400)

        ser = VirtualCardApplySerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        now = timezone.now()
        exp_dt = now.replace(year=now.year + 3)

        card = VirtualCard.objects.create(
            customer=cust,
            gl_no=CARD_GL,
            ac_no=_generate_unique_card_ac_no(),
            expiry_month=exp_dt.month,
            expiry_year=exp_dt.year,
            status="pending",
        )

        # Mirror as requested
        _sync_customer_gl_ac(cust, card.gl_no, card.ac_no)

        return Response({"status": "pending", "card": VirtualCardSerializer(card).data}, status=201)


class CardsApproveView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @transaction.atomic
    def post(self, request, card_id: uuid.UUID):
        try:
            card = VirtualCard.objects.select_related("customer").get(id=card_id)
        except VirtualCard.DoesNotExist:
            return Response({"detail": "Card not found"}, status=404)

        if card.status == "active":
            return Response({"detail": "Card already active"}, status=400)

        ser = VirtualCardApproveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        approve = ser.validated_data.get("approve", True)

        if not approve:
            card.status = "inactive"
            card.save(update_fields=["status"])
            return Response({"status": "inactive", "card": VirtualCardSerializer(card).data})

        card.status = "active"
        card.activated_at = timezone.now()
        card.save(update_fields=["status", "activated_at"])

        _sync_customer_gl_ac(card.customer, card.gl_no, card.ac_no)

        return Response({"status": "active", "card": VirtualCardSerializer(card).data})


class CardsPrimaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cust = _user_customer(request)
        if not cust:
            return Response({"detail": "No customer profile"}, status=404)

        active = (
            VirtualCard.objects
            .filter(customer=cust, status="active")
            .order_by("-activated_at", "-created_at")
            .first()
        )
        if not active:
            return Response({"detail": "No active card"}, status=404)

        card_bal = float(_balance(active.gl_no or "", active.ac_no or ""))

        holder = request.user.customer.get_full_name()
        last4 = (active.card_number or "")[-4:]
        expiry = f"{str(active.expiry_month).zfill(2)}/{str(active.expiry_year)[-2:]}"
        pan_mask = f"**** **** **** {last4 if last4 else '••••'}"

        # Source (mirrored)
        src_gl, src_ac = normalize_account(getattr(cust, "gl_no", "") or "", getattr(cust, "ac_no", "") or "")
        source_balance = float(_balance(src_gl, src_ac))

        return Response({
            "pan": pan_mask,
            "last4": last4,
            "holder": holder,
            "expiry": expiry,
            "brand": "FINANCEFLEX",
            "status": "active",
            "balance": card_bal,
            "card_gl_no": active.gl_no or "",
            "card_ac_no": active.ac_no or "",
            "account": {"gl_no": src_gl, "ac_no": src_ac},
            "source_balance": source_balance,
        })


class CardsFundView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        cust = _user_customer(request)
        if not cust:
            return Response({"detail": "No customer profile"}, status=404)

        active = VirtualCard.objects.filter(customer=cust, status="active").first()
        if not active:
            return Response({"detail": "No active card"}, status=404)

        ser = CardFundSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        amount: Decimal = ser.validated_data["amount"]

        src_gl, src_ac = normalize_account(getattr(cust, "gl_no", ""), getattr(cust, "ac_no", ""))
        if not src_gl or not src_ac:
            return Response({"detail": "Primary account not set"}, status=400)

        card_gl, card_ac = normalize_account(active.gl_no or "", active.ac_no or "")

        if _balance(src_gl, src_ac) < amount:
            return Response({"detail": "Insufficient funds"}, status=400)

        trx_no = _gen_trx_no()
        now = timezone.now()
        ses = now.date()
        narration = f"Card funding {card_gl}{card_ac}"

        # DR primary (-), CR card (+)
        Memtrans.objects.create(
            trx_no=trx_no,
            gl_no=src_gl,
            ac_no=src_ac,
            amount=-amount,
            description=narration,
            ses_date=ses,
            sys_date=now,
            user=request.user,
            customer=cust,
            trx_type="CARD_FUND",
        )
        Memtrans.objects.create(
            trx_no=trx_no,
            gl_no=card_gl,
            ac_no=card_ac,
            amount=amount,
            description=narration,
            ses_date=ses,
            sys_date=now,
            user=request.user,
            customer=cust,
            trx_type="CARD_FUND",
        )

        return Response({
            "status": "success",
            "trx_no": trx_no,
            "card_balance": float(_balance(card_gl, card_ac)),
            "source_balance": float(_balance(src_gl, src_ac)),
        }, status=201)


class CardsWithdrawView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        cust = _user_customer(request)
        if not cust:
            return Response({"detail": "No customer profile"}, status=404)

        active = VirtualCard.objects.filter(customer=cust, status="active").first()
        if not active:
            return Response({"detail": "No active card"}, status=404)

        ser = CardWithdrawSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        amount: Decimal = ser.validated_data["amount"]

        card_gl, card_ac = normalize_account(active.gl_no or "", active.ac_no or "")
        dst_gl, dst_ac = normalize_account(getattr(cust, "gl_no", ""), getattr(cust, "ac_no", ""))
        if not dst_gl or not dst_ac:
            return Response({"detail": "Primary account not set"}, status=400)

        if _balance(card_gl, card_ac) < amount:
            return Response({"detail": "Insufficient card balance"}, status=400)

        trx_no = _gen_trx_no()
        now = timezone.now()
        ses = now.date()
        narration = f"Card withdrawal to {dst_gl}{dst_ac}"

        # DR card (-), CR primary (+)
        Memtrans.objects.create(
            trx_no=trx_no,
            gl_no=card_gl,
            ac_no=card_ac,
            amount=-amount,
            description=narration,
            ses_date=ses,
            sys_date=now,
            user=request.user,
            customer=cust,
            trx_type="CARD_WITHDRAW",
        )
        Memtrans.objects.create(
            trx_no=trx_no,
            gl_no=dst_gl,
            ac_no=dst_ac,
            amount=amount,
            description=narration,
            ses_date=ses,
            sys_date=now,
            user=request.user,
            customer=cust,
            trx_type="CARD_WITHDRAW",
        )

        return Response({
            "status": "success",
            "trx_no": trx_no,
            "card_balance": float(_balance(card_gl, card_ac)),
            "source_balance": float(_balance(dst_gl, dst_ac)),
        }, status=201)


class CardsRevealView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cust = _user_customer(request)
        if not cust:
            return Response({"detail": "No customer profile"}, status=404)
        active = VirtualCard.objects.filter(customer=cust, status="active").first()
        if not active:
            return Response({"detail": "No active card"}, status=404)
        return Response({
            "card_number": active.card_number or "",
            "cvv": active.cvv or "",
            "expiry_month": active.expiry_month,
            "expiry_year": active.expiry_year,
        })


class CardsTransactionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cust = _user_customer(request)
        if not cust:
            return Response({"results": []}, status=200)
        active = VirtualCard.objects.filter(customer=cust, status="active").first()
        if not active:
            return Response({"results": []}, status=200)

        try:
            limit = int(request.query_params.get("limit", "50"))
        except ValueError:
            limit = 50

        qs = (
            Memtrans.objects
            .filter(gl_no=active.gl_no, ac_no=active.ac_no)
            .order_by("-sys_date")[:max(1, min(limit, 200))]
        )

        data = [{
            "id": getattr(m, "id", None),
            "trx_no": m.trx_no or "",
            "sys_date": (m.sys_date or timezone.now()).isoformat(),
            "amount": float(m.amount),  # signed
            "description": m.description or "",
        } for m in qs]

        return Response({"results": data}, status=200)


# Backward-compat: a plain-list variant
class CardsPrimaryTransactionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get("limit", 50))
        cust = _user_customer(request)
        if not cust:
            return Response([], status=200)
        active = VirtualCard.objects.filter(customer=cust, status="active").first()
        if not active:
            return Response([], status=200)

        qs = (
            Memtrans.objects
            .filter(gl_no=active.gl_no, ac_no=active.ac_no)
            .order_by("-sys_date")[:max(1, min(limit, 200))]
        )

        items = []
        for m in qs:
            created = getattr(m, "sys_date", None) or timezone.now()
            items.append(
                {
                    "id": str(getattr(m, "id", "")),
                    "date": created.isoformat(),
                    "amount": float(m.amount),
                    "merchant": getattr(m, "description", "") or "Card transaction",
                    "status": "SUCCESS",
                    "description": getattr(m, "description", "") or "",
                }
            )
        return Response(items)







