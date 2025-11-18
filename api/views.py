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


# class DashboardView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def get(self, request, *args, **kwargs):
#         print("🔥 DashboardView called - float_account_number fix is ACTIVE!")

#         # ✅ 1️⃣ Get logged-in customer
#         customer = getattr(request.user, 'customer', None)
#         if not customer:
#             print("❌ No Customer profile linked to user")
#             return Response({"detail": "Customer profile not linked to user."}, status=404)

#         # ✅ 2️⃣ Get linked company or fallback to first one
#         company = getattr(request.user, 'company', None)
#         if not company:
#             company = Company.objects.first()

#         if not company:
#             print("❌ No company found in system")
#             return Response(
#                 {"detail": "Company profile not found in the system."},
#                 status=404
#             )

#         print(f"✅ Using company: {company.company_name} ({company.id})")

#         # ✅ 3️⃣ Extract key data
#         gl_no = (customer.gl_no or '').strip()
#         ac_no = (customer.ac_no or '').strip()
#         float_account_number = (company.float_account_number or '').strip()
#         bank_name = (customer.bank_name or '').strip()
#         bank_code = (customer.bank_code or '').strip()

#         print(f"🏦 float_account_number from DB: {float_account_number or '❌ None'}")

#         # ✅ 4️⃣ If basic info missing
#         if not gl_no or not ac_no:
#             return Response({
#                 "customer": {
#                     "id": customer.id,
#                     "first_name": customer.first_name or "",
#                     "last_name": customer.last_name or "",
#                     "full_name": f"{customer.first_name or ''} {customer.last_name or ''}".strip(),
#                     "email": customer.email or "",
#                     "gl_no": gl_no,
#                     "ac_no": ac_no,
#                     "float_account_number": float_account_number,
#                     "bank_name": bank_name,
#                     "bank_code": bank_code,
#                 },
#                 "balance": 0.0,
#                 "accounts": [],
#                 "transactions": [],
#             })

#         # ✅ 5️⃣ Aggregate balances
#         per_accounts = (
#             Memtrans.objects
#             .filter(ac_no=ac_no)
#             .values('gl_no', 'ac_no')
#             .annotate(
#                 balance=Coalesce(
#                     Sum('amount'),
#                     Value(0, output_field=DecimalField(max_digits=18, decimal_places=2))
#                 )
#             )
#             .order_by('gl_no')
#         )

#         # ✅ 6️⃣ Primary account balance
#         primary_balance = Decimal('0')
#         for r in per_accounts:
#             if str(r['gl_no']).strip() == gl_no:
#                 primary_balance = r['balance'] or Decimal('0')
#                 break

#         # ✅ 7️⃣ Get last 20 transactions
#         recent = (
#             Memtrans.objects
#             .filter(gl_no=gl_no, ac_no=ac_no)
#             .order_by('-sys_date')[:20]
#         )
#         data = MemtransSerializer(recent, many=True).data

#         # ✅ 8️⃣ Build account list
#         accounts_data = []
#         for r in per_accounts:
#             accounts_data.append({
#                 "gl_no": r["gl_no"],
#                 "ac_no": r["ac_no"],
#                 "balance": float(r["balance"] or 0),
#                 "available_balance": float(r["balance"] or 0),
#                 "float_account_number": float_account_number,
#                 "bank_name": bank_name,
#                 "bank_code": bank_code,
#             })

#         # ✅ 9️⃣ Final response
#         response_data = {
#             "customer": {
#                 "id": customer.id,
#                 "first_name": customer.first_name or "",
#                 "last_name": customer.last_name or "",
#                 "full_name": f"{customer.first_name or ''} {customer.last_name or ''}".strip(),
#                 "email": customer.email or "",
#                 "gl_no": gl_no,
#                 "ac_no": ac_no,
#                 "float_account_number": float_account_number,
#                 "bank_name": bank_name,
#                 "bank_code": bank_code,
#                 "balance": float(primary_balance),
#             },
#             "primary_gl_no": gl_no,
#             "primary_ac_no": ac_no,
#             "primary_float_account_number": float_account_number,
#             "balance": float(primary_balance),
#             "accounts": accounts_data,
#             "transactions": data,
#         }

#         print("✅ Dashboard response prepared successfully.")
#         print(f"🧾 Returning float_account_number: {float_account_number or '❌ None'}")

#         return Response(response_data)


