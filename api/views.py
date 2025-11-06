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
from django.core.paginator import Paginator
import logging
from datetime import date
from django.utils import timezone

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
    PinSetSerializer, PinVerifySerializer,
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

logger = logging.getLogger(__name__)

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
from decimal import Decimal
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from transactions.models import Memtrans
from .serializers import MemtransSerializer

from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.response import Response
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from transactions.models import Memtrans
from .serializers import MemtransSerializer
from company.models import Company  # ✅ Import Company model


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        print("🔥 DashboardView called - float_account_number fix is ACTIVE!")

        # ✅ 1️⃣ Get logged-in customer
        customer = getattr(request.user, 'customer', None)
        if not customer:
            print("❌ No Customer profile linked to user")
            return Response({"detail": "Customer profile not linked to user."}, status=404)

        # ✅ 2️⃣ Get linked company or fallback to first one
        company = getattr(request.user, 'company', None)
        if not company:
            company = Company.objects.first()

        if not company:
            print("❌ No company found in system")
            return Response(
                {"detail": "Company profile not found in the system."},
                status=404
            )

        print(f"✅ Using company: {company.company_name} ({company.id})")

        # ✅ 3️⃣ Extract key data
        gl_no = (customer.gl_no or '').strip()
        ac_no = (customer.ac_no or '').strip()
        float_account_number = (company.float_account_number or '').strip()
        bank_name = (customer.bank_name or '').strip()
        bank_code = (customer.bank_code or '').strip()

        print(f"🏦 float_account_number from DB: {float_account_number or '❌ None'}")

        # ✅ 4️⃣ If basic info missing
        if not gl_no or not ac_no:
            return Response({
                "customer": {
                    "id": customer.id,
                    "first_name": customer.first_name or "",
                    "last_name": customer.last_name or "",
                    "full_name": f"{customer.first_name or ''} {customer.last_name or ''}".strip(),
                    "email": customer.email or "",
                    "gl_no": gl_no,
                    "ac_no": ac_no,
                    "float_account_number": float_account_number,
                    "bank_name": bank_name,
                    "bank_code": bank_code,
                },
                "balance": 0.0,
                "accounts": [],
                "transactions": [],
            })

        # ✅ 5️⃣ Aggregate balances
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

        # ✅ 6️⃣ Primary account balance
        primary_balance = Decimal('0')
        for r in per_accounts:
            if str(r['gl_no']).strip() == gl_no:
                primary_balance = r['balance'] or Decimal('0')
                break

        # ✅ 7️⃣ Get last 20 transactions
        recent = (
            Memtrans.objects
            .filter(gl_no=gl_no, ac_no=ac_no)
            .order_by('-sys_date')[:20]
        )
        data = MemtransSerializer(recent, many=True).data

        # ✅ 8️⃣ Build account list
        accounts_data = []
        for r in per_accounts:
            accounts_data.append({
                "gl_no": r["gl_no"],
                "ac_no": r["ac_no"],
                "balance": float(r["balance"] or 0),
                "available_balance": float(r["balance"] or 0),
                "float_account_number": float_account_number,
                "bank_name": bank_name,
                "bank_code": bank_code,
            })

        # ✅ 9️⃣ Final response
        response_data = {
            "customer": {
                "id": customer.id,
                "first_name": customer.first_name or "",
                "last_name": customer.last_name or "",
                "full_name": f"{customer.first_name or ''} {customer.last_name or ''}".strip(),
                "email": customer.email or "",
                "gl_no": gl_no,
                "ac_no": ac_no,
                "float_account_number": float_account_number,
                "bank_name": bank_name,
                "bank_code": bank_code,
                "balance": float(primary_balance),
            },
            "primary_gl_no": gl_no,
            "primary_ac_no": ac_no,
            "primary_float_account_number": float_account_number,
            "balance": float(primary_balance),
            "accounts": accounts_data,
            "transactions": data,
        }

        print("✅ Dashboard response prepared successfully.")
        print(f"🧾 Returning float_account_number: {float_account_number or '❌ None'}")

        return Response(response_data)


# ---------------------------------------------------------------------------
# FIXED: Transaction Views - Class-based with JWT Authentication
# ---------------------------------------------------------------------------

