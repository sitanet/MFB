from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .serializers import (
    RoleSerializer, UserSerializer, UserWriteSerializer, UserProfileSerializer,
    CompanySerializer, BranchSerializer, RegionSerializer, AccountOfficerSerializer,
    CustomerSerializer, KYCDocumentSerializer, LoansSerializer, LoanHistSerializer,
    MemtransSerializer
)
from accounts.models import Role, User, UserProfile
from company.models import Company, Branch
from customers.models import Customer, KYCDocument
from loans.models import Loans, LoanHist
from transactions.models import Memtrans
from accounts_admin.models import Account_Officer, Region

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
    queryset = User.objects.select_related('branch','customer').all()
    search_fields = ['email','username','first_name','last_name','phone_number','activation_code']
    filterset_fields = ['role','branch','is_active','is_admin','is_staff','is_superadmin','verified','customer']

    def get_serializer_class(self):
        if self.action in ['create','update','partial_update']:
            return UserWriteSerializer
        return UserSerializer

    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        user = self.get_object()
        password = request.data.get('password')
        if not password:
            return Response({'detail':'Password required'}, status=400)
        user.set_password(password)
        user.save(update_fields=['password'])
        return Response({'detail':'Password updated'})

class UserProfileViewSet(BaseModelViewSet):
    queryset = UserProfile.objects.select_related('user').all()
    serializer_class = UserProfileSerializer
    search_fields = ['address','country','state','city','user__email','user__username']
    filterset_fields = ['user']


# api/views.py
from decimal import Decimal
from django.db.models import Sum, DecimalField, Value
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from transactions.models import Memtrans
from .serializers import MemtransSerializer

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

        # Per-account balances for same ac_no across different gl_no
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

        # Primary account balance (this user’s gl_no + ac_no)
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
            "balance": float(primary_balance),  # backward compatibility
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

        
class CompanyViewSet(BaseModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    search_fields = ['company_name','contact_person','email','license_key']
    filterset_fields = ['session_status']

class BranchViewSet(BaseModelViewSet):
    queryset = Branch.objects.select_related('company').all()
    serializer_class = BranchSerializer
    search_fields = ['branch_code','branch_name','company_name','company__company_name','phone_number']
    filterset_fields = ['company','plan','head_office','phone_verified','session_status']

class RegionViewSet(BaseModelViewSet):
    queryset = Region.objects.select_related('branch').all()
    serializer_class = RegionSerializer
    search_fields = ['region_name','branch__branch_name']
    filterset_fields = ['branch','region_name']

class AccountOfficerViewSet(BaseModelViewSet):
    queryset = Account_Officer.objects.select_related('branch','region').all()
    serializer_class = AccountOfficerSerializer
    search_fields = ['user','branch__branch_name','region__region_name']
    filterset_fields = ['branch','region']

class CustomerViewSet(BaseModelViewSet):
    queryset = Customer.objects.select_related('branch','region','credit_officer').all()
    serializer_class = CustomerSerializer
    search_fields = ['first_name','middle_name','last_name','registration_number','email','phone_no','mobile','wallet_account','bvn','nin','ac_no','gl_no']
    filterset_fields = ['branch','status','is_company','sms','email_alert','region','credit_officer']

class KYCDocumentViewSet(BaseModelViewSet):
    queryset = KYCDocument.objects.select_related('customer','verified_by').all()
    serializer_class = KYCDocumentSerializer
    search_fields = ['document_type','customer__first_name','customer__last_name']
    filterset_fields = ['customer','document_type','verified']

class LoansViewSet(BaseModelViewSet):
    queryset = Loans.objects.select_related('customer','branch','loan_officer').all()
    serializer_class = LoansSerializer
    search_fields = ['gl_no','ac_no','cust_gl_no','trx_type','reason']
    filterset_fields = ['branch','customer','approval_status','disb_status','payment_freq','interest_calculation_method']

class LoanHistViewSet(BaseModelViewSet):
    queryset = LoanHist.objects.select_related('branch').all()
    serializer_class = LoanHistSerializer
    search_fields = ['gl_no','ac_no','trx_no','trx_type','trx_naration']
    filterset_fields = ['branch','gl_no','ac_no','trx_date','period']

class MemtransViewSet(BaseModelViewSet):
    queryset = Memtrans.objects.select_related('branch','cust_branch','customer','user').all()
    serializer_class = MemtransSerializer
    search_fields = ['trx_no','gl_no','ac_no','description','trx_type','code']
    filterset_fields = ['branch','cust_branch','customer','ses_date','app_date','sys_date','error','type','account_type','user']




from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

User = get_user_model()

def _find_user_by_username_or_email(value: str):
    try:
        return User.objects.get(username=value)
    except User.DoesNotExist:
        try:
            return User.objects.get(email__iexact=value)
        except User.DoesNotExist:
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
        # optional hardening:
        # user.is_active = True
        # user.activation_code = None
        user.save(update_fields=["verified"])

        return Response({"activated": True}, status=status.HTTP_200_OK)






from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .serializers import ChangePasswordSerializer  # adjust import if needed

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_password = serializer.validated_data["new_password"]
        user.set_password(new_password)
        user.save()

        # Optional: If you use SimpleJWT blacklist, revoke existing refresh tokens
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            for token in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=token)
        except Exception:
            # Blacklist not installed/enabled or another non-fatal issue — ignore.
            pass

        return Response({"detail": "Password changed successfully. Please log in again."}, status=status.HTTP_200_OK)