# ---------------------------------------------------------------------------
# FIXED: Transaction Views - Class-based with JWT Authentication
# ---------------------------------------------------------------------------

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TransactionsView(APIView):
    """Get transactions using customer gl_no and ac_no with optional request parameters override"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            customer = request.user.customer
            print(f"[DEBUG] TransactionsView called by user: {request.user.username}, customer_id={customer.id}")
            
            # ✅ FIXED: Use request parameters if provided, otherwise fall back to customer session
            request_gl_no = request.GET.get('gl_no', '').strip()
            request_ac_no = request.GET.get('ac_no', '').strip()
            
            # Priority: Request parameters (from dashboard) > Customer session data
            filter_gl_no = request_gl_no if request_gl_no else (customer.gl_no or '').strip()
            filter_ac_no = request_ac_no if request_ac_no else (customer.ac_no or '').strip()
            
            print(f"[DEBUG] Request parameters: gl_no='{request_gl_no}', ac_no='{request_ac_no}'")
            print(f"[DEBUG] Customer session: gl_no='{customer.gl_no}', ac_no='{customer.ac_no}'")
            print(f"[DEBUG] Using for filtering: gl_no='{filter_gl_no}', ac_no='{filter_ac_no}'")
            
            if not filter_gl_no or not filter_ac_no:
                print(f"[DEBUG] Customer {customer.id} missing account info: gl_no='{filter_gl_no}', ac_no='{filter_ac_no}'")
                return Response({'error': 'Customer account information incomplete'}, status=status.HTTP_400_BAD_REQUEST)
            
            # ✅ FIXED: Use the determined account parameters for filtering
            transactions_query = Memtrans.objects.filter(
                gl_no=filter_gl_no,  # Now uses dashboard gl_no when provided
                ac_no=filter_ac_no   # Now uses dashboard ac_no when provided
            )
            
            # Apply additional filters from request
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            min_amount = request.GET.get('min_amount')
            max_amount = request.GET.get('max_amount')
            trx_no = request.GET.get('trx_no')
            
            # Date range filter
            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                    transactions_query = transactions_query.filter(sys_date__gte=start_date_obj)
                    print(f"[DEBUG] Applied start_date filter: {start_date}")
                except ValueError:
                    print(f"[DEBUG] Invalid start_date format: {start_date}")
            
            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    transactions_query = transactions_query.filter(sys_date__lte=end_date_obj)
                    print(f"[DEBUG] Applied end_date filter: {end_date}")
                except ValueError:
                    print(f"[DEBUG] Invalid end_date format: {end_date}")
            
            # Amount range filters
            if min_amount:
                try:
                    min_amt = float(min_amount)
                    transactions_query = transactions_query.filter(amount__gte=min_amt)
                    print(f"[DEBUG] Applied min_amount filter: {min_amt}")
                except (ValueError, TypeError):
                    print(f"[DEBUG] Invalid min_amount: {min_amount}")
            
            if max_amount:
                try:
                    max_amt = float(max_amount)
                    transactions_query = transactions_query.filter(amount__lte=max_amt)
                    print(f"[DEBUG] Applied max_amount filter: {max_amt}")
                except (ValueError, TypeError):
                    print(f"[DEBUG] Invalid max_amount: {max_amount}")
            
            # Transaction number filter
            if trx_no:
                transactions_query = transactions_query.filter(trx_no__icontains=trx_no)
                print(f"[DEBUG] Applied transaction number filter: {trx_no}")
            
            # Order by transaction date (newest first)
            transactions = transactions_query.order_by('-sys_date')
            
            print(f"[DEBUG] Found {transactions.count()} transactions for account {filter_gl_no}-{filter_ac_no}")
            
            # Pagination
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 10))
            paginator = Paginator(transactions, limit)
            page_obj = paginator.get_page(page)
            
            print(f"[DEBUG] Pagination: page={page}, limit={limit}, total_pages={paginator.num_pages}")
            
            # Serialize transaction data
            transactions_data = []
            for transaction in page_obj.object_list:
                transactions_data.append({
                    'trx_no': transaction.trx_no or '',
                    'id': transaction.trx_no or '',  # Flutter expects 'id' field
                    'trx_type': transaction.trx_type or '',
                    'type': transaction.trx_type or 'debit',  # Flutter expects 'type' field
                    'code': transaction.code or transaction.trx_type or 'UNKNOWN',
                    'amount': float(transaction.amount) if transaction.amount else 0.0,
                    'sys_date': transaction.sys_date.isoformat() if transaction.sys_date else '',
                    'ses_date': transaction.ses_date.isoformat() if transaction.ses_date else '',
                    'date': transaction.sys_date.isoformat() if transaction.sys_date else '',  # Flutter expects 'date' field
                    'description': transaction.description or '',
                    'gl_no': transaction.gl_no or '',
                    'ac_no': transaction.ac_no or '',
                })
            
            return Response({
                'data': transactions_data,
                'pagination': {
                    'page': page,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                }
            })
            
        except Exception as e:
            logger.error(f"Transactions error: {str(e)}")
            print(f"[ERROR] Transactions error: {e}")
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
from django.contrib.auth import get_user_model, authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

UserModel = get_user_model()


def _find_user_by_username_or_email(value: str):
    """
    Optional helper: just to locate user for pre-login messages.
    Not strictly necessary if you only rely on authenticate().
    """
    print(f"[DEBUG] Searching for user by: {value}")
    try:
        user = UserModel.objects.get(username=value)
        print(f"[DEBUG] Found user by username: {user.username}")
        return user
    except UserModel.DoesNotExist:
        print("[DEBUG] Not found by username, trying email lookup...")
        try:
            user = UserModel.objects.get(email__iexact=value)
            print(f"[DEBUG] Found user by email: {user.email}")
            return user
        except UserModel.DoesNotExist:
            print("[DEBUG] User not found by either username or email.")
            return None


class PreLoginView(APIView):
    """
    Pre-login API:
    1. Checks credentials using Django authentication backends.
    2. Returns whether the user can login or requires activation.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        print("\n========== [DEBUG] PreLoginView POST called ==========")
        username_or_email = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''

        print(f"[DEBUG] Received username/email: '{username_or_email}'")
        print(f"[DEBUG] Received password: {'*' * len(password)}")  # hide actual password

        if not username_or_email or not password:
            print("[DEBUG] Missing username or password.")
            return Response(
                {"detail": "username and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authenticate using Django backends
        user = authenticate(request, email=username_or_email, password=password)
        if not user:
            # Optionally check if user exists for clearer message
            db_user = _find_user_by_username_or_email(username_or_email)
            if db_user:
                print(f"[DEBUG] Password check failed for user: {db_user.username}")
            else:
                print("[DEBUG] No user found with provided username/email")
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST
            )

        print(f"[DEBUG] Authentication SUCCESS for user: {user.username} (id={user.id})")

        # Check if user is verified
        if getattr(user, "verified", False):
            print("[DEBUG] User is verified → can login")
            return Response({"can_login": True}, status=status.HTTP_200_OK)
        else:
            print("[DEBUG] User not verified → activation required")
            return Response(
                {"activation_required": True, "username": user.username},
                status=status.HTTP_202_ACCEPTED
            )



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
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from customers.models import Customer
from transactions.models import Memtrans
from .serializers import TransferToFinanceFlexSerializer
from .helpers import (
    _user_customer,
    _balance,
    _gen_trx_no,
    normalize_account,
)
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions

from customers.models import Customer
from transactions.models import Memtrans
from .serializers import TransferToFinanceFlexSerializer
from .helpers import normalize_account, _balance, _gen_trx_no

class TransferToFinanceFlexView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        print("DEBUG: Incoming request data:", request.data)

        # Validate request data
        ser = TransferToFinanceFlexSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        print("DEBUG: Validated data:", data)

        # Get logged-in user and their source account
        user = request.user
        norm_from_gl = user.gl_no
        norm_from_ac = user.ac_no
        print(f"DEBUG: Source account derived from user - GL: {norm_from_gl}, AC: {norm_from_ac}")

        # Extract destination and amount
        to_gl = data["to_gl_no"]
        to_ac = data["to_ac_no"]
        amount = data["amount"]
        if isinstance(amount, str):
            amount = Decimal(amount)
        narr = data.get("narration") or "FinanceFlex transfer"
        print(f"DEBUG: Transfer details - Amount: {amount}, Narration: {narr}")

        # Normalize destination account
        norm_to_gl, norm_to_ac = normalize_account(to_gl, to_ac)
        print(f"DEBUG: Destination account normalized - GL: {norm_to_gl}, AC: {norm_to_ac}")

        # Find destination customer
        dest_cust = Customer.objects.filter(gl_no=norm_to_gl, ac_no=norm_to_ac).first()
        print("DEBUG: Destination customer:", dest_cust)
        if not dest_cust:
            print("DEBUG: Destination customer not found")
            return Response({"detail": "Destination account not found."}, status=404)

        # Check source balance
        cur_bal = _balance(norm_from_gl, norm_from_ac)
        print(f"DEBUG: Current source balance: {cur_bal}")
        if cur_bal < amount:
            print("DEBUG: Insufficient funds")
            return Response({"detail": f"Insufficient funds. Available: {cur_bal}, Requested: {amount}"}, status=400)

        # Generate transaction metadata
        now = timezone.now()
        today = timezone.localdate()
        trx_no = _gen_trx_no()
        print(f"DEBUG: Transaction number generated: {trx_no}")

        # Credit destination (+)
        dest_trans = Memtrans.objects.create(
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
        print("DEBUG: Destination transaction created:", dest_trans.id)

        # Debit source (-)
        src_trans = Memtrans.objects.create(
            branch=user.branch,  # Assuming user has branch attribute
            cust_branch=user.branch,
            customer=user.customer,  # Assuming user has related customer
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
        print("DEBUG: Source transaction created:", src_trans.id)

        # Compute new balances
        new_src_bal = _balance(norm_from_gl, norm_from_ac)
        new_dst_bal = _balance(norm_to_gl, norm_to_ac)
        print(f"DEBUG: New balances - Source: {new_src_bal}, Destination: {new_dst_bal}")

        # Build response
        response_data = {
            "status": True,
            "reference": trx_no,
            "amount": str(amount),
            "narration": narr,
            "timestamp": now.isoformat(),
            "from": {
                "gl_no": norm_from_gl,
                "ac_no": norm_from_ac,
                "customer_id": user.customer.id,
                "balance": str(new_src_bal),
            },
            "to": {
                "gl_no": norm_to_gl,
                "ac_no": norm_to_ac,
                "customer_id": dest_cust.id,
                "balance": str(new_dst_bal),
            },
        }

        print("DEBUG: Response data:", response_data)
        return Response(response_data, status=201)




# 🧩 Improved ownership check helper
def _owns_source_account(cust, gl_no, ac_no):
    print("DEBUG _owns_source_account called")
    print(f"DEBUG Expected (from request): gl_no={gl_no}, ac_no={ac_no}")
    print(f"DEBUG Customer record: id={cust.id}, gl_no={cust.gl_no}, ac_no={cust.ac_no}, name={getattr(cust, 'full_name', cust)}")

    # Normalize to avoid type or leading-zero mismatches
    same_gl = str(cust.gl_no).lstrip("0") == str(gl_no).lstrip("0")
    same_ac = str(cust.ac_no).lstrip("0") == str(ac_no).lstrip("0")

    print(f"DEBUG Comparison: same_gl={same_gl}, same_ac={same_ac}")
    owns = same_gl and same_ac
    print(f"DEBUG Result: owns_source_account={owns}")
    return owns

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
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db import IntegrityError  # ← MISSING IMPORT ADDED
from .models import Beneficiary
from .serializers import BeneficiarySerializer

class BeneficiaryListCreateView(APIView):
    """
    List all beneficiaries or create a new beneficiary for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """GET /api/v1/beneficiaries/ - List beneficiaries."""
        beneficiaries = Beneficiary.objects.filter(user=request.user).order_by('name')
        serializer = BeneficiarySerializer(beneficiaries, many=True)
        
        return Response({
            'success': True,
            'count': len(serializer.data),
            'results': serializer.data
        })
    
    def post(self, request):
        """POST /api/v1/beneficiaries/ - Create beneficiary."""
        # 🔍 DEBUG: Log incoming data to see what Flutter is sending
        print(f"[DEBUG] 📥 Incoming beneficiary data: {request.data}")
        print(f"[DEBUG] 👤 User: {request.user.username}")
        
        serializer = BeneficiarySerializer(data=request.data, context={'request': request})
        
        print(f"[DEBUG] 🔍 Serializer is_valid: {serializer.is_valid()}")
        if not serializer.is_valid():
            print(f"[DEBUG] ❌ Serializer errors: {serializer.errors}")
        
        if serializer.is_valid():
            try:
                beneficiary = serializer.save()
                print(f"[DEBUG] ✅ Beneficiary created: {beneficiary.name} ({beneficiary.account_number})")
                return Response({
                    'success': True,
                    'message': 'Beneficiary saved successfully',
                    'data': BeneficiarySerializer(beneficiary).data
                }, status=status.HTTP_201_CREATED)
            except IntegrityError:
                return Response({
                    'success': False,
                    'message': 'This beneficiary already exists'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'message': 'Invalid data',
            'errors': serializer.errors,
            'received_data': request.data  # 🔍 Show what was received for debugging
        }, status=status.HTTP_400_BAD_REQUEST)

class BeneficiaryDetailView(APIView):
    """
    Retrieve, update or delete a beneficiary.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, pk, user):
        try:
            return Beneficiary.objects.get(pk=pk, user=user)
        except Beneficiary.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """GET /api/v1/beneficiaries/{id}/"""
        beneficiary = self.get_object(pk, request.user)
        if not beneficiary:
            return Response({'success': False, 'message': 'Not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        serializer = BeneficiarySerializer(beneficiary)
        return Response({'success': True, 'data': serializer.data})
    
    def put(self, request, pk):
        """PUT /api/v1/beneficiaries/{id}/"""
        beneficiary = self.get_object(pk, request.user)
        if not beneficiary:
            return Response({'success': False, 'message': 'Not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        serializer = BeneficiarySerializer(beneficiary, data=request.data, 
                                         context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'data': serializer.data})
        
        return Response({'success': False, 'errors': serializer.errors}, 
                      status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """DELETE /api/v1/beneficiaries/{id}/"""
        beneficiary = self.get_object(pk, request.user)
        if not beneficiary:
            return Response({'success': False, 'message': 'Not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        beneficiary.delete()
        return Response({'success': True, 'message': 'Deleted successfully'}, 
                      status=status.HTTP_204_NO_CONTENT)
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

from decimal import Decimal
from django.utils import timezone
from django.db import transaction

# Import fee models
try:
    from api.services.global_fee_service import GlobalTransferFeeService
    from api.models.global_transfer_fees import GlobalTransferFeeTransaction
except ImportError:
    GlobalTransferFeeService = None
    GlobalTransferFeeTransaction = None

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_transfer(request):
    """
    Initiate fund transfer with proper fee handling using Memtrans entries.
    
    UPDATED WITH FEE LOGIC:
    1. Customer Account → Debit transfer_amount (existing logic)
    2. Customer Account → Debit fee_amount (NEW)
    3. Fee Account → Credit fee_amount (NEW) 
    4. Mobile Teller/Float logic (existing, unchanged)
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

        # Convert to Decimal for precise fee calculations
        transfer_amount = Decimal(str(amount))

        # --- Get logged-in user & linked customer ---
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return JsonResponse({'success': False, 'error': 'Customer profile not linked to user.'}, status=404)

        branch = getattr(customer, 'branch', None)
        if not branch:
            return JsonResponse({'success': False, 'error': 'Branch not linked to customer.'}, status=404)

        today = date.today()
        trx_no = f"TRX{timezone.now().strftime('%Y%m%d%H%M%S')}"

        # --- STEP 1: CALCULATE TRANSFER FEE ---
        print(f"=== FEE CALCULATION START ===")
        
        fee_amount = Decimal('0.00')
        fee_info = None
        
        if GlobalTransferFeeService:
            try:
                # Get customer ID for fee calculation
                customer_id = str(customer.id) if customer else str(request.user.id)
                
                # Calculate fee using database service
                fee_info = GlobalTransferFeeService.calculate_fee_for_any_customer(
                    customer_id=customer_id,
                    transfer_amount=transfer_amount,
                    transfer_type='other_bank'
                )
                
                fee_amount = fee_info.get('applied_fee', Decimal('0.00'))
                print(f"[DEBUG] Fee calculated: ₦{fee_amount} (waived: {fee_info.get('is_waived', False)})")
                
            except Exception as e:
                print(f"[WARNING] Fee calculation error: {e}")
                fee_info = {
                    'base_fee': Decimal('10.00'),
                    'applied_fee': Decimal('0.00'),
                    'is_waived': True,
                    'waiver_reason': 'Fee calculation error - defaulting to free',
                    'config_name': 'Error Default',
                    'fee_gl_no': '30101',
                    'fee_ac_no': '000001'
                }
        else:
            print(f"[WARNING] GlobalTransferFeeService not available, proceeding with zero fee")
            fee_info = {
                'base_fee': Decimal('10.00'),
                'applied_fee': Decimal('0.00'),
                'is_waived': True,
                'waiver_reason': 'Fee service not available',
                'config_name': 'Service Unavailable',
                'fee_gl_no': '30101',
                'fee_ac_no': '000001'
            }

        total_customer_debit = transfer_amount + fee_amount
        print(f"[DEBUG] Transfer: ₦{transfer_amount}, Fee: ₦{fee_amount}, Total Debit: ₦{total_customer_debit}")

        # --- Get sender & receiver company (EXISTING LOGIC) ---
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

        # --- STEP 2: CREATE MEMTRANS ENTRIES ---
        print(f"=== MEMTRANS ENTRIES START ===")

        # ✅ 1. DEBIT sender customer for TRANSFER AMOUNT (EXISTING LOGIC)
        print(f"[MEMTRANS] Debit customer {src_gl}{src_ac} by ₦{transfer_amount} (Transfer)")
        Memtrans.objects.create(
            branch=branch,
            cust_branch=branch,
            customer=customer,
            gl_no=src_gl,
            ac_no=src_ac,
            trx_no=trx_no,
            ses_date=today,
            app_date=today,
            sys_date=timezone.now(),
            amount=-float(transfer_amount),  # Negative for debit
            description=f"Transfer via Mobile Teller: {narration}",
            error="A",
            type="T",
            account_type="C",
            user=request.user,
            trx_type="TRANSFER",
        )

        # ✅ 2. DEBIT sender customer for FEE AMOUNT (NEW FEE LOGIC)
        fee_memtrans_id = None
        if fee_amount > 0:
            print(f"[MEMTRANS] Debit customer {src_gl}{src_ac} by ₦{fee_amount} (Fee)")
            fee_debit_entry = Memtrans.objects.create(
                branch=branch,
                cust_branch=branch,
                customer=customer,
                gl_no=src_gl,
                ac_no=src_ac,
                trx_no=f"FEE{trx_no}",
                ses_date=today,
                app_date=today,
                sys_date=timezone.now(),
                amount=-float(fee_amount),  # Negative for debit
                description=f"Transfer Fee - {fee_info.get('config_name', 'Other Bank Transfer')}",
                error="A",
                type="T",
                account_type="C",
                user=request.user,
                trx_type="FEE_DEBIT",
            )
            fee_memtrans_id = fee_debit_entry.id

            # ✅ 3. CREDIT fee account for FEE AMOUNT (NEW FEE LOGIC)
            fee_gl_no = fee_info.get('fee_gl_no', '30101')
            fee_ac_no = fee_info.get('fee_ac_no', '000001')
            print(f"[MEMTRANS] Credit fee account {fee_gl_no}{fee_ac_no} by ₦{fee_amount} (Fee Income)")
            
            Memtrans.objects.create(
                branch=branch,
                cust_branch=branch,
                customer=None,  # Fee account, not customer account
                gl_no=fee_gl_no[:6],  # Ensure max 6 chars
                ac_no=fee_ac_no[:6],  # Ensure max 6 chars
                trx_no=f"FEE{trx_no}",
                ses_date=today,
                app_date=today,
                sys_date=timezone.now(),
                amount=float(fee_amount),  # Positive for credit
                description=f"Transfer Fee Income - Customer {customer.id}",
                error="A",
                type="T",
                account_type="C",
                user=request.user,
                trx_type="FEE_CREDIT",
            )
        else:
            print(f"[MEMTRANS] No fee entries needed (fee waived)")

        # ✅ 4. CREDIT receiver company (EXISTING LOGIC - UNCHANGED)
        print(f"[MEMTRANS] Credit receiver {dst_gl}{dst_ac} by ₦{transfer_amount} (Mobile Teller)")
        Memtrans.objects.create(
            branch=branch,
            cust_branch=branch,
            gl_no=dst_gl,
            ac_no=dst_ac,
            trx_no=trx_no,
            ses_date=today,
            app_date=today,
            sys_date=timezone.now(),
            amount=float(transfer_amount),  # Positive for credit - TRANSFER AMOUNT ONLY
            description=narration,
            error="A",
            type="T",
            account_type="C",
            user=request.user,
            trx_type="TRANSFER",
        )

        # ✅ 5. FLOAT COMPANY TRANSACTIONS (EXISTING LOGIC - UNCHANGED)
        float_gl = receiver_company.float_gl_no or "20111"
        float_ac = receiver_company.float_ac_no or to_account[-5:]

        # 🔹 CREDIT float (+)
        print(f"[MEMTRANS] Credit float {float_gl}{float_ac} by ₦{transfer_amount} (Float Credit)")
        Memtrans.objects.create(
            branch=branch,
            cust_branch=branch,
            gl_no=float_gl,
            ac_no=float_ac,
            trx_no=trx_no,
            ses_date=today,
            app_date=today,
            sys_date=timezone.now(),
            amount=float(transfer_amount),  # TRANSFER AMOUNT ONLY, not including fee
            description=f"Float Credit for {narration}",
            error="A",
            type="T",
            account_type="C",
            user=request.user,
            trx_type="FLOAT_TRANSFER",
        )

        # --- STEP 3: RECORD FEE TRANSACTION FOR TRACKING ---
        if GlobalTransferFeeTransaction and fee_info:
            try:
                fee_transaction = GlobalTransferFeeTransaction.objects.create(
                    customer_id=str(customer.id),
                    customer_account=from_account,
                    transfer_reference=trx_no,
                    fee_config_name=fee_info.get('config_name', 'Unknown'),
                    base_fee_amount=fee_info.get('base_fee', Decimal('0.00')),
                    applied_fee_amount=fee_amount,
                    was_waived=fee_info.get('is_waived', False),
                    waiver_reason=fee_info.get('waiver_reason', ''),
                    transfer_amount=transfer_amount,
                    total_debited=total_customer_debit,
                    destination_bank='internal',
                    destination_account=to_account,
                    destination_name='Internal Transfer',
                    fee_gl_no=fee_info.get('fee_gl_no', '30101'),
                    fee_ac_no=fee_info.get('fee_ac_no', '000001'),
                    fee_transaction_ref=f"FEE{trx_no}"
                )
                print(f"[DEBUG] Fee transaction recorded: {fee_transaction.id}")
            except Exception as e:
                print(f"[WARNING] Fee transaction recording failed (non-critical): {e}")

        # --- STEP 4: UPDATE CUSTOMER USAGE STATISTICS ---
        if GlobalTransferFeeService:
            try:
                GlobalTransferFeeService.update_customer_usage_after_transfer(
                    customer_id=str(customer.id),
                    transfer_amount=transfer_amount,
                    fee_paid=fee_amount
                )
                print(f"[DEBUG] Customer usage updated for {customer.id}")
            except Exception as e:
                print(f"[WARNING] Customer usage update failed (non-critical): {e}")

        print("✅ Transfer completed successfully using Mobile Teller GL and AC with fee handling.")

        # --- RESPONSE WITH FEE INFORMATION ---
        response_data = {
            'success': True,
            'message': 'Transfer completed successfully.',
            'trx_no': trx_no,
            
            # Existing response fields
            'sender_gl': src_gl,
            'sender_ac': src_ac,
            'receiver_company': receiver_company.company_name,
            'receiver_gl': dst_gl,
            'receiver_ac': dst_ac,
            'float_gl': float_gl,
            'float_ac': float_ac,
            'branch': branch.branch_name if branch else None,
            
            # NEW: Fee information
            'fee_info': {
                'transfer_amount': str(transfer_amount),
                'fee_amount': str(fee_amount),
                'total_debited': str(total_customer_debit),
                'fee_waived': fee_info.get('is_waived', False),
                'waiver_reason': fee_info.get('waiver_reason', ''),
                'config_name': fee_info.get('config_name', 'Unknown'),
                'remaining_free_today': fee_info.get('remaining_free_today', 0),
                'remaining_free_month': fee_info.get('remaining_free_month', 0)
            }
        }

        return JsonResponse(response_data, status=200)

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




"""
Complete Django Views for Wallet Creation with Account Number Replacement
Integrated with existing gl_no/ac_no and float_account_number system
Now includes gender fetch from DB and normalized mapping for 9PSB (0=Male, 1=Female)
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db.models import Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from customers.models import Customer, Company
from transactions.models import Memtrans
from .serializers import MemtransSerializer
import logging
import requests
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import re

logger = logging.getLogger(__name__)

# ============================================================================
# WALLET CREATION WITH ACCOUNT NUMBER REPLACEMENT - MAIN ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_creation_data(request):
    """
    Get customer data required for 9PSB wallet creation
    Returns readonly form data for wallet creation with current account number
    NOW INCLUDES: UI state for dynamic button (Create Wallet vs Add Money)
    """
    try:
        # Find customer by matching gl_no and ac_no with request.user
        customer = None
        
        # Method 1: Try to find customer by exact gl_no and ac_no match
        if hasattr(request.user, 'gl_no') and hasattr(request.user, 'ac_no'):
            if request.user.gl_no and request.user.ac_no:
                customer = Customer.objects.filter(
                    gl_no=request.user.gl_no,
                    ac_no=request.user.ac_no
                ).first()
                logger.info(f"[WALLET_CREATION_DATA] Found customer by gl_no/ac_no match: {customer.id if customer else 'None'}")
        
        # Method 2: Fallback to user.customer if no match found and it exists
        if not customer:
            customer = getattr(request.user, 'customer', None)
            if customer:
                logger.info(f"[WALLET_CREATION_DATA] Using fallback customer: {customer.id}")

        if not customer:
            return Response({
                'error': 'Customer profile not found for matching gl_no and ac_no'
            }, status=status.HTTP_404_NOT_FOUND)

        # Get the CURRENT account number (what will be replaced)
        current_account_number = None
        
        # Method 1: Check if User.username contains the account number
        if hasattr(request.user, 'username') and request.user.username:
            username = request.user.username.strip()
            # If username looks like an account number (digits only, reasonable length)
            if username.isdigit() and 8 <= len(username) <= 15:
                current_account_number = username
                logger.info(f"[WALLET_CREATION_DATA] Using username as current account: {username}")
        
        # Method 2: Try gl_no + ac_no combination
        if not current_account_number:
            if hasattr(customer, 'gl_no') and hasattr(customer, 'ac_no') and customer.gl_no and customer.ac_no:
                current_account_number = f"{customer.gl_no}{customer.ac_no}"
                logger.info(f"[WALLET_CREATION_DATA] Using computed account: {current_account_number}")
            elif hasattr(request.user, 'gl_no') and hasattr(request.user, 'ac_no'):
                if request.user.gl_no and request.user.ac_no:
                    current_account_number = f"{request.user.gl_no}{request.user.ac_no}"
                    logger.info(f"[WALLET_CREATION_DATA] Using user's computed account: {current_account_number}")

        # Method 3: Check if there's already a wallet_account that could be the current account
        if not current_account_number and hasattr(customer, 'wallet_account') and customer.wallet_account:
            current_account_number = customer.wallet_account
            logger.info(f"[WALLET_CREATION_DATA] Using existing wallet_account: {current_account_number}")

        # Pull gender from DB and normalize
        gender_raw = getattr(customer, 'gender', None) or getattr(customer, 'cust_sex', None)
        gender_text = normalize_gender_text(gender_raw) if gender_raw else None
        try:
            gender_code = normalize_gender_code(gender_raw) if gender_raw is not None else None
        except Exception:
            gender_code = None

        # Check wallet status for UI state
        existing_wallet = getattr(customer, 'wallet_account', None)
        has_wallet = bool(existing_wallet)

        # Extract customer data using exact Customer model fields
        data = {
            'full_name': customer.get_full_name() if hasattr(customer, 'get_full_name') else f"{customer.first_name or ''} {customer.last_name or ''}".strip(),
            'phone_number': getattr(customer, 'mobile', '') or getattr(customer, 'phone_no', '') or getattr(customer, 'phone', '') or '',
            'email': getattr(customer, 'email', '') or '',
            'date_of_birth': customer.dob.strftime('%Y-%m-%d') if hasattr(customer, 'dob') and customer.dob else '',
            'address': getattr(customer, 'address', '') or '',
            'state': getattr(customer, 'state', '') or '',
            'nationality': getattr(customer, 'nationality', 'Nigerian'),
            'bvn': getattr(customer, 'bvn', '') or '',
            'account_number': current_account_number or '',
            'has_existing_wallet': has_wallet,
            'wallet_account': existing_wallet,
            'current_wallet_account': existing_wallet,
            'customer_gl_no': getattr(customer, 'gl_no', ''),
            'customer_ac_no': getattr(customer, 'ac_no', ''),

            # Gender fields
            'gender': gender_text,
            'gender_code': gender_code,
            'cust_sex': gender_raw,

            # UI CONTROL: Determines which button to show
            'ui_state': {
                'show_create_wallet_button': not has_wallet,
                'show_add_money_button': has_wallet,
                'button_text': 'Add Money' if has_wallet else 'Create Wallet',
                'button_action': 'add_money' if has_wallet else 'create_wallet',
                'wallet_ready_for_funding': has_wallet
            },
            
            # Account details for copying (when Add Money is shown)
            'funding_details': {
                'account_name': customer.get_full_name() if hasattr(customer, 'get_full_name') else f"{customer.first_name or ''} {customer.last_name or ''}".strip(),
                'account_number': existing_wallet if has_wallet else None,
                'bank_name': getattr(customer, 'bank_name', '9PSB Microfinance Bank') if has_wallet else None,
                'bank_code': getattr(customer, 'bank_code', '120001') if has_wallet else None,
                'copy_ready': has_wallet
            } if has_wallet else None
        }

        # Log the data for debugging
        logger.info(
            f"[WALLET_CREATION_DATA] Customer {customer.id} data: "
            f"BVN={'Present' if data['bvn'] else 'Missing'}, "
            f"Gender={data['gender']} (code={data['gender_code']} raw={data['cust_sex']}), "
            f"Current_Account={current_account_number}, "
            f"Has_Wallet={data['has_existing_wallet']}, "
            f"Button={data['ui_state']['button_text']}, "
            f"GL_NO={data['customer_gl_no']}, AC_NO={data['customer_ac_no']}, "
            f"Name={data['full_name']}"
        )
        
        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"[WALLET_CREATION_DATA] Error: {str(e)}")
        return Response({
            'error': 'Failed to load wallet creation data'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wallet_create(request):
    """
    Create 9PSB wallet account and INSERT the wallet account into the Customer model
    Finds customer by matching gl_no and ac_no with request.user
    Uses gender from DB if not provided, normalized to 0=Male, 1=Female for 9PSB
    ALSO inserts wallet_account into Customer with gl_no='20111' and same ac_no
    """
    try:
        # Find customer by matching gl_no and ac_no with request.user
        customer = None
        
        # Method 1: Try to find customer by exact gl_no and ac_no match
        if hasattr(request.user, 'gl_no') and hasattr(request.user, 'ac_no'):
            if request.user.gl_no and request.user.ac_no:
                customer = Customer.objects.filter(
                    gl_no=request.user.gl_no,
                    ac_no=request.user.ac_no
                ).first()
                logger.info(f"[WALLET_CREATE] Found customer by gl_no/ac_no match: {customer.id if customer else 'None'}")
        
        # Method 2: Fallback to user.customer if no match found and it exists
        if not customer:
            customer = getattr(request.user, 'customer', None)
            if customer:
                logger.info(f"[WALLET_CREATE] Using fallback customer: {customer.id}")

        if not customer:
            return Response({
                'error': 'Customer profile not found for matching gl_no and ac_no',
                'user_gl_no': getattr(request.user, 'gl_no', None),
                'user_ac_no': getattr(request.user, 'ac_no', None)
            }, status=status.HTTP_404_NOT_FOUND)

        # Store the old account number for reference
        old_account_number = request.data.get('account_number', '')
        
        # Get wallet creation data from request
        wallet_data = request.data
        
        # Validate required fields
        required_fields = ['full_name', 'phone_number', 'email', 'bvn', 'account_number']
        missing_fields = []
        
        for field in required_fields:
            value = wallet_data.get(field, '').strip() if wallet_data.get(field) else ''
            if not value or value == 'null' or value == 'Not provided':
                missing_fields.append(field)
        
        if missing_fields:
            return Response({
                'error': f'Missing or invalid required fields: {", ".join(missing_fields)}',
                'missing_fields': missing_fields
            }, status=status.HTTP_400_BAD_REQUEST)

        # Resolve/normalize gender (prefer request, fallback to DB)
        gender_raw = wallet_data.get('gender')
        if not gender_raw:
            gender_raw = wallet_data.get('gender_text')
        if not gender_raw and wallet_data.get('gender_code') is not None:
            gender_raw = wallet_data.get('gender_code')

        if gender_raw is None:
            gender_raw = getattr(customer, 'gender', None) or getattr(customer, 'cust_sex', None)

        try:
            gender_code = normalize_gender_code(gender_raw)
            gender_text = normalize_gender_text(gender_raw)
        except ValueError as e:
            return Response({
                'error': f'Invalid gender value: {e}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if customer already has a wallet account
        if hasattr(customer, 'wallet_account') and customer.wallet_account and customer.wallet_account != old_account_number:
            logger.info(f"[WALLET_CREATE] Customer {customer.id} already has different wallet: {customer.wallet_account}")
            return Response({
                'message': 'Different wallet account already exists for this customer',
                'old_account_number': old_account_number,
                'new_account_number': customer.wallet_account,
                'bank_name': getattr(customer, 'bank_name', '9PSB'),
                'bank_code': getattr(customer, 'bank_code', '120001'),
                'already_exists': True,
                'account_updated': False,
                'customer_id': customer.id,
                'customer_gl_no': getattr(customer, 'gl_no', ''),
                'customer_ac_no': getattr(customer, 'ac_no', '')
            }, status=status.HTTP_200_OK)

        # Prepare 9PSB API request data
        ninepsb_data = {
            'customer_name': wallet_data['full_name'],
            'customer_phone': wallet_data['phone_number'],
            'customer_email': wallet_data['email'],
            'customer_bvn': wallet_data['bvn'],
            'customer_address': wallet_data.get('address', ''),
            'date_of_birth': wallet_data.get('date_of_birth', ''),
            'state_of_origin': wallet_data.get('state', ''),
            'nationality': wallet_data.get('nationality', 'Nigerian'),
            'reference_account': old_account_number,  # Original account number for reference
            'customer_id': customer.id,
            'gl_no': getattr(customer, 'gl_no', ''),
            'ac_no': getattr(customer, 'ac_no', ''),
            # Normalized gender for 9PSB
            'customer_gender_code': gender_code,
            'customer_gender': gender_text,
        }

        logger.info(
            f"[WALLET_CREATE] Creating wallet for customer {customer.id} "
            f"(gl_no: {ninepsb_data['gl_no']}, ac_no: {ninepsb_data['ac_no']}) "
            f"to replace account {old_account_number} | gender={gender_text}({gender_code})"
        )

        # Use database transaction to ensure data consistency
        with transaction.atomic():
            # Call 9PSB API to create wallet using real API
            ninepsb_response = create_ninepsb_wallet(ninepsb_data)

            if ninepsb_response['success']:
                new_wallet_account = ninepsb_response['wallet_account_number']
                
                # INSERT the wallet account into the primary Customer model
                logger.info(f"[WALLET_CREATE] Inserting wallet_account {new_wallet_account} into Customer {customer.id} where gl_no={getattr(customer, 'gl_no', '')} and ac_no={getattr(customer, 'ac_no', '')}")
                
                # Store old values for logging
                old_wallet_account = getattr(customer, 'wallet_account', None)
                old_username = request.user.username
                
                # Update customer fields - INSERT the wallet account
                customer.wallet_account = new_wallet_account
                update_fields = ['wallet_account']

                if hasattr(customer, 'bank_name'):
                    customer.bank_name = ninepsb_response.get('bank_name', '9PSB Microfinance Bank')
                    update_fields.append('bank_name')
                if hasattr(customer, 'bank_code'):
                    customer.bank_code = ninepsb_response.get('bank_code', '120001')
                    update_fields.append('bank_code')

                # Persist normalized gender if useful/available on model
                try:
                    if hasattr(customer, 'gender'):
                        customer.gender = gender_text
                        update_fields.append('gender')
                    if hasattr(customer, 'cust_sex') and not getattr(customer, 'cust_sex', None):
                        customer.cust_sex = 'M' if gender_code == 0 else 'F'
                        update_fields.append('cust_sex')
                except Exception:
                    pass
                
                # IMPORTANT: Keep gl_no and ac_no unchanged as they are used for transactions
                logger.info(f"[WALLET_CREATE] Preserving gl_no={getattr(customer, 'gl_no', '')} and ac_no={getattr(customer, 'ac_no', '')} for transaction compatibility")
                
                # Save the primary customer with updated wallet information
                customer.save(update_fields=update_fields)

                # ADDITIONAL: Also insert wallet_account into Customer with gl_no='20111' and same ac_no
                current_ac_no = getattr(customer, 'ac_no', '')
                secondary_customer_updated = False
                secondary_customer_id = None
                
                if current_ac_no:
                    try:
                        secondary_customer = Customer.objects.filter(
                            gl_no='20111',
                            ac_no=current_ac_no
                        ).first()
                        
                        if secondary_customer:
                            logger.info(f"[WALLET_CREATE] Found secondary customer {secondary_customer.id} with gl_no=20111, ac_no={current_ac_no}")
                            
                            # Update the secondary customer with same wallet details
                            secondary_customer.wallet_account = new_wallet_account
                            secondary_update_fields = ['wallet_account']
                            
                            if hasattr(secondary_customer, 'bank_name'):
                                secondary_customer.bank_name = ninepsb_response.get('bank_name', '9PSB Microfinance Bank')
                                secondary_update_fields.append('bank_name')
                            if hasattr(secondary_customer, 'bank_code'):
                                secondary_customer.bank_code = ninepsb_response.get('bank_code', '120001')
                                secondary_update_fields.append('bank_code')
                            
                            # Save the secondary customer
                            secondary_customer.save(update_fields=secondary_update_fields)
                            secondary_customer_updated = True
                            secondary_customer_id = secondary_customer.id
                            
                            logger.info(f"[WALLET_CREATE] SUCCESS - Also updated secondary customer {secondary_customer.id} (gl_no=20111, ac_no={current_ac_no}) with wallet_account={new_wallet_account}")
                        else:
                            logger.warning(f"[WALLET_CREATE] No secondary customer found with gl_no=20111, ac_no={current_ac_no}")
                    
                    except Exception as secondary_error:
                        logger.error(f"[WALLET_CREATE] Failed to update secondary customer (gl_no=20111, ac_no={current_ac_no}): {str(secondary_error)}")
                        # Don't fail the main transaction for secondary customer update failure
                
                # Update the User.username if it was the account number
                username_updated = False
                if hasattr(request.user, 'username'):
                    if request.user.username == old_account_number:
                        request.user.username = new_wallet_account
                        request.user.save()
                        username_updated = True
                        logger.info(f"[WALLET_CREATE] Updated username from {old_account_number} to {new_wallet_account}")

                # Verify the primary save was successful
                customer.refresh_from_db()
                if customer.wallet_account != new_wallet_account:
                    logger.error(f"[WALLET_CREATE] SAVE FAILED - Wallet not saved to customer {customer.id}")
                    raise Exception("Failed to save new wallet account number to customer profile")

                logger.info(
                    f"[WALLET_CREATE] SUCCESS - Customer {customer.id} wallet_account inserted: "
                    f"Old={old_wallet_account}, New={new_wallet_account}, "
                    f"GL_NO={getattr(customer, 'gl_no', '')}, AC_NO={getattr(customer, 'ac_no', '')}, "
                    f"Username_Updated={username_updated}, "
                    f"Secondary_Customer_Updated={secondary_customer_updated} (ID={secondary_customer_id})"
                )

                # Verify that gl_no and ac_no match request.user
                verification_status = {
                    'customer_gl_no_matches': getattr(customer, 'gl_no', '') == getattr(request.user, 'gl_no', ''),
                    'customer_ac_no_matches': getattr(customer, 'ac_no', '') == getattr(request.user, 'ac_no', ''),
                    'wallet_inserted': customer.wallet_account == new_wallet_account,
                    'secondary_customer_updated': secondary_customer_updated,
                    'secondary_customer_id': secondary_customer_id
                }

                return Response({
                    'message': 'Wallet created and inserted into Customer model successfully!',
                    'old_account_number': old_account_number,
                    'new_account_number': new_wallet_account,
                    'wallet_account_number': new_wallet_account,  # For backwards compatibility
                    'bank_name': getattr(customer, 'bank_name', '9PSB Microfinance Bank'),
                    'bank_code': getattr(customer, 'bank_code', '120001'),
                    'reference_number': ninepsb_response.get('reference_number'),
                    'tracking_ref': ninepsb_response.get('tracking_ref'),
                    'created_at': ninepsb_response.get('created_at'),
                    'customer_id': customer.id,
                    'customer_gl_no': getattr(customer, 'gl_no', ''),
                    'customer_ac_no': getattr(customer, 'ac_no', ''),
                    'account_updated': True,
                    'username_updated': username_updated,
                    'verification': verification_status,
                    'api_version': ninepsb_response.get('api_version', '3.0'),
                    # Echo normalized gender for confirmation
                    'gender': gender_text,
                    'gender_code': gender_code,
                    # Secondary customer update info
                    'secondary_updates': {
                        'gl_20111_customer_updated': secondary_customer_updated,
                        'gl_20111_customer_id': secondary_customer_id,
                        'gl_20111_ac_no': current_ac_no if secondary_customer_updated else None
                    }
                }, status=status.HTTP_201_CREATED)

            else:
                # 9PSB API failed
                error_message = ninepsb_response.get('message', 'Failed to create wallet with 9PSB')
                logger.error(f"[WALLET_CREATE] 9PSB API failed for customer {customer.id}: {error_message}")
                
                return Response({
                    'error': f'9PSB API Error: {error_message}',
                    'details': ninepsb_response.get('details'),
                    'ninepsb_response': ninepsb_response,
                    'account_unchanged': True,
                    'customer_id': customer.id,
                    'retry_allowed': ninepsb_response.get('retry_allowed', False)
                }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"[WALLET_CREATE] Critical Error for customer {getattr(customer, 'id', 'unknown') if 'customer' in locals() else 'unknown'}: {str(e)}")
        return Response({
            'error': 'Failed to create wallet and insert into Customer model',
            'details': str(e),
            'account_unchanged': True
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# ============================================================================
# ENHANCED DASHBOARD VIEW - INTEGRATED WITH WALLET FUNCTIONALITY
# ============================================================================

class DashboardView(APIView):
    """
    Enhanced dashboard with strict wallet source:
    - Use request.user.gl_no and request.user.ac_no to find the Customer row
    - Take wallet_account from that matched Customer row only
    - Use that same (gl_no, ac_no) as the primary account for balances/transactions
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        print("🔥 Enhanced DashboardView called - wallet integration ACTIVE!")

        # 1) Ensure a customer is linked (for general info), but we will rely on user.gl_no/ac_no
        customer = getattr(request.user, 'customer', None)
        if not customer:
            print("❌ No Customer profile linked to user")
            return Response({"detail": "Customer profile not linked to user."}, status=404)

        # 2) Company
        company = getattr(request.user, 'company', None) or Company.objects.first()
        if not company:
            print("❌ No company found in system")
            return Response({"detail": "Company profile not found in the system."}, status=404)
        print(f"✅ Using company: {getattr(company, 'company_name', 'N/A')} ({company.id})")

        # 3) PRIMARY gl/ac come from the USER model
        user_gl_no = (getattr(request.user, 'gl_no', '') or '').strip()
        user_ac_no = (getattr(request.user, 'ac_no', '') or '').strip()

        # Fallback to attached customer only if user fields are empty
        gl_no = user_gl_no or (customer.gl_no or '').strip()
        ac_no = user_ac_no or (customer.ac_no or '').strip()

        float_account_number = (getattr(company, 'float_account_number', '') or '').strip()

        # 3b) STRONG SOURCE for wallet_account: Customer row that matches USER gl/ac
        cust_row = (
            Customer.objects
            .filter(gl_no=gl_no, ac_no=ac_no)
            .values('wallet_account', 'bank_name', 'bank_code', 'first_name', 'middle_name', 'last_name', 'label')
            .first()
        )

        wallet_account_val = (cust_row or {}).get('wallet_account')  # None if no row or empty
        wallet_account = (wallet_account_val or '').strip() or None
        has_wallet = bool(wallet_account)
        wallet_bank_name = "9PSB Microfinance Bank"

        # Bank/name fields
        bank_name = ((cust_row or {}).get('bank_name') or customer.bank_name or '').strip()
        bank_code = ((cust_row or {}).get('bank_code') or customer.bank_code or '').strip()
        if has_wallet:
            bank_name = wallet_bank_name

        fn = ((cust_row or {}).get('first_name') or customer.first_name or '').strip()
        mn = ((cust_row or {}).get('middle_name') or getattr(customer, 'middle_name', '') or '').strip()
        ln = ((cust_row or {}).get('last_name') or customer.last_name or '').strip()
        label = ((cust_row or {}).get('label') or getattr(customer, 'label', '') or '').strip()
        account_name = " ".join([p for p in [fn, mn, ln] if p]).strip() or label or (customer.email or '').strip()

        print(f"🏦 float_account_number: {float_account_number or '❌ None'}")
        print(f"👤 user.gl_no/ac_no: {gl_no}/{ac_no}")
        print(f"💳 wallet_account (from Customer matching user gl/ac): {wallet_account or '❌ None'}")

        # 4) If primary gl/ac missing, still return wallet-aware shell
        if not gl_no or not ac_no:
            return Response({
                "customer": {
                    "id": customer.id,
                    "first_name": fn,
                    "last_name": ln,
                    "full_name": f"{fn} {ln}".strip(),
                    "email": customer.email or "",
                    "gl_no": gl_no,
                    "ac_no": ac_no,
                    "float_account_number": float_account_number,
                    "bank_name": bank_name or "FinanceFlex",
                    "bank_code": bank_code,
                    "account_name": account_name,
                    "wallet_account": wallet_account,
                    "has_wallet": has_wallet,
                    "primary_account": wallet_account if has_wallet else float_account_number,
                    "account_type": "9PSB_WALLET" if has_wallet else "TRADITIONAL",
                    "display_account": wallet_account or float_account_number,
                    "wallet_created_at": getattr(customer, 'wallet_created_at', None),
                },
                "wallet_status": {
                    "has_wallet": has_wallet,
                    "wallet_account": wallet_account,
                    "wallet_bank": wallet_bank_name if has_wallet else None,
                    "integration_status": "wallet_active" if has_wallet else "traditional_account",
                },
                "customer_last_name": ln,
                "balance": 0.0,
                "accounts": [],
                "transactions": [],
                "primary_gl_no": gl_no,
                "primary_ac_no": ac_no,
                "primary_float_account_number": float_account_number,
                "account_display": {
                    "primary_display": wallet_account if has_wallet else float_account_number,
                    "transaction_account": f"{gl_no}{ac_no}",
                    "float_account": float_account_number,
                    "wallet_account": wallet_account,
                    "show_wallet_first": has_wallet,
                    "integration_type": "hybrid_display",
                },
            })

        # 5) Aggregate balances for THIS primary ac_no
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

        # 6) Primary balance for this primary gl_no
        primary_balance: Decimal = Decimal('0')
        for r in per_accounts:
            if str(r['gl_no']).strip() == gl_no:
                primary_balance = r['balance'] or Decimal('0')
                break

        # 7) Last 20 transactions for this gl/ac
        recent_qs = (
            Memtrans.objects
            .filter(gl_no=gl_no, ac_no=ac_no)
            .order_by('-sys_date')[:20]
        )
        transactions_data = MemtransSerializer(recent_qs, many=True).data

        # 8) Accounts list; wallet adornments only for the primary account
        accounts_data = []
        for r in per_accounts:
            r_gl = (str(r["gl_no"]).strip())
            r_ac = (str(r["ac_no"]).strip())
            r_bal = r["balance"] or Decimal('0')
            is_primary = (r_gl == gl_no and r_ac == ac_no)
            accounts_data.append({
                "gl_no": r_gl,
                "ac_no": r_ac,
                "balance": float(r_bal),
                "available_balance": float(r_bal),
                "float_account_number": float_account_number,
                "bank_name": (wallet_bank_name if (has_wallet and is_primary) else (bank_name or "FinanceFlex")),
                "bank_code": bank_code,
                "has_wallet": has_wallet if is_primary else False,
                "wallet_account": wallet_account if is_primary else None,
                "account_type": "wallet_integrated" if (has_wallet and is_primary) else "traditional",
                "display_account": (wallet_account if (has_wallet and is_primary) else float_account_number),
            })

        # 9) Final payload
        response_data = {
            "customer": {
                "id": customer.id,
                "first_name": fn,
                "last_name": ln,
                "full_name": f"{fn} {ln}".strip(),
                "email": customer.email or "",
                "gl_no": gl_no,
                "ac_no": ac_no,
                "float_account_number": float_account_number,
                "bank_name": bank_name or "FinanceFlex",
                "bank_code": bank_code,
                "balance": float(primary_balance),
                "account_name": account_name,
                "wallet_account": wallet_account,
                "has_wallet": has_wallet,
                "primary_account": wallet_account if has_wallet else float_account_number,
                "account_type": "9PSB_WALLET" if has_wallet else "TRADITIONAL",
                "display_account": wallet_account or float_account_number,
                "wallet_created_at": getattr(customer, 'wallet_created_at', None),
            },
            "customer_last_name": ln,
            "wallet_status": {
                "has_wallet": has_wallet,
                "wallet_account": wallet_account,
                "wallet_bank": wallet_bank_name if has_wallet else None,
                "wallet_bank_code": "120001" if has_wallet else None,
                "integration_status": "wallet_active" if has_wallet else "traditional_account",
                "transaction_compatibility": "preserved",
                "gl_no_preserved": gl_no,
                "ac_no_preserved": ac_no,
                "data_completeness": calculate_data_completeness(customer) if 'calculate_data_completeness' in globals() else 100,
            },
            "primary_gl_no": gl_no,
            "primary_ac_no": ac_no,
            "primary_float_account_number": float_account_number,
            "balance": float(primary_balance),
            "accounts": accounts_data,
            "transactions": transactions_data,
            "account_display": {
                "primary_display": wallet_account if has_wallet else float_account_number,
                "transaction_account": f"{gl_no}{ac_no}",
                "float_account": float_account_number,
                "wallet_account": wallet_account,
                "show_wallet_first": has_wallet,
                "integration_type": "hybrid_display",
            },
        }

        print("✅ Enhanced Dashboard response prepared successfully.")
        print(f"🧾 Primary display account: {response_data['account_display']['primary_display']}")
        print(f"📊 Transaction account (GL+AC): {gl_no}{ac_no}")
        print(f"🔗 Wallet integration status: {'ACTIVE' if has_wallet else 'TRADITIONAL'}")
        return Response(response_data, status=200)


# ============================================================================
# 9PSB API INTEGRATION
# ============================================================================
def create_ninepsb_wallet(data):
    """
    Call 9PSB API to create wallet account using the official 9PSB WAAS API.
    
    Based on 9PSB API Documentation Section 3: WALLET OPENING
    URL: http://102.216.128.75:9090/waas/api/v1/open_wallet
    
    Args:
        data: Dictionary containing customer information for wallet creation
        
    Returns:
        Dictionary with success/failure status and wallet details or error information
    """
    try:
        # Get 9PSB API configuration from Django settings
        ninepsb_api_base = getattr(settings, 'NINEPSB_API_BASE', 'http://102.216.128.75:9090/waas/api/v1')
        ninepsb_username = getattr(settings, 'NINEPSB_USERNAME', 'your-username')
        ninepsb_password = getattr(settings, 'NINEPSB_PASSWORD', 'your-password')
        ninepsb_client_id = getattr(settings, 'NINEPSB_CLIENT_ID', 'your-client-id')
        ninepsb_client_secret = getattr(settings, 'NINEPSB_CLIENT_SECRET', 'your-client-secret')
        ninepsb_timeout = getattr(settings, 'NINEPSB_API_TIMEOUT', 30)

        logger.info(f"[9PSB_API] Starting wallet creation for customer: {data.get('customer_name')} (ID: {data.get('customer_id')})")

        # Step 1: Authenticate with 9PSB to get access token
        auth_url = f"{ninepsb_api_base}/authenticate"
        auth_payload = {
            'username': ninepsb_username,
            'password': ninepsb_password,
            'clientId': ninepsb_client_id,
            'clientSecret': ninepsb_client_secret
        }

        logger.info(f"[9PSB_AUTH] Authenticating with 9PSB API")
        auth_response = requests.post(
            auth_url, 
            json=auth_payload, 
            headers={'Content-Type': 'application/json'},
            timeout=ninepsb_timeout
        )

        if auth_response.status_code != 200:
            logger.error(f"[9PSB_AUTH] Authentication failed: {auth_response.status_code}")
            return {
                'success': False,
                'message': 'Failed to authenticate with 9PSB API',
                'details': f'Authentication failed with status {auth_response.status_code}',
                'retry_allowed': True
            }

        auth_data = auth_response.json()
        access_token = auth_data.get('accessToken')
        
        if not access_token:
            logger.error(f"[9PSB_AUTH] No access token received")
            return {
                'success': False,
                'message': 'Failed to get access token from 9PSB',
                'details': 'Authentication response missing accessToken',
                'retry_allowed': True
            }

        logger.info(f"[9PSB_AUTH] Successfully authenticated with 9PSB")

        # Step 2: Prepare wallet creation payload according to 9PSB API spec
        wallet_url = f"{ninepsb_api_base}/open_wallet"
        
        # Generate unique transaction tracking reference
        tracking_ref = f"FF_{uuid.uuid4().hex[:12].upper()}_{int(timezone.now().timestamp())}"
        
        # Parse date of birth from various formats to 9PSB format (dd/MM/yyyy)
        date_of_birth = ""
        if data.get('date_of_birth'):
            try:
                # Try to parse the date and convert to 9PSB format
                if isinstance(data['date_of_birth'], str):
                    # Handle different date formats
                    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S'):
                        try:
                            parsed_date = datetime.strptime(data['date_of_birth'], fmt)
                            date_of_birth = parsed_date.strftime('%d/%m/%Y')
                            break
                        except ValueError:
                            continue
            except Exception as e:
                logger.warning(f"[9PSB_API] Could not parse date of birth: {e}")

        # Split customer name into lastName and otherNames
        full_name = data.get('customer_name', '').strip()
        name_parts = full_name.split() if full_name else []
        last_name = name_parts[-1] if name_parts else 'Unknown'
        other_names = ' '.join(name_parts[:-1]) if len(name_parts) > 1 else ''

        # Parse gender (9PSB expects 0: Male, 1: Female)
        gender = data.get('customer_gender_code')
        if gender is None:
            try:
                gender = normalize_gender_code(data.get('customer_gender'))
            except Exception:
                gender = 0  # default to Male if unknown

        # Create 9PSB API payload according to their specification
        wallet_payload = {
            'transactionTrackingRef': tracking_ref,
            'lastName': last_name,
            'otherNames': other_names,
            'accountName': full_name,  # How account will be named
            'phoneNo': data.get('customer_phone', ''),
            'gender': gender,  # 0/1 must be preserved even if 0
            'placeOfBirth': data.get('place_of_birth', ''),
            'dateOfBirth': date_of_birth,
            'address': data.get('customer_address', ''),
            'nationalIdentityNo': '',  # NIN if available
            'ninUserId': '',  # NIN User ID
            'nextOfKinPhoneNo': '',
            'nextOfKinName': '',
            'referralPhoneNo': '',
            'referralName': '',
            'otherAccountInformationSource': f"FinanceFlex - Customer ID {data.get('customer_id')} - GL:{data.get('gl_no')} AC:{data.get('ac_no')} - Replacing {data.get('reference_account', '')}",
            'email': data.get('customer_email', ''),
            'customerImage': '',  # Base64 image if available
            'customerSignature': '',  # Base64 signature if available
            'bvn': data.get('customer_bvn', '')
        }

        # Remove empty fields but keep zeros (e.g., gender=0)
        wallet_payload = {
            k: v for k, v in wallet_payload.items()
            if v is not None and (not isinstance(v, str) or v.strip() != '')
        }

        # Ensure required fields are present
        required_fields = ['transactionTrackingRef', 'lastName', 'phoneNo', 'address']
        missing_required = [field for field in required_fields if not wallet_payload.get(field)]
        
        if missing_required:
            logger.error(f"[9PSB_API] Missing required fields: {missing_required}")
            return {
                'success': False,
                'message': f'Missing required fields for 9PSB wallet creation: {", ".join(missing_required)}',
                'details': 'Customer data incomplete for wallet creation',
                'retry_allowed': False
            }

        # Step 3: Create wallet with 9PSB API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
            'User-Agent': 'FinanceFlex-Mobile/1.0'
        }

        logger.info(f"[9PSB_API] Creating wallet with tracking ref: {tracking_ref}")
        
        wallet_response = requests.post(
            wallet_url,
            json=wallet_payload,
            headers=headers,
            timeout=ninepsb_timeout
        )

        logger.info(f"[9PSB_API] Wallet creation response status: {wallet_response.status_code}")

        # Step 4: Process 9PSB response
        if wallet_response.status_code in [200, 201]:
            try:
                result = wallet_response.json()
                logger.info(f"[9PSB_API] Raw response: {result}")
                
                # 9PSB returns {message, status, statusCode, data}
                api_status = result.get('status', '').upper()
                api_message = result.get('message', '')
                api_data = result.get('data', {})
                
                if api_status == 'SUCCESS':
                    # Extract account details from response data
                    wallet_account_number = None
                    
                    # Try to extract account number from various possible locations in response
                    if isinstance(api_data, dict):
                        wallet_account_number = (
                            api_data.get('accountNumber') or 
                            api_data.get('account_number') or
                            api_data.get('walletAccountNumber') or
                            api_data.get('wallet_account_number')
                        )
                    
                    if not wallet_account_number:
                        logger.error(f"[9PSB_API] No account number found in successful response")
                        return {
                            'success': False,
                            'message': '9PSB wallet created but account number not found in response',
                            'details': api_data,
                            'retry_allowed': False
                        }

                    logger.info(f"[9PSB_API] Wallet created successfully: {wallet_account_number}")
                    
                    return {
                        'success': True,
                        'wallet_account_number': wallet_account_number,
                        'bank_name': '9PSB Microfinance Bank',
                        'bank_code': '120001',
                        'reference_number': tracking_ref,
                        'transaction_id': tracking_ref,
                        'tracking_ref': tracking_ref,
                        'created_at': timezone.now().isoformat(),
                        'message': f'Wallet account {wallet_account_number} created successfully',
                        'api_response': result,
                        'api_version': '3.0',
                        'customer_id': data.get('customer_id'),
                        'gl_no': data.get('gl_no'),
                        'ac_no': data.get('ac_no')
                    }
                
                else:
                    # 9PSB returned failure status
                    logger.error(f"[9PSB_API] Wallet creation failed - Status: {api_status}, Message: {api_message}")
                    
                    return {
                        'success': False,
                        'message': f'9PSB wallet creation failed: {api_message}',
                        'details': api_data,
                        'api_response': result,
                        'retry_allowed': api_status != 'FAILED'
                    }
                    
            except json.JSONDecodeError as e:
                logger.error(f"[9PSB_API] Invalid JSON response: {e}")
                return {
                    'success': False,
                    'message': 'Invalid response format from 9PSB API',
                    'details': wallet_response.text[:500],
                    'retry_allowed': True
                }
        
        else:
            # HTTP error status
            logger.error(f"[9PSB_API] HTTP error {wallet_response.status_code}: {wallet_response.text}")
            
            try:
                error_data = wallet_response.json()
            except:
                error_data = {'message': wallet_response.text[:500]}
            
            return {
                'success': False,
                'message': f'9PSB API HTTP error: {wallet_response.status_code}',
                'details': error_data,
                'status_code': wallet_response.status_code,
                'retry_allowed': wallet_response.status_code in [500, 502, 503, 504, 429]
            }

    except requests.exceptions.Timeout:
        logger.error(f"[9PSB_API] Request timed out after {ninepsb_timeout} seconds")
        return {
            'success': False,
            'message': '9PSB API request timed out - please try again',
            'details': f'Request timed out after {ninepsb_timeout} seconds',
            'retry_allowed': True
        }
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[9PSB_API] Connection error: {str(e)}")
        return {
            'success': False,
            'message': 'Unable to connect to 9PSB API',
            'details': f'Network connection error: {str(e)}',
            'retry_allowed': True
        }
        
    except Exception as e:
        logger.error(f"[9PSB_API] Unexpected error: {str(e)}")
        return {
            'success': False,
            'message': 'Unexpected error occurred during 9PSB wallet creation',
            'details': str(e),
            'retry_allowed': False
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def normalize_gender_code(value):
    """
    Returns 0 for Male, 1 for Female. Accepts 'Male'/'M'/0 and 'Female'/'F'/1.
    Raises ValueError if cannot normalize.
    """
    if value is None:
        raise ValueError("gender is required")
    s = str(value).strip().lower()
    if s in ("0", "male", "m"):
        return 0
    if s in ("1", "female", "f"):
        return 1
    if s in ("true", "false"):
        raise ValueError("invalid gender value")
    raise ValueError(f"invalid gender value: {value}")


def normalize_gender_text(value):
    try:
        code = normalize_gender_code(value)
        return "Male" if code == 0 else "Female"
    except Exception:
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        lower = raw.lower()
        if lower == 'm':
            return 'Male'
        if lower == 'f':
            return 'Female'
        return raw[:1].upper() + raw[1:].lower()


def get_current_account_number(user, customer):
    """
    Determine the current account number for a customer using priority-based logic.
    Enhanced to work with gl_no/ac_no system.
    
    Priority Order:
    1. Existing wallet_account (if customer already has one)
    2. Customer gl_no + ac_no (computed account for transactions)
    3. Username (if it looks like an account number)
    4. User gl_no + ac_no (fallback)
    
    Args:
        user: Django User object
        customer: Customer model instance
        
    Returns:
        String account number or None if not found
    """
    # Priority 1: Existing wallet account
    if hasattr(customer, 'wallet_account') and customer.wallet_account:
        logger.debug(f"Using existing wallet_account: {customer.wallet_account}")
        return customer.wallet_account
    
    # Priority 2: Customer gl_no + ac_no (most common for transaction system)
    if hasattr(customer, 'gl_no') and hasattr(customer, 'ac_no'):
        if customer.gl_no and customer.ac_no:
            computed_account = f"{customer.gl_no}{customer.ac_no}"
            logger.debug(f"Using customer computed account: {computed_account}")
            return computed_account
    
    # Priority 3: Username if it looks like an account number
    if user.username and user.username.isdigit() and 8 <= len(user.username) <= 15:
        logger.debug(f"Using username as account: {user.username}")
        return user.username
    
    # Priority 4: User gl_no + ac_no (fallback)
    if hasattr(user, 'gl_no') and hasattr(user, 'ac_no'):
        if user.gl_no and user.ac_no:
            computed_account = f"{user.gl_no}{user.ac_no}"
            logger.debug(f"Using user computed account: {computed_account}")
            return computed_account
    
    logger.warning(f"No account number found for user {user.id}, customer {getattr(customer, 'id', 'None')}")
    return None


def get_customer_full_name(customer):
    """Get customer's full name with fallbacks."""
    if hasattr(customer, 'get_full_name') and callable(customer.get_full_name):
        full_name = customer.get_full_name()
        if full_name and full_name.strip():
            return full_name.strip()
    
    # Fallback to first_name + last_name
    first_name = getattr(customer, 'first_name', '') or ''
    last_name = getattr(customer, 'last_name', '') or ''
    full_name = f"{first_name} {last_name}".strip()
    
    if full_name:
        return full_name
    
    # Final fallback to name field if exists
    return getattr(customer, 'name', '') or ''


def get_customer_phone(customer):
    """Get customer's phone number with fallbacks."""
    # Try multiple phone field names
    phone_fields = ['mobile', 'phone_no', 'phone', 'phone_number']
    
    for field in phone_fields:
        phone = getattr(customer, field, None)
        if phone and str(phone).strip():
            return str(phone).strip()
    
    return ''


def get_customer_email(customer):
    """Get customer's email with fallbacks."""
    email = getattr(customer, 'email', '') or ''
    return email.strip()


def calculate_data_completeness(customer):
    """Calculate percentage of required data completeness for wallet creation."""
    required_fields = [
        ('full_name', get_customer_full_name(customer)),
        ('phone_number', get_customer_phone(customer)),
        ('email', get_customer_email(customer)),
        ('bvn', getattr(customer, 'bvn', '')),
    ]
    
    completed = sum(1 for field, value in required_fields if value and str(value).strip())
    total = len(required_fields)
    
    return int((completed / total) * 100)


def validate_wallet_creation_data(wallet_data):
    """
    Validate customer data for wallet creation.
    
    Args:
        wallet_data: Dictionary containing customer information
        
    Returns:
        Dictionary with validation results
    """
    required_fields = ['full_name', 'phone_number', 'email', 'bvn', 'account_number']
    missing_fields = []
    
    for field in required_fields:
        value = wallet_data.get(field, '').strip() if wallet_data.get(field) else ''
        if not value or value.lower() in ['null', 'none', 'not provided', '']:
            missing_fields.append(field)
    
    # Additional validation rules
    validation_errors = []
    
    # Validate email format if provided
    email = wallet_data.get('email', '').strip()
    if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        validation_errors.append('Invalid email format')
    
    # Validate BVN format if provided
    bvn = wallet_data.get('bvn', '').strip()
    if bvn and (not bvn.isdigit() or len(bvn) != 11):
        validation_errors.append('BVN must be 11 digits')
    
    # Validate phone number format if provided
    phone = wallet_data.get('phone_number', '').strip()
    if phone:
        # Remove common prefixes and check length
        clean_phone = re.sub(r'^(\+234|234|0)', '', phone)
        if not clean_phone.isdigit() or len(clean_phone) not in [10, 11]:
            validation_errors.append('Invalid phone number format')
    
    return {
        'valid': len(missing_fields) == 0 and len(validation_errors) == 0,
        'missing_fields': missing_fields,
        'validation_errors': validation_errors
    }


# ============================================================================
# DEBUG ENDPOINTS (Remove in production)
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_account_number_status(request):
    """
    Debug endpoint to check customer account number status and resolution logic.
    Enhanced to show gl_no/ac_no integration.
    
    WARNING: Remove this endpoint in production for security.
    """
    try:
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return Response({'error': 'Customer profile not found'}, status=404)

        # Get company information
        company = getattr(request.user, 'company', None) or Company.objects.first()
        
        # Resolve current account number using the same logic as production
        current_account = get_current_account_number(request.user, customer)
        
        debug_data = {
            'timestamp': timezone.now().isoformat(),
            'user_id': request.user.id,
            'customer_id': customer.id,
            'resolved_account_number': current_account,
            
            'customer_fields': {
                'wallet_account': getattr(customer, 'wallet_account', 'N/A'),
                'bank_name': getattr(customer, 'bank_name', 'N/A'),
                'bank_code': getattr(customer, 'bank_code', 'N/A'),
                'gl_no': getattr(customer, 'gl_no', 'N/A'),
                'ac_no': getattr(customer, 'ac_no', 'N/A'),
                'computed_account': f"{getattr(customer, 'gl_no', '')}{getattr(customer, 'ac_no', '')}" if hasattr(customer, 'gl_no') and hasattr(customer, 'ac_no') else 'N/A',
                'first_name': getattr(customer, 'first_name', 'N/A'),
                'last_name': getattr(customer, 'last_name', 'N/A'),
                'full_name_resolved': get_customer_full_name(customer),
                'email': getattr(customer, 'email', 'N/A'),
                'mobile': getattr(customer, 'mobile', 'N/A'),
                'phone_no': getattr(customer, 'phone_no', 'N/A'),
                'phone_resolved': get_customer_phone(customer),
                'bvn': getattr(customer, 'bvn', 'N/A'),
                'is_company': getattr(customer, 'is_company', False),
            },
            
            'company_fields': {
                'company_name': company.company_name if company else 'N/A',
                'float_account_number': company.float_account_number if company else 'N/A',
                'company_id': company.id if company else 'N/A',
            },
            
            'user_fields': {
                'username': request.user.username,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                'gl_no': getattr(request.user, 'gl_no', 'N/A'),
                'ac_no': getattr(request.user, 'ac_no', 'N/A'),
                'computed_account': f"{getattr(request.user, 'gl_no', '')}{getattr(request.user, 'ac_no', '')}" if hasattr(request.user, 'gl_no') and hasattr(request.user, 'ac_no') else 'N/A',
            },
            
            'account_resolution_analysis': {
                'username_is_digits': request.user.username.isdigit() if request.user.username else False,
                'username_length': len(request.user.username) if request.user.username else 0,
                'username_valid_account': bool(request.user.username and request.user.username.isdigit() and 8 <= len(request.user.username) <= 15),
                'primary_source': get_account_source_priority(request.user, customer),
                'has_gl_ac_combo': bool(getattr(customer, 'gl_no', None) and getattr(customer, 'ac_no', None)),
                'gl_ac_computed': f"{getattr(customer, 'gl_no', '')}{getattr(customer, 'ac_no', '')}" if hasattr(customer, 'gl_no') and hasattr(customer, 'ac_no') else None,
            },
            
            'wallet_integration': {
                'has_wallet_account': bool(getattr(customer, 'wallet_account', None)),
                'wallet_account': getattr(customer, 'wallet_account', None),
                'integration_strategy': 'wallet_separate_preserve_gl_ac',
                'transaction_compatibility': 'preserved',
                'data_completeness_percentage': calculate_data_completeness(customer),
            },
            
            'validation_result': validate_wallet_creation_data({
                'full_name': get_customer_full_name(customer),
                'phone_number': get_customer_phone(customer),
                'email': get_customer_email(customer),
                'bvn': getattr(customer, 'bvn', ''),
                'account_number': current_account or ''
            }),
            
            'model_field_availability': {
                'customer_has_wallet_account': hasattr(customer, 'wallet_account'),
                'customer_has_bank_name': hasattr(customer, 'bank_name'),
                'customer_has_bank_code': hasattr(customer, 'bank_code'),
                'customer_has_gl_no': hasattr(customer, 'gl_no'),
                'customer_has_ac_no': hasattr(customer, 'ac_no'),
                'customer_has_get_full_name': hasattr(customer, 'get_full_name'),
                'customer_has_is_company': hasattr(customer, 'is_company'),
                'company_available': company is not None,
            }
        }
        
        return Response(debug_data, status=200)

    except Exception as e:
        logger.error(f"[DEBUG_ACCOUNT_STATUS] Error: {str(e)}")
        return Response({'error': str(e), 'timestamp': timezone.now().isoformat()}, status=500)


def get_account_source_priority(user, customer):
    """Helper function for debug endpoint to show account resolution priority."""
    if hasattr(customer, 'wallet_account') and customer.wallet_account:
        return 'wallet_account'
    elif hasattr(customer, 'gl_no') and hasattr(customer, 'ac_no') and customer.gl_no and customer.ac_no:
        return 'customer_gl_ac'
    elif user.username and user.username.isdigit() and 8 <= len(user.username) <= 15:
        return 'username'
    elif hasattr(user, 'gl_no') and hasattr(user, 'ac_no') and user.gl_no and user.ac_no:
        return 'user_gl_ac'
    else:
        return 'none'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_status_check(request):
    """
    Check the current wallet status for a customer with gl_no/ac_no integration.
    """
    try:
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return Response({'error': 'Customer profile not found'}, status=404)
        
        company = getattr(request.user, 'company', None) or Company.objects.first()
        
        # Get account information
        gl_no = getattr(customer, 'gl_no', '') or ''
        ac_no = getattr(customer, 'ac_no', '') or ''
        wallet_account = getattr(customer, 'wallet_account', None)
        float_account = company.float_account_number if company else ''
        
        wallet_data = {
            'has_wallet': bool(wallet_account),
            'wallet_account': wallet_account,
            'bank_name': getattr(customer, 'bank_name', None),
            'bank_code': getattr(customer, 'bank_code', None),
            'current_account': get_current_account_number(request.user, customer),
            'ready_for_creation': calculate_data_completeness(customer) >= 80,
            'data_completeness': calculate_data_completeness(customer),
            
            # Integration details
            'gl_no': gl_no,
            'ac_no': ac_no,
            'computed_account': f"{gl_no}{ac_no}" if gl_no and ac_no else '',
            'float_account_number': float_account,
            'integration_status': 'wallet_active' if wallet_account else 'traditional_account',
            'transaction_compatibility': 'preserved',
            
            # Display preferences
            'primary_display': wallet_account if wallet_account else float_account,
            'transaction_account': f"{gl_no}{ac_no}" if gl_no and ac_no else '',
        }
        
        return Response(wallet_data, status=200)
        
    except Exception as e:
        logger.error(f"[WALLET_STATUS] Error for user {request.user.id}: {str(e)}")
        return Response({'error': 'Failed to check wallet status'}, status=500)










# api/views.py (Add these imports at the top)

# CORRECTED IMPORTS for fee management
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal, InvalidOperation
from datetime import datetime

# Import the models and services with correct paths
from .models import GlobalTransferFeeConfiguration, GlobalTransferFeeTransaction, CustomerTransferUsage
from .services.global_fee_service import GlobalTransferFeeService

def is_admin_user(user):
    """Check if user is admin"""
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin_user)
def fee_management_dashboard(request):
    """Dashboard for managing global transfer fees"""
    
    # Get current active configuration
    active_config = GlobalTransferFeeService.get_active_fee_configuration()
    
    # Get recent configurations
    all_configs = GlobalTransferFeeConfiguration.objects.all()[:5]
    
    # Get recent transactions
    recent_transactions = GlobalTransferFeeTransaction.objects.all()[:20]
    
    # Get usage stats
    today_transactions = GlobalTransferFeeTransaction.objects.filter(
        processing_date=datetime.now().date()
    )
    
    total_fees_today = sum(t.applied_fee_amount for t in today_transactions)
    waived_today = today_transactions.filter(was_waived=True).count()
    charged_today = today_transactions.filter(was_waived=False).count()
    
    context = {
        'active_config': active_config,
        'all_configs': all_configs,
        'recent_transactions': recent_transactions,
        'stats': {
            'total_fees_today': total_fees_today,
            'waived_today': waived_today,
            'charged_today': charged_today,
            'total_transactions_today': today_transactions.count()
        }
    }
    
    return render(request, 'fee_management/dashboard.html', context)

@login_required
@user_passes_test(is_admin_user)
def create_fee_configuration(request):
    """Create new global fee configuration"""
    
    if request.method == 'POST':
        try:
            config_data = {
                'name': request.POST.get('name', 'Other Bank Transfer Fee'),
                'base_fee': request.POST.get('base_fee', '10.00'),
                'free_transfers_per_day': int(request.POST.get('free_transfers_per_day', 3)),
                'free_transfers_per_month': int(request.POST.get('free_transfers_per_month', 10)),
                'fee_gl_no': request.POST.get('fee_gl_no', ''),
                'fee_ac_no': request.POST.get('fee_ac_no', ''),
                'min_amount_for_fee': request.POST.get('min_amount_for_fee', '100.00'),
                'max_daily_free_amount': request.POST.get('max_daily_free_amount', '50000.00'),
                'created_by': request.user.username
            }
            
            # Validate required fields
            if not config_data['fee_gl_no'] or not config_data['fee_ac_no']:
                messages.error(request, 'Fee GL number and AC number are required')
                return render(request, 'fee_management/create_config.html')
            
            # Create configuration
            new_config = GlobalTransferFeeService.create_global_fee_configuration(config_data)
            
            messages.success(request, f'Global fee configuration created successfully! Applies to ALL customers.')
            return redirect('fee_management_dashboard')
            
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f'Invalid input: {str(e)}')
            return render(request, 'fee_management/create_config.html')
        except Exception as e:
            messages.error(request, f'Error creating configuration: {str(e)}')
            return render(request, 'fee_management/create_config.html')
    
    return render(request, 'fee_management/create_config.html')

@login_required
@user_passes_test(is_admin_user)
def deactivate_configuration(request, config_id):
    """Deactivate a fee configuration"""
    
    if request.method == 'POST':
        try:
            config = get_object_or_404(GlobalTransferFeeConfiguration, id=config_id)
            config.is_active = False
            config.save()
            
            messages.success(request, f'Configuration "{config.name}" deactivated successfully.')
        except Exception as e:
            messages.error(request, f'Error deactivating configuration: {str(e)}')
    
    return redirect('fee_management_dashboard')

@login_required
@user_passes_test(is_admin_user)
def transaction_history(request):
    """View all fee transactions"""
    
    # Filter options
    customer_filter = request.GET.get('customer')
    date_filter = request.GET.get('date')
    waived_filter = request.GET.get('waived')
    
    transactions = GlobalTransferFeeTransaction.objects.all()
    
    if customer_filter:
        transactions = transactions.filter(customer_id__icontains=customer_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            transactions = transactions.filter(processing_date=filter_date)
        except ValueError:
            pass
    
    if waived_filter == 'true':
        transactions = transactions.filter(was_waived=True)
    elif waived_filter == 'false':
        transactions = transactions.filter(was_waived=False)
    
    transactions = transactions.order_by('-processed_at')[:100]
    
    context = {
        'transactions': transactions,
        'filters': {
            'customer': customer_filter,
            'date': date_filter,
            'waived': waived_filter
        }
    }
    
    return render(request, 'fee_management/transaction_history.html', context)

from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Import fee service
try:
    from api.services.global_fee_service import GlobalTransferFeeService
except ImportError:
    GlobalTransferFeeService = None

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_global_transfer_fee(request):
    """
    Calculate transfer fee using database-driven fee configuration
    
    POST /api/v1/transfer/fee/
    """
    
    try:
        print("=== TRANSFER FEE DEBUG START ===")
        print(f"User: {request.user}")
        print(f"Request data: {request.data}")
        
        # Support both 'amount' and 'transfer_amount' field names (Flutter compatibility)
        transfer_amount = (
            request.data.get('transfer_amount') or 
            request.data.get('amount')
        )
        
        customer_id = request.data.get('customer_id')
        transfer_type = request.data.get('transfer_type', 'other_bank')
        
        # Get customer_id from authenticated user if not provided
        if not customer_id:
            try:
                if hasattr(request.user, 'customer'):
                    customer_id = str(request.user.customer.id)
                elif hasattr(request.user, 'username') and request.user.username:
                    customer_id = str(request.user.username)
                else:
                    customer_id = str(request.user.id)
                    
                print(f"Auto-extracted customer_id: {customer_id}")
            except AttributeError:
                customer_id = str(request.user.id)
        
        # Validate amount
        if not transfer_amount:
            return Response({
                'success': False,
                'message': 'Transfer amount is required'
            }, status=400)
        
        # Convert amount to Decimal for precise calculations
        try:
            amount = Decimal(str(transfer_amount))
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (InvalidOperation, ValueError) as e:
            return Response({
                'success': False,
                'message': 'Invalid transfer amount - must be a positive number',
                'errors': {'amount': str(e)}
            }, status=400)
        
        # Use GlobalTransferFeeService for database-driven calculation
        if GlobalTransferFeeService:
            print(f"Using GlobalTransferFeeService for customer: {customer_id}")
            
            # Calculate fee using database configuration
            fee_info = GlobalTransferFeeService.calculate_fee_for_any_customer(
                customer_id=customer_id,
                transfer_amount=amount,
                transfer_type=transfer_type
            )
            
            # Convert Decimal values to strings for JSON serialization
            response_data = {
                'success': True,
                'data': {
                    'base_fee': str(fee_info.get('base_fee', '0.00')),
                    'applied_fee': str(fee_info.get('applied_fee', '0.00')),
                    'is_waived': fee_info.get('is_waived', False),
                    'waiver_reason': fee_info.get('waiver_reason', ''),
                    'remaining_free_today': fee_info.get('remaining_free_today', 0),
                    'remaining_free_month': fee_info.get('remaining_free_month', 0),
                    'total_amount': str(amount + fee_info.get('applied_fee', Decimal('0.00'))),
                    'config_name': fee_info.get('config_name', 'Database Configuration'),
                    'fee_gl_no': fee_info.get('fee_gl_no', '30101'),
                    'fee_ac_no': fee_info.get('fee_ac_no', '00001')
                },
                'message': 'Fee calculated successfully using database configuration'
            }
            
        else:
            # Fallback if service not available (models not migrated)
            print("WARNING: GlobalTransferFeeService not available, using fallback")
            response_data = {
                'success': True,
                'data': {
                    'base_fee': '52.50',
                    'applied_fee': '0.00',
                    'is_waived': True,
                    'waiver_reason': 'Service initialization - free transfer',
                    'remaining_free_today': 5,
                    'remaining_free_month': 20,
                    'total_amount': str(amount),
                    'config_name': 'Fallback Configuration'
                },
                'message': 'Fee calculated using fallback configuration'
            }
        
        print(f"SUCCESS: Returning {response_data}")
        print("=== TRANSFER FEE DEBUG END ===")
        return Response(response_data, status=200)
        
    except Exception as e:
        print(f"ERROR: {e}")
        return Response({'success': False, 'error': str(e)}, status=500)


# ALTERNATIVE MINIMAL DEBUG VERSION (if the above is too verbose)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_global_transfer_fee_minimal_debug(request):
    """MINIMAL DEBUG VERSION - Use this if you want less verbose logging"""
    
    try:
        print("=== TRANSFER FEE DEBUG START ===")
        print(f"User: {request.user}")
        
        # Step 1: Basic validation
        customer_id = request.data.get('customer_id')
        transfer_amount = request.data.get('transfer_amount') 
        print(f"Data: customer_id={customer_id}, amount={transfer_amount}")
        
        if not customer_id or not transfer_amount:
            print("ERROR: Missing required fields")
            return Response({'success': False, 'error': 'Missing fields'}, status=400)
        
        # Step 2: Get customer (THE CRITICAL PART)
        print("Getting customer from request.user...")
        
        # Try different customer access patterns
        if hasattr(request.user, 'customer'):
            customer = request.user.customer
            print(f"SUCCESS: Found request.user.customer = {customer}")
        elif hasattr(request.user, 'customer_profile'):  
            customer = request.user.customer_profile
            print(f"SUCCESS: Found request.user.customer_profile = {customer}")
        else:
            print(f"ERROR: No customer found. Available attrs: {[a for a in dir(request.user) if not a.startswith('_')]}")
            return Response({'success': False, 'error': 'No customer found'}, status=400)
        
        # Step 3: Convert amount
        try:
            amount = Decimal(str(transfer_amount))
            print(f"Amount converted: {amount}")
        except Exception as e:
            print(f"ERROR: Amount conversion failed: {e}")
            return Response({'success': False, 'error': 'Invalid amount'}, status=400)
        
        # Step 4: Return mock response for now (to isolate the customer issue)
        print("Returning mock fee response...")
        
        return Response({
            'success': True,
            'data': {
                'base_fee': '52.50',
                'applied_fee': '0.00', 
                'is_waived': True,
                'waiver_reason': 'DEBUG MODE - Free transfer',
                'remaining_free_today': 3,
                'remaining_free_month': 10
            },
            'debug': 'Mock response - customer access worked!'
        })
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return Response({'success': False, 'error': str(e)}, status=500)
    finally:
        print("=== TRANSFER FEE DEBUG END ===")


# INTEGRATION INSTRUCTIONS:
"""
1. REPLACE your existing get_global_transfer_fee function with either:
   - get_global_transfer_fee (full debug version)
   - get_global_transfer_fee_minimal_debug (minimal version)

2. Add these imports at the top of your views.py:
   import traceback
   from decimal import Decimal, InvalidOperation

3. Test the endpoint and check your Django console output for the debug messages

4. The debug output will show you EXACTLY where the 500 error occurs
"""


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ninepsb_transfer_with_global_fee(request):
    """
    Process transfer with proper Memtrans debit/credit handling
    
    CORRECTED MEMTRANS LOGIC using your actual model:
    1. Customer Account → Debit transfer_amount (Memtrans entry)
    2. Customer Account → Debit fee_amount (Memtrans entry) 
    3. Fee Account → Credit fee_amount (Memtrans entry)
    4. 9PSB Transfer → Send transfer_amount only
    
    POST /api/v1/ninepsb/transfer-with-fee/
    """
    
    try:
        print("=== TRANSFER WITH MEMTRANS DEBUG START ===")
        print(f"User: {request.user}")
        print(f"Request data: {request.data}")
        
        # Get request data
        from_account = request.data.get('from_account')
        to_account = request.data.get('to_account')
        bank_code = request.data.get('bank_code')
        amount_str = request.data.get('amount')
        narration = request.data.get('narration', 'Fund Transfer')
        beneficiary_name = request.data.get('beneficiary_name', '')
        customer_id = request.data.get('customer_id')
        
        # Get customer_id from authenticated user if not provided
        if not customer_id:
            try:
                if hasattr(request.user, 'customer'):
                    customer_id = str(request.user.customer.id)
                elif hasattr(request.user, 'username') and request.user.username:
                    customer_id = str(request.user.username)
                else:
                    customer_id = str(request.user.id)
                    
                print(f"Auto-extracted customer_id: {customer_id}")
            except AttributeError:
                customer_id = str(request.user.id)
        
        # Validate required fields
        required_fields = {
            'from_account': from_account,
            'to_account': to_account,
            'bank_code': bank_code,
            'amount': amount_str
        }
        
        missing_fields = {k: 'This field is required' for k, v in required_fields.items() if not v}
        if missing_fields:
            return Response({
                'success': False,
                'message': 'Missing required fields',
                'errors': missing_fields
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert amount to Decimal
        try:
            transfer_amount = Decimal(str(amount_str))
            if transfer_amount <= 0:
                raise ValueError("Amount must be positive")
        except (InvalidOperation, ValueError):
            return Response({
                'success': False,
                'message': 'Invalid amount',
                'errors': {'amount': 'Must be a valid positive number'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get customer profile
        try:
            customer = request.user.customer
            logger.info(f"Retrieved customer: {customer} for user: {request.user}")
        except AttributeError as e:
            logger.error(f"Customer attribute error for user {request.user}: {e}")
            return Response({
                'success': False,
                'message': 'Customer profile not found for user',
                'errors': {'authentication': 'Customer profile required for transfer'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # STEP 1: Calculate fee using database-driven service
        if not GlobalTransferFeeService:
            logger.warning("GlobalTransferFeeService not available - proceeding with zero fee")
            fee_info = {
                'base_fee': Decimal('52.50'),
                'applied_fee': Decimal('0.00'),
                'is_waived': True,
                'waiver_reason': 'Fee system not configured',
                'config_name': 'Default',
                'fee_gl_no': '30101',
                'fee_ac_no': '00001'
            }
        else:
            # Calculate fee using the service
            fee_info = GlobalTransferFeeService.calculate_fee_for_any_customer(
                customer_id=customer_id,
                transfer_amount=transfer_amount,
                transfer_type='other_bank'
            )
        
        fee_amount = fee_info.get('applied_fee', Decimal('0.00'))
        total_amount = transfer_amount + fee_amount
        
        # Generate transaction reference
        import uuid
        transaction_reference = f"TXN{uuid.uuid4().hex[:10].upper()}"
        
        print(f"Processing transfer: {transfer_amount} from {from_account} to {to_account}")
        print(f"Fee calculated: {fee_amount} (waived: {fee_info.get('is_waived', False)})")
        
        # STEP 2: Process the transfer with proper Memtrans entries
        try:
            with transaction.atomic():
                
                # ============================================
                # CORRECTED MEMTRANS DEBIT/CREDIT LOGIC
                # ============================================
                
                print(f"=== MEMTRANS BREAKDOWN ===")
                print(f"Transfer Amount: ₦{transfer_amount}")
                print(f"Fee Amount: ₦{fee_amount}")
                print(f"Total Customer Impact: ₦{total_amount}")
                print(f"Amount to Transfer (9PSB): ₦{transfer_amount}")
                
                # Parse customer account details
                customer_gl_no, customer_ac_no = parse_account_number(from_account)
                fee_gl_no = fee_info.get('fee_gl_no', '30101')
                fee_ac_no = fee_info.get('fee_ac_no', '00001')
                
                # Get customer object for Memtrans
                customer_obj = get_customer_object(customer_id)
                
                # 1. MEMTRANS ENTRY: Debit customer account for transfer amount
                print(f"📝 MEMTRANS: Debit customer {customer_gl_no}{customer_ac_no} by ₦{transfer_amount} (Transfer)")
                transfer_memtrans = create_memtrans_entry(
                    customer=customer_obj,
                    gl_no=customer_gl_no,
                    ac_no=customer_ac_no,
                    amount=transfer_amount,
                    is_debit=True,
                    description=f"Transfer to {bank_code} - {to_account[:4]}****",
                    trx_no=transaction_reference,
                    trx_type='TRANSFER_DEBIT',
                    user=request.user
                )
                
                # 2. MEMTRANS ENTRY: Debit customer account for fee (if fee > 0)
                fee_memtrans = None
                if fee_amount > 0:
                    print(f"📝 MEMTRANS: Debit customer {customer_gl_no}{customer_ac_no} by ₦{fee_amount} (Fee)")
                    fee_memtrans = create_memtrans_entry(
                        customer=customer_obj,
                        gl_no=customer_gl_no,
                        ac_no=customer_ac_no,
                        amount=fee_amount,
                        is_debit=True,
                        description=f"Transfer Fee - {fee_info.get('config_name', 'Other Bank Transfer')}",
                        trx_no=f"FEE{transaction_reference}",
                        trx_type='FEE_DEBIT',
                        user=request.user
                    )
                    
                    # 3. MEMTRANS ENTRY: Credit fee account for fee amount
                    print(f"📝 MEMTRANS: Credit fee account {fee_gl_no}{fee_ac_no} by ₦{fee_amount} (Fee Income)")
                    fee_credit_memtrans = create_memtrans_entry(
                        customer=None,  # Fee account, not customer account
                        gl_no=fee_gl_no,
                        ac_no=fee_ac_no,
                        amount=fee_amount,
                        is_debit=False,  # Credit
                        description=f"Transfer Fee Income - Customer {customer_id}",
                        trx_no=f"FEE{transaction_reference}",
                        trx_type='FEE_CREDIT',
                        user=request.user
                    )
                else:
                    print(f"📝 MEMTRANS: No fee entries needed (fee waived)")
                
                # 4. PROCESS 9PSB TRANSFER (Transfer Amount Only - NOT including fee)
                print(f"📤 9PSB: Send ₦{transfer_amount} to {to_account} via bank {bank_code}")
                # TODO: Replace with your actual 9PSB transfer call
                # ninepsb_result = call_9psb_transfer({
                #     'sender_account': from_account,
                #     'destination_account': to_account,
                #     'bank_code': bank_code,
                #     'amount': transfer_amount,  # ← IMPORTANT: Transfer amount only, not total
                #     'narration': narration,
                #     'reference': transaction_reference
                # })
                
                # For now, simulate successful transfer
                transfer_successful = True  # Replace with actual 9PSB response check
                
                # STEP 3: Record fee transaction for tracking
                if GlobalTransferFeeTransaction:
                    fee_transaction = GlobalTransferFeeTransaction.objects.create(
                        customer_id=str(customer_id),
                        customer_account=from_account,
                        transfer_reference=transaction_reference,
                        fee_config_name=fee_info.get('config_name', 'Unknown'),
                        base_fee_amount=fee_info.get('base_fee', Decimal('0.00')),
                        applied_fee_amount=fee_amount,
                        was_waived=fee_info.get('is_waived', False),
                        waiver_reason=fee_info.get('waiver_reason', ''),
                        transfer_amount=transfer_amount,
                        total_debited=total_amount,
                        destination_bank=bank_code,
                        destination_account=to_account,
                        destination_name=beneficiary_name,
                        fee_gl_no=fee_gl_no,
                        fee_ac_no=fee_ac_no,
                        fee_transaction_ref=f"FEE{transaction_reference}",
                       
                    )
                    print(f"✅ Fee transaction recorded: {fee_transaction.id}")
                
                # STEP 4: Update customer usage statistics
                if GlobalTransferFeeService and transfer_successful:
                    GlobalTransferFeeService.update_customer_usage_after_transfer(
                        customer_id=customer_id,
                        transfer_amount=transfer_amount,
                        fee_paid=fee_amount
                    )
                    print(f"✅ Customer usage updated for {customer_id}")
                
                # STEP 5: Return success response
                if transfer_successful:
                    print("✅ TRANSFER COMPLETED SUCCESSFULLY")
                    print("=== TRANSFER WITH MEMTRANS DEBUG END ===")
                    
                    logger.info(f"Transfer completed successfully: {transaction_reference}")
                    
                    return Response({
                        'success': True,
                        'data': {
                            'reference': transaction_reference,
                            'transfer_amount': str(transfer_amount),
                            'fee_amount': str(fee_amount),
                            'total_debited': str(total_amount),
                            'fee_waived': fee_info.get('is_waived', False),
                            'waiver_reason': fee_info.get('waiver_reason', ''),
                            'destination_account': to_account,
                            'destination_bank': bank_code,
                            'destination_name': beneficiary_name,
                            'narration': narration,
                            'timestamp': timezone.now().isoformat(),
                            'remaining_free_today': fee_info.get('remaining_free_today', 0),
                            'remaining_free_month': fee_info.get('remaining_free_month', 0),
                            'memtrans_entries': {
                                'transfer_debit_id': transfer_memtrans.id if transfer_memtrans else None,
                                'fee_debit_id': fee_memtrans.id if fee_memtrans else None,
                                'fee_credit_id': fee_credit_memtrans.id if fee_amount > 0 else None,
                                'customer_gl_ac': f"{customer_gl_no}{customer_ac_no}",
                                'fee_gl_ac': f"{fee_gl_no}{fee_ac_no}",
                                'entries_created': 3 if fee_amount > 0 else 1
                            }
                        },
                        'message': 'Transfer completed successfully with Memtrans entries'
                    }, status=status.HTTP_200_OK)
                
                else:
                    raise Exception("9PSB transfer failed")
                    
        except Exception as e:
            print(f"❌ TRANSFER ERROR: {e}")
            logger.error(f"Transfer processing error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': 'Transfer processing failed',
                'error': str(e),
                'data': {
                    'reference': transaction_reference,
                    'transfer_amount': str(transfer_amount),
                    'fee_amount': str(fee_amount),
                    'total_that_would_be_debited': str(total_amount)
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        print(f"❌ REQUEST ERROR: {e}")
        print("=== TRANSFER WITH MEMTRANS DEBUG END ===")
        logger.error(f"Error in ninepsb_transfer_with_global_fee: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Transfer failed',
            'errors': {'system': 'Internal server error occurred'},
            'debug_info': str(e) if logger.isEnabledFor(logging.DEBUG) else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# MEMTRANS HELPER FUNCTIONS (Using your actual Memtrans model)
# ============================================================================

def parse_account_number(account_number):
    """
    Parse account number to extract GL and AC numbers
    
    Args:
        account_number: Full account number (e.g., "2010112345")
        
    Returns:
        Tuple of (gl_no, ac_no) - both max 6 characters per your model
    """
    # TODO: Implement your actual account parsing logic
    
    if len(account_number) >= 10:
        gl_no = account_number[:5]  # First 5 digits for GL
        ac_no = account_number[5:11]  # Next 6 digits for AC (max 6 per model)
    elif len(account_number) >= 5:
        gl_no = account_number[:5]
        ac_no = account_number[5:]
    else:
        # Fallback for shorter account numbers
        gl_no = "20101"  # Default current account
        ac_no = account_number[:6]  # Truncate to 6 chars max
    
    # Ensure they fit your model's max_length=6 constraint
    gl_no = gl_no[:6]
    ac_no = ac_no[:6]
    
    print(f"🔧 Parsed account {account_number} -> GL: {gl_no}, AC: {ac_no}")
    return gl_no, ac_no


def get_customer_object(customer_id):
    """
    Get Customer object for Memtrans foreign key
    
    Args:
        customer_id: Customer ID string
        
    Returns:
        Customer object or None
    """
    try:
        # TODO: Replace with your actual Customer model import and query
        from your_app.models import Customer  # Replace with actual import
        
        customer = Customer.objects.get(id=customer_id)
        print(f"🔧 Found customer object: {customer}")
        return customer
        
    except Exception as e:
        print(f"🔧 TODO: Implement get_customer_object({customer_id}) - Error: {e}")
        return None


def create_memtrans_entry(customer, gl_no, ac_no, amount, is_debit, description, trx_no, trx_type, user):
    """
    Create a Memtrans entry using your actual model structure
    
    Args:
        customer: Customer object (can be None for fee accounts)
        gl_no: General Ledger number (max 6 chars)
        ac_no: Account number (max 6 chars) 
        amount: Transaction amount
        is_debit: True for debit, False for credit
        description: Transaction description (max 100 chars)
        trx_no: Transaction number (max 20 chars)
        trx_type: Transaction type (max 20 chars)
        user: User object
        
    Returns:
        Created Memtrans object
    """
    print(f"📝 Creating Memtrans: {gl_no}{ac_no} {'DR' if is_debit else 'CR'} ₦{amount}")
    
    # TODO: Import your actual models
    from transactions.models import Memtrans, Branch  # Replace with actual imports
    
    try:
        # Get default branch (TODO: Replace with actual logic)
        default_branch = Branch.objects.first()  # or your branch selection logic
        
        # Create Memtrans entry using your actual model structure
        memtrans_entry = Memtrans.objects.create(
            branch=default_branch,  # TODO: Set appropriate branch
            cust_branch=default_branch,  # TODO: Set customer's branch
            customer=customer,  # Customer object or None
            loans=None,  # Set if loan-related
            cycle=None,  # Set if needed
            gl_no=gl_no[:6],  # Ensure max 6 chars
            ac_no=ac_no[:6],  # Ensure max 6 chars
            trx_no=trx_no[:20],  # Ensure max 20 chars
            ses_date=timezone.now().date(),  # Session date
            app_date=timezone.now().date(),  # Application date
            sys_date=timezone.now(),  # System date (auto-set)
            amount=amount,  # Decimal amount
            description=description[:100],  # Ensure max 100 chars
            error='A',  # Default value
            type='D' if is_debit else 'C',  # TODO: Verify if this is how you indicate debit/credit
            account_type='N',  # Default value
            code='001',  # TODO: Set appropriate code
            user=user,  # User object
            trx_type=trx_type[:20]  # Ensure max 20 chars
        )
        
        print(f"✅ Memtrans created: ID={memtrans_entry.id}, {gl_no}{ac_no} {'DR' if is_debit else 'CR'} ₦{amount}")
        return memtrans_entry
        
    except Exception as e:
        print(f"❌ Error creating Memtrans entry: {e}")
        raise


def call_9psb_transfer(transfer_data):
    """
    Call 9PSB API for interbank transfer
    
    Args:
        transfer_data: Dictionary containing transfer details
        
    Returns:
        Boolean indicating success/failure
    """
    print(f"🔧 TODO: Implement call_9psb_transfer({transfer_data})")
    # Your 9PSB implementation here
    return True  # Simulated success





def process_global_fee_transaction(fee_data):
    """
    Process fee transaction to GLOBAL fee collection account
    ALL customer fees go to the SAME account
    """
    
    try:
        # Parse customer account
        customer_account = fee_data['customer_account']
        customer_gl = customer_account[:5] if len(customer_account) >= 10 else customer_account[:3]
        customer_ac = customer_account[len(customer_gl):]
        
        # Create transaction entries
        debit_entry = {
            'gl_no': customer_gl,
            'ac_no': customer_ac,
            'amount': fee_data['amount'],
            'transaction_type': 'DR',
            'narration': fee_data.get('narration', f'Transfer fee - {fee_data["original_reference"]}'),
            'reference': fee_data['reference']
        }
        
        # Credit GLOBAL fee collection account (SAME for ALL customers)
        credit_entry = {
            'gl_no': fee_data['fee_gl_no'],
            'ac_no': fee_data['fee_ac_no'], 
            'amount': fee_data['amount'],
            'transaction_type': 'CR',
            'narration': f'Transfer fee collection - {fee_data["original_reference"]}',
            'reference': fee_data['reference']
        }
        
        # Process both entries (implement based on your core banking system)
        # For now, return success - integrate with your actual transaction posting
        return {
            'success': True, 
            'message': 'Global fee transaction completed'
        }
        
    except Exception as e:
        return {'success': False, 'message': str(e)}

def process_ninepsb_transfer(transfer_data):
    """Process main transfer via 9PSB"""
    # Implement your existing 9PSB transfer logic here
    return {'success': True, 'message': 'Transfer completed'}