class TransactionsView(APIView):
    """Get all transactions using customer gl_no and ac_no - SAME as balance calculation"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            customer = request.user.customer
            print(f"[DEBUG] TransactionsView called by user: {request.user.username}, customer_id={customer.id}")
            
            # Use customer's primary gl_no and ac_no - SAME as DashboardView balance logic
            customer_gl_no = (customer.gl_no or '').strip()
            customer_ac_no = (customer.ac_no or '').strip()
            
            if not customer_gl_no or not customer_ac_no:
                print(f"[DEBUG] Customer {customer.id} missing gl_no or ac_no: gl_no='{customer_gl_no}', ac_no='{customer_ac_no}'")
                return Response({'error': 'Customer account information incomplete'}, status=status.HTTP_400_BAD_REQUEST)
            
            print(f"[DEBUG] Using customer account: gl_no='{customer_gl_no}', ac_no='{customer_ac_no}'")
            
            # Filter by customer's gl_no and ac_no - EXACTLY like DashboardView balance calculation
            transactions = Memtrans.objects.filter(
                gl_no=customer_gl_no, 
                ac_no=customer_ac_no
            ).order_by('-sys_date')  # Use sys_date like in DashboardView
            
            print(f"[DEBUG] Found {transactions.count()} transactions for customer account {customer_gl_no}-{customer_ac_no}")
            
            # Pagination
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 10))
            paginator = Paginator(transactions, limit)
            page_obj = paginator.get_page(page)
            
            print(f"[DEBUG] Pagination: page={page}, limit={limit}, total_pages={paginator.num_pages}")
            
            serializer = MemtransSerializer(page_obj.object_list, many=True)
            return Response({
                'data': serializer.data,
                'pagination': {
                    'page': page,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                }
            })
            
        except Customer.DoesNotExist:
            print("[DEBUG] Customer not found for user:", request.user.username)
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Transactions error: {str(e)}")
            print("[ERROR] Transactions error:", e)
            return Response({'error': 'Failed to load transactions'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from datetime import datetime
from decimal import Decimal
from django.db.models import Q

class LoanTransactionsView(APIView):
    """Get loan transactions for specific account with advanced filtering"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            customer = request.user.customer
            print(f"[DEBUG] LoanTransactionsView called by {request.user.username}, customer_id={customer.id}")
            
            # Get account parameters
            query_gl_no = request.query_params.get('gl_no')
            query_ac_no = request.query_params.get('ac_no')
            
            # Fallback to customer's account if not provided
            if not query_gl_no or not query_ac_no:
                customer_gl_no = (customer.gl_no or '').strip()
                customer_ac_no = (customer.ac_no or '').strip()
                
                if not customer_gl_no or not customer_ac_no:
                    print(f"[DEBUG] Customer {customer.id} missing gl_no or ac_no")
                    return Response({'error': 'Account information missing'}, status=status.HTTP_400_BAD_REQUEST)
                
                query_gl_no = customer_gl_no
                query_ac_no = customer_ac_no
            
            print(f"[DEBUG] Base filter: gl_no='{query_gl_no}', ac_no='{query_ac_no}'")
            
            # Start with base query
            transactions_query = Memtrans.objects.filter(
                gl_no=query_gl_no,
                ac_no=query_ac_no
            )
            
            # Apply filters
            filters_applied = []
            
            # Date range filters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                    transactions_query = transactions_query.filter(ses_date__gte=start_date_obj)
                    filters_applied.append(f"start_date >= {start_date}")
                except ValueError:
                    print(f"[DEBUG] Invalid start_date format: {start_date}")
            
            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    transactions_query = transactions_query.filter(ses_date__lte=end_date_obj)
                    filters_applied.append(f"end_date <= {end_date}")
                except ValueError:
                    print(f"[DEBUG] Invalid end_date format: {end_date}")
            
            # Amount range filters
            min_amount = request.query_params.get('min_amount')
            max_amount = request.query_params.get('max_amount')
            
            if min_amount:
                try:
                    min_amount_decimal = Decimal(min_amount)
                    # Filter for transactions with absolute amount >= min_amount
                    transactions_query = transactions_query.filter(
                        Q(amount__gte=min_amount_decimal) | Q(amount__lte=-min_amount_decimal)
                    )
                    filters_applied.append(f"abs(amount) >= {min_amount}")
                except (ValueError, TypeError):
                    print(f"[DEBUG] Invalid min_amount: {min_amount}")
            
            if max_amount:
                try:
                    max_amount_decimal = Decimal(max_amount)
                    # Filter for transactions with absolute amount <= max_amount  
                    transactions_query = transactions_query.filter(
                        Q(amount__lte=max_amount_decimal, amount__gte=0) | 
                        Q(amount__gte=-max_amount_decimal, amount__lt=0)
                    )
                    filters_applied.append(f"abs(amount) <= {max_amount}")
                except (ValueError, TypeError):
                    print(f"[DEBUG] Invalid max_amount: {max_amount}")
            
            # Transaction number filter
            trx_no = request.query_params.get('trx_no')
            if trx_no:
                transactions_query = transactions_query.filter(trx_no__icontains=trx_no)
                filters_applied.append(f"trx_no contains '{trx_no}'")
            
            # Order by date (newest first)
            transactions_query = transactions_query.order_by('-sys_date')
            
            print(f"[DEBUG] Applied filters: {', '.join(filters_applied) if filters_applied else 'None'}")
            print(f"[DEBUG] Found {transactions_query.count()} transactions after filtering")
            
            # Pagination
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 10))
            paginator = Paginator(transactions_query, limit)
            page_obj = paginator.get_page(page)
            
            print(f"[DEBUG] Pagination: page={page}/{paginator.num_pages}, limit={limit}")
            
            serializer = MemtransSerializer(page_obj.object_list, many=True)
            
            return Response({
                'data': serializer.data,
                'pagination': {
                    'page': page,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                },
                'filters_applied': filters_applied,  # Debug info
                'query_params': dict(request.query_params),  # Debug info
            })
            
        except Customer.DoesNotExist:
            print("[DEBUG] Customer not found for user:", request.user.username)
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Loan transactions error: {str(e)}")
            print("[ERROR] Loan transactions error:", e)
            import traceback
            traceback.print_exc()
            return Response({'error': 'Failed to load loan transactions'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RegularTransactionsView(APIView):
    """Get regular (non-loan) transactions - customer's gl_no and ac_no, excluding loans"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            customer = request.user.customer
            print(f"[DEBUG] RegularTransactionsView called by {request.user.username}, customer_id={customer.id}")
            
            # Use customer's primary gl_no and ac_no
            customer_gl_no = (customer.gl_no or '').strip()
            customer_ac_no = (customer.ac_no or '').strip()
            
            if not customer_gl_no or not customer_ac_no:
                print(f"[DEBUG] Customer {customer.id} missing gl_no or ac_no: gl_no='{customer_gl_no}', ac_no='{customer_ac_no}'")
                return Response({'error': 'Customer account information incomplete'}, status=status.HTTP_400_BAD_REQUEST)
            
            print(f"[DEBUG] Looking for regular transactions: gl_no='{customer_gl_no}', ac_no='{customer_ac_no}', excluding gl_no='10412'")
            
            # Filter by customer's gl_no and ac_no, but EXCLUDE loan transactions (gl_no='10412')
            transactions = Memtrans.objects.filter(
                gl_no=customer_gl_no,
                ac_no=customer_ac_no
            ).order_by('-sys_date')
            
            print(f"[DEBUG] Found {transactions.count()} regular transactions (excluding loans) for {customer_gl_no}-{customer_ac_no}")
            
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 10))
            paginator = Paginator(transactions, limit)
            page_obj = paginator.get_page(page)
            
            print(f"[DEBUG] Regular pagination: page={page}/{paginator.num_pages}, limit={limit}")
            
            serializer = MemtransSerializer(page_obj.object_list, many=True)
            return Response({
                'data': serializer.data,
                'pagination': {
                    'page': page,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                }
            })
            
        except Customer.DoesNotExist:
            print("[DEBUG] Customer not found for user:", request.user.username)
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Regular transactions error: {str(e)}")
            print("[ERROR] Regular transactions error:", e)
            return Response({'error': 'Failed to load regular transactions'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

# Add these new signup views to your existing views.py file
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
import string
from customers.models import Customer
from accounts.models import User as CustomUser

# CORRECTED SMS Service for Termii - FIXED VERSION
class TermiiSMSService:
    def __init__(self):
        self.api_key = getattr(settings, 'TERMII_API_KEY', '')
        self.sender_id = getattr(settings, 'TERMII_SENDER_ID', 'FinanceFlex')
        self.base_url = 'https://api.ng.termii.com/api'
    
    def send_otp_sms(self, phone_number, otp_code, expires_in_minutes=5):
        if not self.api_key:
            logger.warning("[SMS] Termii API key not configured")
            return {'success': False, 'error': 'SMS API key not configured'}
        
        # Format phone number for Nigerian numbers
        if phone_number.startswith('0'):
            phone_number = '234' + phone_number[1:]
        elif not phone_number.startswith('234'):
            phone_number = '234' + phone_number
        
        message = f"Your FinanceFlex verification code is: {otp_code}. Valid for {expires_in_minutes} minutes. Do not share this code."
        
        payload = {
            "to": phone_number,
            "from": self.sender_id,
            "sms": message,
            "type": "plain",
            "api_key": self.api_key,
            "channel": "generic"  # FIXED: Use 'generic' instead of 'dnd' for better delivery
        }
        
        try:
            logger.info(f"[SMS] Sending OTP to {phone_number}")
            response = requests.post(f"{self.base_url}/sms/send", json=payload, timeout=10)
            response_data = response.json()
            
            # FIXED: Better response validation
            if response.status_code == 200 and (
                response_data.get('code') == 'ok' or 
                response_data.get('message') == 'Successfully Sent'
            ):
                logger.info(f"[SMS] SMS sent successfully: {response_data.get('message_id')}")
                return {
                    'success': True,
                    'message_id': response_data.get('message_id'),
                    'balance': response_data.get('balance')
                }
            else:
                logger.error(f"[SMS] SMS failed: {response_data}")
                return {
                    'success': False,
                    'error': response_data.get('message', 'SMS sending failed')
                }
                
        except Exception as e:
            logger.error(f"[SMS] SMS service error: {str(e)}")
            return {'success': False, 'error': f'SMS service error: {str(e)}'}

from django.core.mail import send_mail
from django.conf import settings

# Create SMS service instance
sms_service = TermiiSMSService()

# CORRECTED 9PSB Virtual Account Service - FIXED VERSION
# ---------------------------------------------------------------------------
# CORRECTED & ENHANCED 9PSB Virtual Account Service
# - Uses 'code': '00' for success
# - Returns bank_name and branch_code (hardcoded defaults)
# ---------------------------------------------------------------------------
import requests
import logging
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

logger = logging.getLogger(__name__)

class NinePSBVirtualAccountService:
    def __init__(self):
        self.base_url = getattr(settings, 'PSB_BASE_URL', 'https://baastest.9psb.com.ng/iva-api/v1').strip()
        self.public_key = getattr(settings, 'PSB_PUBLIC_KEY', '').strip()
        self.private_key = getattr(settings, 'PSB_PRIVATE_KEY', '').strip()
        self.access_token = None
        self.token_expires_at = None

    def authenticate(self):
        """Authenticate using 'code': '00' success logic."""
        if not self.public_key or not self.private_key:
            logger.error("[9PSB] API keys not configured")
            return {'success': False, 'error': 'API keys not configured'}

        if self.access_token and self.token_expires_at and timezone.now() < self.token_expires_at:
            return {'success': True, 'access_token': self.access_token}

        try:
            url = f"{self.base_url}/merchant/virtualaccount/authenticate"
            # NOTE: 9PSB uses "publickey" and "privatekey" (lowercase) in actual API
            payload = {
                "publickey": self.public_key,
                "privatekey": self.private_key
            }
            headers = {"Content-Type": "application/json"}
            logger.info(f"[9PSB] Authenticating at: {url}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            logger.info(f"[9PSB] Auth Status: {response.status_code}")
            logger.info(f"[9PSB] Auth Response: {response.text}")

            if not response.text.strip():
                return {'success': False, 'error': 'Empty auth response'}

            if response.text.strip().startswith('<'):
                return {'success': False, 'error': f'HTML response (status {response.status_code})'}

            try:
                data = response.json()
            except ValueError as e:
                logger.error(f"[9PSB] Auth JSON decode error: {e}")
                return {'success': False, 'error': 'Invalid JSON in auth response'}

            # ✅ CRITICAL FIX: Use 'code' == '00' instead of 'status' == 'SUCCESS'
            if response.status_code == 200 and data.get('code') == '00':
                token = data.get('access_token')
                expires_in = data.get('expires_in', 3600)
                if not token:
                    return {'success': False, 'error': 'Missing access_token'}

                self.access_token = token
                self.token_expires_at = timezone.now() + timedelta(seconds=expires_in - 60)
                logger.info("[9PSB] Authentication successful")
                return {'success': True, 'access_token': token}
            else:
                msg = data.get('message', 'Unknown auth error')
                logger.error(f"[9PSB] Auth failed: {msg}")
                return {'success': False, 'error': msg}

        except Exception as e:
            logger.exception(f"[9PSB] Auth exception: {e}")
            return {'success': False, 'error': str(e)}

    def create_virtual_account(self, customer_name, customer_id, phone_number, email=None):
        """Create virtual account and return bank_name + branch_code."""
        auth_result = self.authenticate()
        if not auth_result['success']:
            return auth_result

        try:
            url = f"{self.base_url}/merchant/virtualaccount/create"
            transaction_reference = f"REG_{customer_id}_{int(timezone.now().timestamp())}"

            payload = {
                "transaction": {"reference": transaction_reference},
                "order": {
                    "amount": 0,
                    "currency": "NGN",
                    "country": "NGA",
                    "amounttype": "ANY"
                },
                "customer": {
                    "account": {"name": customer_name, "type": "STATIC"},
                    "phone": phone_number,
                    "email": email or f"customer_{customer_id}@financeflex.com"
                }
            }

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            logger.info(f"[9PSB] Creating VA for: {customer_name}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            logger.info(f"[9PSB] VA Create Status: {response.status_code}")
            logger.info(f"[9PSB] VA Create Response: {response.text}")

            if response.text.strip().startswith('<'):
                return {'success': False, 'error': f'HTML response (status {response.status_code})'}

            try:
                data = response.json()
            except ValueError:
                return {'success': False, 'error': 'Invalid JSON in VA creation response'}

            # ✅ Use 'code': '00' for success
            if response.status_code == 200 and data.get('code') == '00':
                va_number = data.get('customer', {}).get('account', {}).get('number')
                if not va_number:
                    return {'success': False, 'error': 'No virtual account number returned'}

                # 🔹 9PSB does NOT return bank_name or branch_code → use defaults
                bank_name = "9 Payment Service Bank"
                branch_code = "0000"  # or derive from settings/customer if needed

                logger.info(f"[9PSB] VA created: {va_number} | Bank: {bank_name} | Branch: {branch_code}")
                return {
                    'success': True,
                    'virtual_account_number': va_number,
                    'bank_name': bank_name,
                    'branch_code': branch_code,
                    'transaction_reference': transaction_reference,
                    'response_data': data
                }

            # Handle token expiry and retry once
            if response.status_code == 401:
                logger.warning("[9PSB] Token expired, retrying...")
                self.access_token = None
                self.token_expires_at = None
                auth_retry = self.authenticate()
                if auth_retry['success']:
                    headers['Authorization'] = f"Bearer {auth_retry['access_token']}"
                    retry_resp = requests.post(url, json=payload, headers=headers, timeout=30)
                    try:
                        retry_data = retry_resp.json()
                    except ValueError:
                        return {'success': False, 'error': 'Invalid JSON on retry'}

                    if retry_resp.status_code == 200 and retry_data.get('code') == '00':
                        va_number = retry_data.get('customer', {}).get('account', {}).get('number')
                        if va_number:
                            bank_name = "9 Payment Service Bank"
                            branch_code = "0000"
                            return {
                                'success': True,
                                'virtual_account_number': va_number,
                                'bank_name': bank_name,
                                'branch_code': branch_code,
                                'transaction_reference': transaction_reference,
                                'response_data': retry_data
                            }

            # Final failure
            msg = data.get('message', 'Unknown error')
            logger.error(f"[9PSB] VA creation failed: {msg}")
            return {'success': False, 'error': msg}

        except Exception as e:
            logger.exception(f"[9PSB] VA creation exception: {e}")
            return {'success': False, 'error': str(e)}


# Global instance
nine_psb_service = NinePSBVirtualAccountService()

# Global instance
nine_psb_service = NinePSBVirtualAccountService()
def create_virtual_account(self, customer_name, customer_id, phone_number, email=None):
    """Create a virtual account for a customer - FIXED VARIABLE SCOPING"""
    # First authenticate
    auth_result = self.authenticate()
    if not auth_result['success']:
        return auth_result
        
    try:
        # FIXED: Use correct virtual account creation endpoint
        url = f"{self.base_url}/merchant/virtualaccount/create"
        
        # Generate unique transaction reference
        transaction_reference = f"REG_{customer_id}_{int(timezone.now().timestamp())}"
        
        # FIXED: Define payload at method level to ensure proper scoping
        payload = {
            "transaction": {
                "reference": transaction_reference
            },
            "order": {
                "amount": 0,  # Minimal amount for ANY type
                "currency": "NGN",
                "country": "NGA",
                "amounttype": "ANY"  # Allows any amount to be received
            },
            "customer": {
                "account": {
                    "name": customer_name,
                    "type": "STATIC"  # Permanent virtual account
                },
                "phone": phone_number,
                "email": email or f"customer_{customer_id}@financeflex.com"
            }
        }
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"[9PSB] Creating virtual account for customer: {customer_name}")
        logger.info(f"[9PSB] Request URL: {url}")
        logger.info(f"[9PSB] Request payload: {payload}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        # FIXED: Add response debugging
        logger.info(f"[9PSB] Response Status: {response.status_code}")
        logger.info(f"[9PSB] Response Headers: {dict(response.headers)}")
        logger.info(f"[9PSB] Response Text: {response.text}")
        
        # Check if response is empty or HTML
        if not response.text.strip():
            logger.error("[9PSB] Empty response received")
            return {'success': False, 'error': 'Empty response from 9PSB API'}
            
        if response.text.strip().startswith('<'):
            logger.error("[9PSB] HTML response received (likely 404 or error page)")
            return {'success': False, 'error': f'HTML response received. Status: {response.status_code}'}
        
        try:
            response_data = response.json()
        except ValueError as e:
            logger.error(f"[9PSB] JSON decode error: {str(e)}")
            logger.error(f"[9PSB] Raw response: {response.text}")
            return {'success': False, 'error': f'Invalid JSON response: {str(e)}'}
        
        if response.status_code == 200 and response_data.get('status') == 'SUCCESS':
            virtual_account_number = response_data.get('customer', {}).get('account', {}).get('number')
            
            if virtual_account_number:
                logger.info(f"[9PSB] Virtual account created successfully: {virtual_account_number}")
                return {
                    'success': True,
                    'virtual_account_number': virtual_account_number,
                    'transaction_reference': transaction_reference,
                    'response_data': response_data
                }
            else:
                logger.error(f"[9PSB] No account number in response: {response_data}")
                return {'success': False, 'error': 'No account number returned'}
        else:
            # FIXED: Proper retry logic with correct variable scoping
            if response.status_code == 401:
                logger.warning("[9PSB] Token expired, retrying authentication")
                self.access_token = None
                self.token_expires_at = None
                
                # Retry authentication and account creation
                auth_retry = self.authenticate()
                if auth_retry['success']:
                    # Update headers with new token
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    
                    logger.info("[9PSB] Retrying virtual account creation with new token")
                    retry_response = requests.post(url, json=payload, headers=headers, timeout=30)
                    
                    # Log retry response
                    logger.info(f"[9PSB] Retry Response Status: {retry_response.status_code}")
                    logger.info(f"[9PSB] Retry Response Text: {retry_response.text}")
                    
                    try:
                        retry_data = retry_response.json()
                    except ValueError as e:
                        logger.error(f"[9PSB] Retry JSON decode error: {str(e)}")
                        return {'success': False, 'error': f'Invalid JSON on retry: {str(e)}'}
                    
                    if retry_response.status_code == 200 and retry_data.get('status') == 'SUCCESS':
                        virtual_account_number = retry_data.get('customer', {}).get('account', {}).get('number')
                        if virtual_account_number:
                            logger.info(f"[9PSB] Virtual account created on retry: {virtual_account_number}")
                            return {
                                'success': True,
                                'virtual_account_number': virtual_account_number,
                                'transaction_reference': transaction_reference,
                                'response_data': retry_data
                            }
            
            logger.error(f"[9PSB] Virtual account creation failed: {response_data}")
            return {'success': False, 'error': response_data.get('message', 'Virtual account creation failed')}
            
    except Exception as e:
        logger.error(f"[9PSB] Virtual account creation error: {str(e)}")
        import traceback
        logger.error(f"[9PSB] Traceback: {traceback.format_exc()}")
        return {'success': False, 'error': f'Virtual account creation error: {str(e)}'}

# Create 9PSB service instance
nine_psb_service = NinePSBVirtualAccountService()

class VerifyAccountAPIView(APIView):
    """Step 1: Verify account ownership with account number, DOB, and phone"""
    permission_classes = [AllowAny]

    def post(self, request):
        account_number = request.data.get('account_number')
        date_of_birth = request.data.get('date_of_birth')  # Format: YYYY-MM-DD
        phone_number = request.data.get('phone_number')

        if not account_number or len(account_number) < 10:
            return Response({
                'error': 'Invalid account number'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Parse account number into gl_no and ac_no
        if len(account_number) >= 10:
            gl_no = account_number[:5]
            ac_no = account_number[5:]
        else:
            return Response({
                'error': 'Account number must be at least 10 digits'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify customer exists with matching details
        try:
            customer = Customer.objects.get(
                gl_no=gl_no,
                ac_no=ac_no,
                dob=date_of_birth,
                phone_no=phone_number
            )
        except Customer.DoesNotExist:
            return Response({
                'error': 'Account verification failed. Please check your details.'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'message': 'Account verified successfully',
            'account_number': account_number,
            'customer_name': customer.get_full_name()
        })

class SendOTPAPIView(APIView):
    """Step 2: Send OTP to phone and email with real SMS"""
    permission_classes = [AllowAny]

    def post(self, request):
        account_number = request.data.get('account_number')
        phone_number = request.data.get('phone_number')

        if not account_number or not phone_number:
            return Response({
                'error': 'Account number and phone number are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify customer exists
        if len(account_number) >= 10:
            gl_no = account_number[:5]
            ac_no = account_number[5:]
        else:
            return Response({
                'error': 'Invalid account number format'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer = Customer.objects.get(gl_no=gl_no, ac_no=ac_no)
        except Customer.DoesNotExist:
            return Response({
                'error': 'Account not found'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Generate 6-digit OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        
        # Store OTP in session
        request.session[f'otp_{account_number}'] = {
            'code': otp_code,
            'expires': (timezone.now() + timedelta(minutes=5)).timestamp(),
            'phone': phone_number,
            'attempts': 0
        }

        # Send OTP via SMS (Termii)
        sms_result = sms_service.send_otp_sms(phone_number, otp_code, expires_in_minutes=5)
        
        # Send OTP via Email (if customer has email)
        email_sent = False
        if customer.email:
            try:
                send_mail(
                    subject='FinanceFlex - Account Verification Code',
                    message=(
                        f'Your FinanceFlex verification code is: {otp_code}\n\n'
                        f'This code expires in 5 minutes. '
                        f'Do not share this code with anyone.\n\n'
                        f'If you didn\'t request this, please ignore this email.'
                    ),
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@financeflex.com'),
                    recipient_list=[customer.email],
                    fail_silently=True
                )
                email_sent = True
            except Exception as e:
                print(f"Email sending failed: {e}")

        # Prepare response
        response_data = {
            'success': True,
            'message': f'OTP sent to {phone_number}',
            'sms_sent': sms_result['success'],
            'email_sent': email_sent,
        }

        # Include SMS details if available
        if sms_result['success']:
            response_data['sms_message_id'] = sms_result.get('message_id')
        else:
            response_data['sms_error'] = sms_result.get('error')

        # For development/testing - remove in production
        if settings.DEBUG:
            response_data['debug_otp'] = otp_code

        return Response(response_data)

class VerifyOTPAPIView(APIView):
    """Step 3: Verify OTP code with attempt limiting"""
    permission_classes = [AllowAny]

    def post(self, request):
        account_number = request.data.get('account_number')
        otp_code = request.data.get('otp_code')

        if not otp_code or len(otp_code) != 6:
            return Response({
                'error': 'Invalid OTP format. Please enter 6 digits.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify OTP from session
        otp_data = request.session.get(f'otp_{account_number}')
        if not otp_data:
            return Response({
                'error': 'OTP session not found or expired'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check expiry
        if timezone.now().timestamp() > otp_data['expires']:
            del request.session[f'otp_{account_number}']
            return Response({
                'error': 'OTP has expired. Please request a new code.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check attempt limit
        attempts = otp_data.get('attempts', 0)
        if attempts >= 3:
            del request.session[f'otp_{account_number}']
            return Response({
                'error': 'Too many failed attempts. Please request a new OTP.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify OTP code
        if otp_data['code'] != otp_code:
            # Increment attempts
            otp_data['attempts'] = attempts + 1
            request.session[f'otp_{account_number}'] = otp_data
            
            remaining_attempts = 3 - otp_data['attempts']
            return Response({
                'error': f'Invalid OTP code. {remaining_attempts} attempts remaining.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # OTP verified successfully
        # Generate temporary token for registration step
        otp_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        request.session[f'otp_token_{account_number}'] = {
            'token': otp_token,
            'expires': (timezone.now() + timedelta(minutes=10)).timestamp(),
            'verified_phone': otp_data['phone']
        }

        # Clear used OTP
        del request.session[f'otp_{account_number}']

        return Response({
            'success': True,
            'message': 'OTP verified successfully',
            'otp_token': otp_token
        })

# Resend OTP endpoint
class ResendOTPAPIView(APIView):
    """Resend OTP with rate limiting"""
    permission_classes = [AllowAny]

    def post(self, request):
        account_number = request.data.get('account_number')
        phone_number = request.data.get('phone_number')

        # Check if previous OTP session exists
        otp_data = request.session.get(f'otp_{account_number}')
        if otp_data:
            # Check if enough time has passed (prevent spam)
            time_since_last = timezone.now().timestamp() - (otp_data['expires'] - 300)  # 300 = 5 mins
            if time_since_last < 60:  # Wait at least 1 minute
                return Response({
                    'error': f'Please wait {60 - int(time_since_last)} seconds before requesting a new OTP'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Use the same logic as SendOTPAPIView
        send_otp_view = SendOTPAPIView()
        return send_otp_view.post(request)

# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
import string
import logging

# ENHANCED: Import the comprehensive 9PSB service
from .services.enhanced_psb_service import enhanced_psb_service

logger = logging.getLogger(__name__)


# api/views_fixed.py - COMPREHENSIVE FIXES FOR ACCOUNT CREATION
"""
FIXED Django API views addressing the 9PSB response parsing issue and other account creation problems
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.core.cache import cache
from datetime import timedelta
import random
import string
import logging

logger = logging.getLogger(__name__)

# Import the FIXED services
# In your api/views.py, replace the failing import:
# from .services.psb_service_final_fix import nine_psb_service
# from .services.sms_service_fix import sms_service

# Import models with error handling
try:
    from customers.models import Customer
except ImportError:
    logger.warning("Customer model not found")
    Customer = None

try:
    from accounts.models import User as CustomUser
except ImportError:
    logger.warning("Custom User model not found, using default")
    CustomUser = get_user_model()

# Import helper functions
from .helpers import (
    normalize_phone, 
    parse_account_number, 
    safe_customer_lookup,
    format_error_response,
    format_success_response
)



# ... other view classes follow the same pattern


# Alternative implementation showing dictionary-based calling convention

class SetupPINAPIView(APIView):
    """Step 5: Setup transaction PIN"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        username = request.data.get('username')
        pin = request.data.get('pin')

        if not pin or len(pin) != 4 or not pin.isdigit():
            return Response({
                'error': 'PIN must be exactly 4 digits'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Set transaction PIN
        user = request.user
        user.set_transaction_pin(pin)
        user.save()

        return Response({
            'success': True,
            'message': 'Transaction PIN set successfully'
        })

# ---------------------------------------------------------------------------
# BULLETPROOF SIGNUP VIEWS - DATABASE STORAGE (Add to end of views.py)
# ---------------------------------------------------------------------------

# Import OTP models
from .models import OTPVerification, RegistrationToken
import requests

# SMS Service imports
logger = logging.getLogger(__name__)

class VerifyAccountAPIView(APIView):
    """Step 1: Verify account ownership with account number, DOB, and phone"""
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            account_number = request.data.get('account_number')
            date_of_birth = request.data.get('date_of_birth')  # Format: YYYY-MM-DD
            phone_number = request.data.get('phone_number')

            logger.info(f"[VERIFY] Account verification attempt for: {account_number}")

            # Validate required fields
            if not account_number:
                return Response({
                    'error': 'Account number is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not date_of_birth:
                return Response({
                    'error': 'Date of birth is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not phone_number:
                return Response({
                    'error': 'Phone number is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate account number format
            if len(account_number) < 10:
                return Response({
                    'error': 'Account number must be at least 10 digits'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Parse account number into gl_no and ac_no
            if len(account_number) >= 10:
                gl_no = account_number[:5]
                ac_no = account_number[5:]
            else:
                return Response({
                    'error': 'Invalid account number format'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Parse and validate date of birth
            try:
                dob_date = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Format phone number (remove any non-digits and check format)
            phone_digits = ''.join(filter(str.isdigit, phone_number))
            
            # Try different phone number formats for matching
            phone_variations = [
                phone_digits,
                phone_digits[-10:] if len(phone_digits) > 10 else phone_digits,
                phone_digits[-11:] if len(phone_digits) > 11 else phone_digits,
            ]

            # Add leading zero if missing for Nigerian numbers
            if len(phone_digits) == 10 and not phone_digits.startswith('0'):
                phone_variations.append('0' + phone_digits)

            logger.info(f"[VERIFY] Looking for customer: gl_no={gl_no}, ac_no={ac_no}")

            # Verify customer exists with matching details
            customer = None
            for phone_var in phone_variations:
                try:
                    customer = Customer.objects.get(
                        gl_no=gl_no,
                        ac_no=ac_no,
                        dob=dob_date,
                        phone_no=phone_var
                    )
                    logger.info(f"[VERIFY] Customer found with phone: {phone_var}")
                    break
                except Customer.DoesNotExist:
                    continue

            # If not found with phone, try without phone (in case phone field is different)
            if not customer:
                try:
                    customer = Customer.objects.get(
                        gl_no=gl_no,
                        ac_no=ac_no,
                        dob=dob_date
                    )
                    logger.info("[VERIFY] Customer found without phone matching")
                    
                    # Update customer phone if found without phone match
                    if phone_digits:
                        customer.phone_no = phone_digits
                        customer.save(update_fields=['phone_no'])
                        
                except Customer.DoesNotExist:
                    pass

            if not customer:
                logger.warning(f"[VERIFY] Account verification FAILED for: {account_number}")
                return Response({
                    'error': 'Account verification failed. Please check your account number, date of birth, and phone number.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if user already exists for this customer
            # Try to check if customer field exists, if not skip this check
            try:
                existing_user = CustomUser.objects.filter(customer=customer).first()
                if existing_user:
                    return Response({
                        'error': 'An account already exists for this customer. Please use the login page.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.warning(f"[VERIFY] Could not check existing user by customer: {e}")
                # If customer field doesn't exist, check by other fields
                pass

            logger.info(f"[VERIFY] Account verification SUCCESS for: {customer.get_full_name()}")

            return Response({
                'success': True,
                'message': 'Account verified successfully',
                'account_number': account_number,
                'customer_name': customer.get_full_name(),
                'customer_id': customer.id
            })

        except Exception as e:
            logger.error(f"[VERIFY] Account verification ERROR: {str(e)}")
            return Response({
                'error': 'Account verification failed due to system error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SendOTPAPIView(APIView):
    """Step 2: Send OTP to phone and email - DATABASE STORAGE"""
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            account_number = request.data.get('account_number')
            phone_number = request.data.get('phone_number')

            logger.info(f"[SEND_OTP] Request for account: {account_number}")

            if not account_number or not phone_number:
                return Response({
                    'error': 'Account number and phone number are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify customer exists (same logic as verify account)
            if len(account_number) >= 10:
                gl_no = account_number[:5]
                ac_no = account_number[5:]
            else:
                return Response({
                    'error': 'Invalid account number format'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                customer = Customer.objects.get(gl_no=gl_no, ac_no=ac_no)
                logger.info(f"[SEND_OTP] Customer found: {customer.get_full_name()}")
            except Customer.DoesNotExist:
                logger.warning(f"[SEND_OTP] Customer not found for: {account_number}")
                return Response({
                    'error': 'Account not found'
                }, status=status.HTTP_400_BAD_REQUEST)

            # DATABASE STORAGE: Create OTP in database
            otp = OTPVerification.create_otp(
                account_number=account_number,
                phone_number=phone_number,
                customer_id=customer.id
            )
            
            logger.info(f"[SEND_OTP] OTP created in database for: {account_number}")

            # Send OTP via SMS
            sms_result = sms_service.send_otp_sms(phone_number, otp.otp_code, expires_in_minutes=5)

            # Send OTP via Email if customer has email
            email_sent = False
            if customer.email:
                try:
                    send_mail(
                        subject='FinanceFlex - Account Verification Code',
                        message=(
                            f'Hello {customer.get_full_name()},\n\n'
                            f'Your FinanceFlex verification code is: {otp.otp_code}\n\n'
                            f'This code expires in 5 minutes. '
                            f'Do not share this code with anyone.\n\n'
                            f'If you didn\'t request this, please ignore this email.\n\n'
                            f'FinanceFlex Team'
                        ),
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@financeflex.com'),
                        recipient_list=[customer.email],
                        fail_silently=False
                    )
                    email_sent = True
                    logger.info(f"[SEND_OTP] Email sent to: {customer.email}")
                except Exception as e:
                    logger.error(f"[SEND_OTP] Email failed: {e}")

            # Prepare response
            response_data = {
                'success': True,
                'message': f'OTP sent to {phone_number[-4:].rjust(len(phone_number), "*")}',
                'sms_sent': sms_result.get('success', False),
                'email_sent': email_sent,
                'expires_in': 300,  # 5 minutes in seconds
                'otp_id': otp.id  # Database ID for debugging
            }

            # Include SMS details if available
            if sms_result.get('success'):
                response_data['sms_message_id'] = sms_result.get('message_id')
                response_data['sms_balance'] = sms_result.get('balance')
            else:
                response_data['sms_error'] = sms_result.get('error')

            # For development/testing - remove in production
            if getattr(settings, 'DEBUG', False):
                response_data['debug_otp'] = otp.otp_code
                response_data['debug_expires_at'] = otp.expires_at.isoformat()
                logger.info(f"[SEND_OTP] DEBUG OTP for {account_number}: {otp.otp_code}")

            return Response(response_data)

        except Exception as e:
            logger.error(f"[SEND_OTP] ERROR: {str(e)}")
            return Response({
                'error': 'Failed to send OTP due to system error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyOTPAPIView(APIView):
    """Step 3: Verify OTP code - DATABASE STORAGE"""
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            account_number = request.data.get('account_number')
            otp_code = request.data.get('otp_code')

            logger.info(f"[VERIFY_OTP] Request for account: {account_number}, OTP: {otp_code}")

            if not otp_code or len(otp_code) != 6 or not otp_code.isdigit():
                return Response({
                    'error': 'Invalid OTP format. Please enter 6 digits.'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not account_number:
                return Response({
                    'error': 'Account number is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # DATABASE STORAGE: Verify OTP from database
            result = OTPVerification.verify_otp(account_number, otp_code)
            
            logger.info(f"[VERIFY_OTP] Database result: {result}")

            if not result['success']:
                return Response({
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)

            # OTP verified successfully
            otp = result['otp']
            
            # DATABASE STORAGE: Create registration token
            reg_token = RegistrationToken.create_token(
                account_number=account_number,
                customer_id=otp.customer_id,
                verified_phone=otp.phone_number
            )

            logger.info(f"[VERIFY_OTP] SUCCESS - Token created for: {account_number}")

            return Response({
                'success': True,
                'message': 'OTP verified successfully',
                'otp_token': reg_token.token
            })

        except Exception as e:
            logger.error(f"[VERIFY_OTP] ERROR: {str(e)}")
            return Response({
                'error': 'OTP verification failed due to system error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import logging

from accounts_admin.models import Account


logger = logging.getLogger(__name__)



class RegisterUserAPIView(APIView):
    """Register user and create 9PSB virtual account with fully populated Customer"""
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # --- Extract input fields ---
            account_number = request.data.get('account_number')
            username = request.data.get('username')
            password = request.data.get('password')
            otp_token = request.data.get('otp_token')

            if not all([username, password, account_number, otp_token]):
                return Response(
                    {'error': 'All fields (username, password, account_number, otp_token) are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # --- Verify registration token ---
            token_result = RegistrationToken.verify_token(account_number, otp_token)
            if not token_result['success']:
                return Response({'error': token_result['error']}, status=status.HTTP_400_BAD_REQUEST)

            reg_token = token_result['token_obj']

            # --- Check username existence ---
            if CustomUser.objects.filter(username=username).exists():
                return Response(
                    {'error': 'Username already exists. Please choose a different username.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # --- Get original Customer linked to token ---
            try:
                orig_customer = Customer.objects.get(id=reg_token.customer_id)
            except Customer.DoesNotExist:
                return Response({'error': 'Customer not found'}, status=status.HTTP_400_BAD_REQUEST)

            # --- Check if GL 20111 exists ---
            gl_account = Account.objects.filter(gl_no='20111').first()
            if not gl_account:
                return Response(
                    {'error': 'System configuration error: GL 20111 not found in Accounts'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # --- Create 9PSB virtual account ---
            try:
                va_result = nine_psb_service.create_virtual_account(
                    customer_name=orig_customer.get_full_name(),
                    customer_id=orig_customer.id,
                    phone_number=orig_customer.phone_no or reg_token.verified_phone,
                    email=orig_customer.email
                )
            except Exception as e:
                return Response({'error': f'Virtual account creation failed: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if not va_result.get('success'):
                return Response(
                    {'error': f"Virtual account creation failed: {va_result.get('error', 'Unknown error')}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            virtual_account_number = va_result['virtual_account_number']
            bank_name = va_result.get('bank_name', '9 Payment Service Bank')
            branch_code = va_result.get('branch_code', '0000')

            # ✅ Split account_number into GL and AC parts
            # Example: if account_number = "2011161775"
            # GL = first 5 digits, AC = last 5 digits
            gl_no = account_number[:5] if len(account_number) >= 5 else "00000"
            ac_no = account_number[-5:] if len(account_number) >= 5 else account_number

            # --- Everything is valid, create user and new customer atomically ---
            with transaction.atomic():
                # ✅ Create new Customer for this VA, fully populated
                new_customer = Customer.objects.create(
                    photo=orig_customer.photo,
                    sign=orig_customer.sign,
                    branch=orig_customer.branch,
                    gl_no=gl_account.gl_no,
                    ac_no=ac_no,
                    first_name=orig_customer.first_name,
                    middle_name=orig_customer.middle_name,
                    last_name=orig_customer.last_name,
                    dob=orig_customer.dob,
                    email=orig_customer.email,
                    cust_sex=orig_customer.cust_sex,
                    marital_status=orig_customer.marital_status,
                    address=orig_customer.address,
                    nationality=orig_customer.nationality,
                    state=orig_customer.state,
                    phone_no=orig_customer.phone_no,
                    mobile=orig_customer.mobile,
                    id_card=orig_customer.id_card,
                    id_type=orig_customer.id_type,
                    ref_no=orig_customer.ref_no,
                    occupation=orig_customer.occupation,
                    cust_cat=orig_customer.cust_cat,
                    internal=orig_customer.internal,
                    region=orig_customer.region,
                    credit_officer=orig_customer.credit_officer,
                    group_code=orig_customer.group_code,
                    group_name=orig_customer.group_name,
                    reg_date=orig_customer.reg_date,
                    close_date=orig_customer.close_date,
                    status=orig_customer.status,
                    balance=orig_customer.balance,
                    label=orig_customer.label,
                    loan=orig_customer.loan,
                    sms=orig_customer.sms,
                    email_alert=orig_customer.email_alert,
                    bvn=orig_customer.bvn,
                    nin=orig_customer.nin,
                    wallet_account=virtual_account_number,
                    bank_name=bank_name,
                    bank_code=orig_customer.bank_code,
                    transfer_limit=orig_customer.transfer_limit,
                    group=orig_customer.group,
                    registration_number=orig_customer.registration_number,
                    contact_person_name=orig_customer.contact_person_name,
                    contact_person_phone=orig_customer.contact_person_phone,
                    contact_person_email=orig_customer.contact_person_email,
                    office_address=orig_customer.office_address,
                    office_phone=orig_customer.office_phone,
                    office_email=orig_customer.office_email,
                    is_company=orig_customer.is_company
                )

                # ✅ Create CustomUser — GL & AC from split input, not from Customer
                user = CustomUser.objects.create_user(
                    username=username,
                    password=password,
                    email=new_customer.email or f"{username}@financeflex.com",
                    first_name=new_customer.first_name or "",
                    last_name=new_customer.last_name or "",
                    role=getattr(CustomUser, 'CUSTOMER', 'customer'),
                    gl_no=gl_no,
                    ac_no=ac_no
                )

                user.customer = new_customer
                user.branch = new_customer.branch  # ✅ Attach the same branch
                if hasattr(user, 'verified'):
                    user.verified = True
                if hasattr(user, 'phone_number'):
                    user.phone_number = new_customer.phone_no
                user.save()

                # ✅ Mark registration token as used
                reg_token.mark_used()

            # --- Generate JWT tokens ---
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            return Response({
                'success': True,
                'message': 'User registered successfully',
                'username': username,
                'customer_name': new_customer.get_full_name(),
                'wallet_account': virtual_account_number,
                'virtual_account_number': virtual_account_number,
                'bank_name': bank_name,
                'branch_code': branch_code,
                'gl_no': gl_no,
                'ac_no': ac_no,
                'access_token': str(access_token),
                'refresh_token': str(refresh)
            })

        except Exception as e:
            logger.error(f"[REGISTER] ERROR: {str(e)}", exc_info=True)
            return Response({'error': f'Registration failed: {str(e)}'},
                            status=status.HTTP_400_BAD_REQUEST)




class SetupPINAPIView(APIView):
    """Step 5: Setup transaction PIN"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            pin = request.data.get('pin')

            logger.info(f"[SETUP_PIN] Request for user: {request.user.username}")

            if not pin or len(pin) != 4 or not pin.isdigit():
                return Response({
                    'error': 'PIN must be exactly 4 digits'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Set transaction PIN for the user
            user = request.user
            try:
                if hasattr(user, 'set_transaction_pin'):
                    user.set_transaction_pin(pin)
                elif hasattr(user, 'transaction_pin'):
                    # Set PIN directly if no special method exists
                    from django.contrib.auth.hashers import make_password
                    user.transaction_pin = make_password(pin)
                else:
                    logger.warning(f"[SETUP_PIN] User model has no transaction_pin field")
                user.save()
            except Exception as e:
                logger.warning(f"[SETUP_PIN] Could not save transaction PIN: {e}")
                # For now, just return success even if PIN can't be set
                pass

            logger.info(f"[SETUP_PIN] SUCCESS - PIN set for: {user.username}")

            return Response({
                'success': True,
                'message': 'Transaction PIN set successfully'
            })

        except Exception as e:
            logger.error(f"[SETUP_PIN] ERROR: {str(e)}")
            return Response({
                'error': 'Failed to set PIN due to system error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResendOTPAPIView(APIView):
    """Resend OTP with rate limiting - DATABASE STORAGE"""
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            account_number = request.data.get('account_number')
            phone_number = request.data.get('phone_number')

            logger.info(f"[RESEND_OTP] Request for account: {account_number}")

            # Check if previous OTP exists and implement rate limiting
            try:
                last_otp = OTPVerification.objects.filter(
                    account_number=account_number
                ).order_by('-created_at').first()
                
                if last_otp:
                    time_since_last = (timezone.now() - last_otp.created_at).total_seconds()
                    if time_since_last < 60:  # Wait at least 1 minute
                        wait_time = 60 - int(time_since_last)
                        return Response({
                            'error': f'Please wait {wait_time} seconds before requesting a new OTP'
                        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            except Exception as e:
                logger.warning(f"[RESEND_OTP] Rate limit check failed: {e}")

            # Use the same logic as SendOTPAPIView
            send_otp_view = SendOTPAPIView()
            return send_otp_view.post(request)

        except Exception as e:
            logger.error(f"[RESEND_OTP] ERROR: {str(e)}")
            return Response({
                'error': 'Failed to resend OTP due to system error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DebugOTPStatusAPIView(APIView):
    """Debug endpoint to check OTP status in database"""
    permission_classes = [AllowAny]

    def post(self, request):
        if not getattr(settings, 'DEBUG', False):
            return Response({'error': 'Debug endpoint only available in DEBUG mode'}, status=404)
            
        account_number = request.data.get('account_number')
        if not account_number:
            return Response({'error': 'Account number required'}, status=400)
            
        # Get OTP records
        otps = OTPVerification.objects.filter(account_number=account_number).order_by('-created_at')
        tokens = RegistrationToken.objects.filter(account_number=account_number).order_by('-created_at')
        
        otp_data = []
        for otp in otps[:3]:  # Last 3 OTPs
            otp_data.append({
                'id': otp.id,
                'otp_code': otp.otp_code,
                'created_at': otp.created_at.isoformat(),
                'expires_at': otp.expires_at.isoformat(),
                'attempts': otp.attempts,
                'is_verified': otp.is_verified,
                'is_expired': otp.is_expired,
                'is_valid': otp.is_valid()
            })
        
        token_data = []
        for token in tokens[:3]:  # Last 3 tokens
            token_data.append({
                'id': token.id,
                'token': token.token,
                'created_at': token.created_at.isoformat(),
                'expires_at': token.expires_at.isoformat(),
                'is_used': token.is_used,
                'is_valid': token.is_valid()
            })
        
        return Response({
            'account_number': account_number,
            'otps': otp_data,
            'tokens': token_data,
            'current_time': timezone.now().isoformat()
        })



from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from django.db.models import Value
from decimal import Decimal
from customers.models import Customer
from transactions.models import Memtrans  # Adjust based on your project structure
from .serializers import (
    CustomerDashboardSerializer, 
    WalletDetailsSerializer, 
    CustomerListSerializer,
    MemtransSerializer  # Your existing serializer
)


import time
from datetime import datetime  
# class DashboardView(APIView):
#     """
#     UPDATED: Now includes wallet_account and bank_name in response
#     """
#     permission_classes = [permissions.IsAuthenticated]

#     def get(self, request, *args, **kwargs):
#         customer = getattr(request.user, 'customer', None)
#         if not customer:
#             return Response({"detail": "Customer profile not linked to user."}, status=404)

#         gl_no = (customer.gl_no or '').strip()
#         ac_no = (customer.ac_no or '').strip()
        
#         if not gl_no or not ac_no:
#             # Return basic customer info with wallet fields when gl_no/ac_no missing
#             return Response({
#                 "customer": {
#                     "id": customer.id,
#                     "last_name": (customer.last_name or ""),
#                     "first_name": (getattr(customer, "first_name", "") or ""),
#                     "full_name": f"{getattr(customer, 'first_name', '')} {getattr(customer, 'last_name', '')}".strip(),
#                     "email": customer.email or "",               # 🔥 ADDED
#                     "gl_no": gl_no,
#                     "ac_no": ac_no,
#                     "wallet_account": customer.wallet_account,  # 🔥 ADDED
#                     "bank_name": customer.bank_name,            # 🔥 ADDED
#                     "bank_code": customer.bank_code,            # 🔥 ADDED
#                 },
#                 "balance": 0.0,
#                 "accounts": [],
#                 "transactions": [],
#             })

#         # Get all accounts for this customer (using ac_no as the key)
#         per_accounts = (
#             Memtrans.objects
#             .filter(ac_no=ac_no)  # This is how you calculate balance
#             .values('gl_no', 'ac_no')
#             .annotate(
#                 balance=Coalesce(
#                     Sum('amount'),
#                     Value(0, output_field=DecimalField(max_digits=18, decimal_places=2))
#                 )
#             )
#             .order_by('gl_no')
#         )

#         primary_balance = Decimal('0')
#         for r in per_accounts:
#             if (r['gl_no'] or '').strip() == gl_no:
#                 primary_balance = r['balance'] or Decimal('0')
#                 break

#         recent = (
#             Memtrans.objects
#             .filter(gl_no=gl_no, ac_no=ac_no)  # Same filtering as balance
#             .order_by('-sys_date')[:20]
#         )

#         data = MemtransSerializer(recent, many=True).data

#         # 🔥 FIXED: Now includes wallet_account and bank_name
#         return Response({
#             "customer": {
#                 "id": customer.id,
#                 "last_name": (customer.last_name or ""),
#                 "first_name": (getattr(customer, "first_name", "") or ""),
#                 "full_name": f"{getattr(customer, 'first_name', '')} {getattr(customer, 'last_name', '')}".strip(),
#                 "email": customer.email or "",               # 🔥 ADDED
#                 "gl_no": gl_no,
#                 "ac_no": ac_no,
#                 "wallet_account": customer.wallet_account,  # 🔥 ADDED
#                 "bank_name": customer.bank_name,            # 🔥 ADDED
#                 "bank_code": customer.bank_code,            # 🔥 ADDED
#                 "balance": str(customer.balance),           # 🔥 ADDED
#             },
#             "primary_gl_no": gl_no,
#             "primary_ac_no": ac_no,
#             "balance": float(primary_balance),
#             "accounts": [
#                 {
#                     "gl_no": r["gl_no"],
#                     "ac_no": r["ac_no"],
#                     "balance": float(r["balance"] or 0),
#                 }
#                 for r in per_accounts
#             ],
#             "transactions": data,
#         })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_api_view(request):
    """
    Alternative function-based dashboard API using CustomerDashboardSerializer
    """
    try:
        # Get customer based on authenticated user
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return Response({
                'error': 'Customer not found',
                'success': False
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Use serializer that includes wallet_account and bank_name
        serializer = CustomerDashboardSerializer(customer)
        
        # Build response with all customer data including wallet details
        response_data = {
            'customer': serializer.data,
            'success': True
        }
        
        # Debug: Log what we're returning
        print(f"DEBUG: Dashboard API returning for customer {customer.gl_no}/{customer.ac_no}:")
        print(f"  wallet_account: '{serializer.data.get('wallet_account')}'")
        print(f"  bank_name: '{serializer.data.get('bank_name')}'")
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"DEBUG: Dashboard API error: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalletDetailsAPIView(APIView):
    """
    Dedicated API View for wallet details
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get customer based on authenticated user
            customer = getattr(request.user, 'customer', None)
            if not customer:
                return Response({
                    'error': 'Customer not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Use wallet-specific serializer
            serializer = WalletDetailsSerializer(customer)
            
            print(f"DEBUG: Wallet API returning for customer {customer.gl_no}/{customer.ac_no}:")
            print(f"  wallet_account: '{customer.wallet_account}'")
            print(f"  bank_name: '{customer.bank_name}'")
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"DEBUG: Wallet API error: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_details_by_account_api_view(request):
    """
    Get wallet details by specific gl_no and ac_no
    """
    gl_no = request.GET.get('gl_no')
    ac_no = request.GET.get('ac_no')
    
    if not gl_no or not ac_no:
        return Response({
            'error': 'Both gl_no and ac_no parameters are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Find customer by gl_no and ac_no
        customer = get_object_or_404(Customer, gl_no=gl_no, ac_no=ac_no)
        
        # Use wallet serializer
        serializer = WalletDetailsSerializer(customer)
        
        print(f"DEBUG: By-account API returning for {gl_no}/{ac_no}:")
        print(f"  wallet_account: '{customer.wallet_account}'")
        print(f"  bank_name: '{customer.bank_name}'")
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Customer.DoesNotExist:
        return Response({
            'error': f'Customer with account {gl_no}{ac_no} not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"DEBUG: By-account API error: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def customers_list_api_view(request):
    """
    List customers with wallet information (if needed for admin/testing)
    """
    try:
        # Get all customers or filter as needed
        customers = Customer.objects.all()
        
        # Serialize with wallet information
        serializer = CustomerListSerializer(customers, many=True)
        
        return Response({
            'results': serializer.data,
            'count': len(serializer.data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)











# Django Views - 9PSB API Views (CORRECTED VERSION)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import logging

from .services.ninepsb_service import NinePsbServiceCorrected

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_bank_list(request):
    """
    Retrieve bank list from PsbBank database table
    """
    try:
        from ninepsb.models import PsbBank  # Adjust import path as needed
        
        # Get active banks from database
        banks = PsbBank.objects.filter(active=True).order_by('bank_name')
        
        # Serialize to the format Flutter expects
        bank_list = [
            {
                'bank_code': bank.bank_code,
                'bank_name': bank.bank_name,
                'code': bank.bank_code,      # For backward compatibility
                'name': bank.bank_name,      # For backward compatibility
                'BankCode': bank.bank_code,  # For legacy support
                'BankName': bank.bank_name,  # For legacy support
            }
            for bank in banks
        ]
        
        return JsonResponse({
            'success': True,
            'banks': bank_list,
            'message': f'Retrieved {len(bank_list)} banks from database'
        })
            
    except Exception as e:
        print(f"[ERROR] Failed to get banks from database: {str(e)}")
        
        return JsonResponse({
            'success': False,
            'error': str(e),
            'banks': [],
            'message': 'Failed to retrieve banks'
        }, status=500)

from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

  # adjust import path as needed


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_account(request):
    """
    Verify bank account details using 9PSB service
    """
    try:
        account_number = request.data.get('account_number', '').strip()
        bank_code = request.data.get('bank_code', '').strip()

        # 1️⃣ Validate inputs
        if not account_number or not bank_code:
            return JsonResponse({
                'success': False,
                'error': 'Account number and bank code are required',
                'message': 'Missing required parameters'
            }, status=400)

        # 2️⃣ Validate credentials
        if not settings.PSB_PUBLIC_KEY or not settings.PSB_PRIVATE_KEY:
            return JsonResponse({
                'success': False,
                'error': 'PSB credentials not configured',
                'message': '9PSB service credentials missing'
            }, status=500)

        # 3️⃣ Initialize service
        service = NinePsbServiceCorrected(
            public_key=settings.PSB_PUBLIC_KEY,
            private_key=settings.PSB_PRIVATE_KEY
        )

        # 4️⃣ Call correct method
        if hasattr(service, 'account_enquiry'):
            result = service.account_enquiry(account_number, bank_code)
        elif hasattr(service, 'name_enquiry'):
            result = service.name_enquiry(account_number, bank_code)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Account verification method not found',
                'message': 'Service method not available'
            }, status=500)

        print(f"[DEBUG] 9PSB Account verification response: {result}")

        if not result:
            return JsonResponse({
                'success': False,
                'error': 'No response from verification service',
                'message': 'No response from account verification'
            }, status=500)

        # 5️⃣ Parse and normalize response
        if isinstance(result, dict):
            code = result.get('code', '99')

            # ✅ Successful verification
            if code == '00' and result.get('success', True):
                # ✅ Correctly extract nested structure
                # ✅ Handle both "account" and "customer.account" response formats
                account_info = result.get('account') or result.get('customer', {}).get('account', {})
                account_name = (account_info or {}).get('name', '').strip()

                # Handle missing or blank names
                if not account_name:
                    if 'sandbox' in settings.PSB_PUBLIC_KEY.lower() or 'test' in settings.PSB_PUBLIC_KEY.lower():
                        account_name = 'Sandbox Account (Verified)'
                    else:
                        account_name = 'Unknown Account'


                # Handle missing or blank names
                if not account_name:
                    if 'sandbox' in settings.PSB_PUBLIC_KEY.lower() or 'test' in settings.PSB_PUBLIC_KEY.lower():
                        account_name = 'Sandbox Account (Verified)'
                    else:
                        account_name = 'Unknown Account'

                # ✅ Return Flutter-friendly structure
                return JsonResponse({
                    'success': True,
                    'code': '00',
                    'message': result.get('message', 'Account verification successful'),
                    'customer': {
                        'account': {
                            'accountName': account_name,
                            'accountNumber': account_number,
                            'bankCode': bank_code
                        }
                    }
                })

            # ❌ Error responses from 9PSB
            else:
                error_messages = {
                    '07': 'Invalid account number',
                    '03': 'Invalid sender account',
                    'S1': 'Authentication failed with 9PSB',
                    '99': 'Banking service temporarily unavailable',
                    '01': 'Invalid request format',
                    '25': 'Account not found',
                }

                error_message = error_messages.get(code, result.get('error', 'Account verification failed'))

                return JsonResponse({
                    'success': False,
                    'code': code,
                    'error': error_message,
                    'message': result.get('message', 'Account verification failed')
                }, status=400)

        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid response format from verification service',
                'message': 'Unexpected response format'
            }, status=500)

    except Exception as e:
        import traceback
        print(f"[ERROR] Account verification error: {str(e)}")
        print(traceback.format_exc())

        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Internal server error during account verification'
        }, status=500)


# Add this method to your NinePsbServiceCorrected class or fix the existing one
def account_enquiry(self, account_number, bank_code):
    """
    Verify account details - implement this method in your service class
    """
    # This is a placeholder - implement based on your 9PSB service structure
    try:
        # Your 9PSB account verification logic here
        response = self.make_api_call('account_enquiry', {
            'account_number': account_number,
            'bank_code': bank_code
        })
        return response
    except Exception as e:
        print(f"Account enquiry error: {e}")
        return {'code': '99', 'message': str(e)}

import time
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import time

# Assumes these are available in your project the same way your other view used them:
# from .utils import _balance, _gen_trx_no, normalize_account, _user_customer  # if you have them
# from .models import Customer, Memtrans
# If your project places them elsewhere, adjust imports accordingly.

from datetime import date
from django.utils import timezone
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from transactions.models import Memtrans
from company.models import Company
from customers.models import Customer
from company.models import Branch


from datetime import date
from django.utils import timezone
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from transactions.models import Memtrans
from company.models import Company
from customers.models import Customer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_transfer(request):
    """
    Initiate fund transfer using the company Mobile Teller account.
    Uses the branch automatically linked to the logged-in customer.
    """
    try:
        print(f"[DEBUG] Transfer request data: {request.data}")

        # --- Parse request fields ---
        from_account = request.data.get('sender_account_number', '').strip()
        to_account = request.data.get('dest_account_number', '').strip()
        amount = float(request.data.get('amount', 0))
        narration = request.data.get('narration', 'Fund Transfer').strip()

        if not from_account or not to_account or not amount:
            return JsonResponse({
                'success': False,
                'error': 'Missing sender, receiver, or amount'
            }, status=400)

        # --- Get logged-in user & linked customer ---
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return JsonResponse({'success': False, 'error': 'Customer profile not linked to user.'}, status=404)

        branch = getattr(customer, 'branch', None)
        if not branch:
            return JsonResponse({'success': False, 'error': 'Branch not linked to customer.'}, status=404)

        today = date.today()
        trx_no = f"TRX{timezone.now().strftime('%Y%m%d%H%M%S')}"

        # --- Get sender & receiver company ---
        sender_company = Company.objects.filter(float_account_number=from_account).first()
        receiver_company = Company.objects.filter(float_account_number=to_account).first()

        if not sender_company:
            return JsonResponse({'success': False, 'error': 'Sender company not found'}, status=404)

        if not receiver_company:
            print("⚠️ Receiver company not found — using sender company for self-transfer.")
            receiver_company = sender_company

        # --- Sender details (from user) ---
        src_gl = request.user.gl_no or "20101"
        src_ac = request.user.ac_no or from_account[-5:]

        # --- Receiver details ---
        dst_gl = receiver_company.mobile_teller_gl_no or "20101"
        dst_ac = receiver_company.mobile_teller_ac_no or to_account[-5:]

        # ✅ CREDIT receiver company (+)
        Memtrans.objects.create(
            branch=branch,
            cust_branch=branch,
            gl_no=dst_gl,
            ac_no=dst_ac,
            trx_no=trx_no,
            ses_date=today,
            app_date=today,
            sys_date=timezone.now(),
            amount=amount,
            description=narration,
            error="A",
            type="T",
            account_type="C",
            user=request.user,
            trx_type="TRANSFER",
        )

        # ✅ DEBIT sender customer (-)
        Memtrans.objects.create(
            branch=branch,
            cust_branch=branch,
            gl_no=src_gl,
            ac_no=src_ac,
            trx_no=trx_no,
            ses_date=today,
            app_date=today,
            sys_date=timezone.now(),
            amount=-amount,
            description=f"Transfer via Mobile Teller: {narration}",
            error="A",
            type="T",
            account_type="C",
            user=request.user,
            trx_type="TRANSFER",
        )

        # --- FLOAT COMPANY TRANSACTIONS ---
        float_gl = receiver_company.float_gl_no or "20111"
        float_ac = receiver_company.float_ac_no or to_account[-5:]

        # 🔹 CREDIT float (+)
        Memtrans.objects.create(
            branch=branch,
            cust_branch=branch,
            gl_no=float_gl,
            ac_no=float_ac,
            trx_no=trx_no,
            ses_date=today,
            app_date=today,
            sys_date=timezone.now(),
            amount=amount,
            description=f"Float Credit for {narration}",
            error="A",
            type="T",
            account_type="C",
            user=request.user,
            trx_type="FLOAT_TRANSFER",
        )

        # 🔹 DEBIT float (-)
        # Memtrans.objects.create(
        #     branch=branch,
        #     cust_branch=branch,
        #     gl_no=float_gl,
        #     ac_no=float_ac,
        #     trx_no=trx_no,
        #     ses_date=today,
        #     app_date=today,
        #     sys_date=timezone.now(),
        #     amount=-amount,
        #     description=f"Float Debit for {narration}",
        #     error="A",
        #     type="T",
        #     account_type="C",
        #     user=request.user,
        #     trx_type="FLOAT_TRANSFER",
        # )

        print("✅ Transfer completed successfully using Mobile Teller GL and AC.")

        return JsonResponse({
            'success': True,
            'message': 'Transfer completed successfully.',
            'trx_no': trx_no,
            'sender_gl': src_gl,
            'sender_ac': src_ac,
            'receiver_company': receiver_company.company_name,
            'receiver_gl': dst_gl,
            'receiver_ac': dst_ac,
            'float_gl': float_gl,
            'float_ac': float_ac,
            'branch': branch.branch_name if branch else None,
        }, status=200)

    except Exception as e:
        print(f"[ERROR] Transfer failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ninepsb_health_check(request):
    """Health check endpoint for 9PSB service"""
    try:
        service = NinePsbServiceCorrected(
                    public_key=settings.PSB_PUBLIC_KEY,
                    private_key=settings.PSB_PRIVATE_KEY
                )
        result = service.health_check()
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
    except Exception as e:
        logger.error(f"9PSB Health check view error: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': f'Health check failed: {str(e)}',
            'base_url': 'Unknown',
            'authenticated': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)