from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TransferToFinanceFlexSerializer
from customers.models import Customer
from transactions.models import Memtrans

def _balance(gl_no: str, ac_no: str) -> Decimal:
    qs = Memtrans.objects.filter(gl_no=gl_no, ac_no=ac_no)
    cr = qs.filter(trx_type='CR').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    dr = qs.filter(trx_type='DR').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    return cr - dr

def _user_customer(request):
    try:
        return request.user.customer
    except Exception:
        return None

def _owns_source_account(customer: Customer, gl_no: str, ac_no: str) -> bool:
    if not customer:
        return False
    if (customer.gl_no == gl_no and customer.ac_no == ac_no):
        return True
    return Memtrans.objects.filter(customer=customer, gl_no=gl_no, ac_no=ac_no).exists()

def _find_destination_customer(to_ac_no: str):
    dest = Customer.objects.filter(wallet_account=to_ac_no).first()
    if dest:
        return dest
    return Customer.objects.filter(ac_no=to_ac_no).first()

def _gen_trx_no(user_id: int) -> str:
    now = timezone.now()
    return f"FF{now.strftime('%y%m%d%H%M%S')}{user_id % 10000:04d}"

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TransferToFinanceFlexSerializer
from .helpers import (
    _user_customer,
    _owns_source_account,
    _balance,
    _gen_trx_no,
)
from customers.models import Customer
from transactions.models import Memtrans


class TransferToFinanceFlexView(APIView):
    permission_classes = [IsAuthenticated]

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

        # Normalize to 5-digit internally
        norm_from_gl = from_gl.strip().zfill(5)[-5:]
        norm_from_ac = from_ac.strip().zfill(5)[-5:]
        norm_to_gl = to_gl.strip().zfill(5)[-5:]
        norm_to_ac = to_ac.strip().zfill(5)[-5:]

        if not _owns_source_account(src_cust, norm_from_gl, norm_from_ac):
            return Response({"detail": "Source account not found for this user."}, status=404)

        dest_cust = Customer.objects.filter(gl_no=norm_to_gl, ac_no=norm_to_ac).first()
        if not dest_cust:
            return Response({"detail": "Destination account not found."}, status=404)

        # Daily limit check
        if getattr(src_cust, "transfer_limit", None) and src_cust.transfer_limit > 0:
            today = timezone.localdate()
            used_today = (
                Memtrans.objects.filter(
                    customer=src_cust,
                    ses_date=today,
                    trx_type="DR"
                ).aggregate(s=Sum("amount"))["s"]
                or Decimal("0")
            )
            if used_today + amount > src_cust.transfer_limit:
                return Response(
                    {
                        "detail": (
                            f"Daily transfer limit exceeded. "
                            f"Used {used_today}, limit {src_cust.transfer_limit}."
                        )
                    },
                    status=400,
                )

        # Balance check
        cur_bal = _balance(norm_from_gl, norm_from_ac)
        if cur_bal < amount:
            return Response({
                "detail": f"Insufficient funds. Available: {cur_bal}, Requested: {amount}"
            }, status=400)

        now = timezone.now()
        today = timezone.localdate()
        trx_no = _gen_trx_no(user.id)  # 8 chars

        # Create transactions
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
            trx_type="CR",
        )
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
            trx_type="DR",
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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from customers.models import Customer

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

        # Support either fields on Customer or via related User
        first_name = getattr(cust, 'first_name', None) or getattr(getattr(cust, 'user', None), 'first_name', '') or ''
        last_name = getattr(cust, 'last_name', None) or getattr(getattr(cust, 'user', None), 'last_name', '') or ''

        return Response({
            'exists': True,
            'gl_no': str(gl_no),
            'ac_no': str(ac_no),
            'account': f'{gl_no}{ac_no}',
            'first_name': first_name,
            'last_name': last_name,
            'full_name': f'{first_name} {last_name}'.strip(),
        }, status=status.HTTP_200_OK)









from rest_framework import serializers
from api.models import Beneficiary

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
        # Automatically link to current user
        user = self.context['request'].user
        return Beneficiary.objects.create(user=user, **validated_data)






# api/views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .serializers import PinSetSerializer, PinVerifySerializer


class PinStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        has_pin = bool(getattr(user, "transaction_pin", None))
        return Response({"has_pin": has_pin}, status=status.HTTP_200_OK)


class PinSetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = PinSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_pin = serializer.validated_data.get("current_pin")
        new_pin = serializer.validated_data["pin"]

        # If a PIN already exists, require the current PIN to change it
        if user.transaction_pin:
            if not current_pin or not user.check_transaction_pin(current_pin):
                return Response({"detail": "Current PIN is incorrect."}, status=status.HTTP_403_FORBIDDEN)

        user.set_transaction_pin(new_pin)
        user.save(update_fields=["transaction_pin"])
        return Response({"detail": "Transaction PIN set successfully."}, status=status.HTTP_200_OK)


class PinVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = PinVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pin = serializer.validated_data["pin"]
        if not user.transaction_pin or not user.check_transaction_pin(pin):
            return Response({"detail": "Invalid PIN."}, status=status.HTTP_403_FORBIDDEN)

        return Response({"ok": True}, status=status.HTTP_200_OK)