# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import update_session_auth_hash
from accounts.models import User
from rest_framework.permissions import AllowAny
from .serializers import (
    LoginSerializer, ActivationSerializer, 
    ChangePasswordSerializer, ForgotPasswordSerializer
)

class LoginView(APIView):
    authentication_classes = []   # 👈 Disable JWT on login
    permission_classes = []  
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        # Customer must activate first
        if user.role == User.CUSTOMER and not user.verified:
            return Response({"message": "Activation code required"}, status=status.HTTP_202_ACCEPTED)

        # Otherwise issue token
        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        })


class ActivateView(APIView):
    permission_classes = [AllowAny] 
    def post(self, request):
        serializer = ActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        user.verified = True
        user.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Activation successful",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        })


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        update_session_auth_hash(request, user)
        return Response({"message": "Password changed successfully"})


class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
            # Generate OTP / send email here
            return Response({"message": "Password reset instructions sent"})
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get("refresh"))
            token.blacklist()
            return Response({"message": "Logged out successfully"})
        except Exception:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)








# customers/views.py

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from customers.models import Customer, KYCDocument
from .serializers import CustomerProfileSerializer, CustomerUpdateSerializer, KYCDocumentUploadSerializer


class CustomerProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'customer') or not user.customer:
            return Response({"error": "No customer profile linked to this user."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CustomerProfileSerializer(user.customer)
        return Response(serializer.data)


class CustomerUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        if not hasattr(user, 'customer') or not user.customer:
            return Response({"error": "No customer profile found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CustomerUpdateSerializer(user.customer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KYCDocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not hasattr(user, 'customer') or not user.customer:
            return Response({"error": "No customer profile found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = KYCDocumentUploadSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(customer=user.customer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)







# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from transactions.models import Memtrans
from accounts.models import Account
from customers.models import Customer
# views.py

from .serializers import CustomerAccountSerializer

class CustomerAccountsAPIView(APIView):
    """
    List all accounts (sub-accounts by GL) for a customer.
    
    Query Parameters:
    - ac_no: Customer account number (required)
    - branch_id: Branch ID (required)
    
    Returns:
    - List of accounts with gl_no, account_name, category, balance, available_funds, status
    """
    def get(self, request):
        ac_no = request.query_params.get('ac_no')
        branch_id = request.query_params.get('branch_id')

        if not ac_no or not branch_id:
            return Response(
                {"error": "Both 'ac_no' and 'branch_id' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Safely fetch customer(s) — handle duplicates gracefully
        customers = Customer.objects.filter(
            ac_no=ac_no,
            branch_id=branch_id
        )

        if not customers.exists():
            return Response(
                {"error": "Customer not found with the given ac_no and branch_id."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Use the first customer (in case of duplicates due to data model issue)
        customer = customers.first()

        # Get all distinct GL accounts used by this customer in this branch
        gl_nos = Memtrans.objects.filter(
            ac_no=ac_no,
            branch_id=branch_id,
            error='A'  # Only valid/active transactions
        ).values_list('gl_no', flat=True).distinct()

        if not gl_nos:
            # Customer exists but has no transactions yet
            return Response([])

        accounts_data = []

        for gl_no in gl_nos:
            # Calculate net balance from transactions
            balance = Memtrans.objects.filter(
                ac_no=ac_no,
                gl_no=gl_no,
                branch_id=branch_id,
                error='A'
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Get GL master info
            try:
                gl_account = Account.objects.get(gl_no=gl_no)
                account_name = gl_account.product_type.internal_type if gl_account.product_type else "UNKNOWN"
                category = gl_account.get_account_type_display()
            except Account.DoesNotExist:
                account_name = "INVALID_GL"
                category = "Other"

            accounts_data.append({
                "gl_no": gl_no,
                "account_name": account_name,
                "category": category,
                "balance": balance,
                "available_funds": balance,  # Extend later if you add holds/limits
                "status": customer.get_status_display() or "Active"
            })

        serializer = CustomerAccountSerializer(accounts_data, many=True)
        return Response(serializer.data)





# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from customers.models import Customer
from .serializers import AccountDetailsSerializer

class AccountDetailsAPIView(APIView):
    def get(self, request):
        ac_no = request.query_params.get('ac_no')
        branch_id = request.query_params.get('branch_id')
        gl_no = request.query_params.get('gl_no')  # Optional

        if not ac_no or not branch_id:
            return Response(
                {"error": "ac_no and branch_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        customers = Customer.objects.select_related(
            'branch', 'credit_officer'
        ).filter(
            ac_no=ac_no,
            branch_id=branch_id
        )

        if not customers.exists():
            return Response(
                {"error": "Account not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        customer = customers.first()

        # Pass gl_no to serializer context if provided
        context = {'gl_no': gl_no} if gl_no else {}
        serializer = AccountDetailsSerializer(customer, context=context)
        return Response(serializer.data)





# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
from transactions.models import Memtrans
from .serializers import TransactionSerializer

class TransactionHistoryAPIView(APIView):
    """
    Transaction History API
    
    Query Params:
    - ac_no (required)
    - branch_id (required)
    - gl_no (optional) → if omitted, returns all GLs for this customer
    - start_date (optional, format: YYYY-MM-DD)
    - end_date (optional, format: YYYY-MM-DD)
    - limit (optional, default=10, max=100) → for mini-statement

    Behavior:
    - If start_date/end_date provided → full statement (date range)
    - Else → mini-statement (last N transactions)
    """
    def get(self, request):
        ac_no = request.query_params.get('ac_no')
        branch_id = request.query_params.get('branch_id')
        gl_no = request.query_params.get('gl_no')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = request.query_params.get('limit', 10)

        # Validate required params
        if not ac_no or not branch_id:
            return Response(
                {"error": "ac_no and branch_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            limit = min(int(limit), 100)  # Cap at 100 for safety
        except (TypeError, ValueError):
            limit = 10

        # Build base queryset
        queryset = Memtrans.objects.filter(
            ac_no=ac_no,
            branch_id=branch_id,
            error='A'
        ).order_by('-ses_date', '-id')  # Newest first

        # Filter by gl_no if provided
        if gl_no:
            queryset = queryset.filter(gl_no=gl_no)

        # Date range filter (full statement)
        if start_date or end_date:
            if start_date:
                start = parse_date(start_date)
                if start:
                    queryset = queryset.filter(ses_date__gte=start)
            if end_date:
                end = parse_date(end_date)
                if end:
                    queryset = queryset.filter(ses_date__lte=end)
        else:
            # Mini-statement: limit to last N transactions
            queryset = queryset[:limit]

        # Serialize
        serializer = TransactionSerializer(queryset, many=True)
        return Response(serializer.data)





# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from .serializers import BalanceEnquirySerializer 



class BalanceEnquiryAPIView(APIView):
    def get(self, request):
        ac_no = request.query_params.get('ac_no')
        branch_id = request.query_params.get('branch_id')
        gl_no = request.query_params.get('gl_no')  # Optional

        if not ac_no or not branch_id:
            return Response(
                {"error": "ac_no and branch_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate customer exists
        customers = Customer.objects.filter(ac_no=ac_no, branch_id=branch_id)
        if not customers.exists():
            return Response({"error": "Account not found"}, status=status.HTTP_404_NOT_FOUND)
        customer = customers.first()

        # Calculate balance
        base_filter = dict(ac_no=ac_no, branch_id=branch_id, error='A')
        if gl_no:
            balance = Memtrans.objects.filter(gl_no=gl_no, **base_filter).aggregate(
                total=Sum('amount')
            )['total'] or 0
            response_gl_no = gl_no
        else:
            balance = Memtrans.objects.filter(**base_filter).aggregate(
                total=Sum('amount')
            )['total'] or 0
            response_gl_no = None  # or omit if you prefer

        data = {
            "account_number": ac_no,
            "gl_no": response_gl_no,        # ✅ Always included
            "balance": balance,
            "available_funds": balance,
            "status": customer.get_status_display() or "Active"
        }

        serializer = BalanceEnquirySerializer(data)
        return Response(serializer.data)







# api/views.py

from .serializers import DepositPostingSerializer, DepositHistorySerializer  # ✅ Import

# api/views.py


# api/views.py
class DepositPostingAPIView(APIView):
    def post(self, request):
        ac_no = request.data.get('ac_no')
        branch_id = request.data.get('branch_id')
        gl_no = request.data.get('gl_no')  # ← REQUIRED to identify the account
        amount = request.data.get('amount')
        description = request.data.get('description', 'Deposit')

        if not all([ac_no, branch_id, gl_no, amount]):
            return Response({"error": "ac_no, branch_id, gl_no, amount required"}, status=400)

        try:
            amount = float(amount)
            if amount <= 0:
                return Response({"error": "Amount must be positive"}, status=400)
        except (TypeError, ValueError):
            return Response({"error": "Invalid amount"}, status=400)

        # ✅ KEY CHANGE: Filter by ac_no + branch + gl_no
        try:
            customer = Customer.objects.get(
                ac_no=ac_no,
                branch_id=branch_id,
                gl_no=gl_no  # ← This makes it unique!
            )
        except Customer.DoesNotExist:
            return Response({"error": "Account not found"}, status=404)

        # ... rest of deposit logic (same as before)

class DepositHistoryAPIView(APIView):
    def get(self, request):
        ac_no = request.query_params.get('ac_no')
        branch_id = request.query_params.get('branch_id')

        if not ac_no or not branch_id:
            return Response(
                {"error": "ac_no and branch_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        deposits = Memtrans.objects.filter(
            ac_no=ac_no,
            branch_id=branch_id,
            trx_type='DEPOSIT',
            error='A'
        ).order_by('-ses_date')

        # Serialize with DepositHistorySerializer
        data = DepositHistorySerializer(deposits, many=True).data
        return Response(data)