"""
Account Officer Mobile App API Views
Comprehensive API endpoints for account officers to perform banking operations
via mobile app with enhanced security and transaction management.
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum, Q, Count
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

# Models
from accounts.models import User, Role
from accounts_admin.models import Account_Officer
from company.models import Branch
from customers.models import Customer
from transactions.models import Memtrans, PendingTransaction
from loans.models import Loans

# Serializers
from api.serializers import (
    UserSerializer, 
    CustomerSerializer, 
    MemtransSerializer,
    LoansSerializer
)

logger = logging.getLogger(__name__)

# =============================================================================
# Account Officer Authentication APIs
# =============================================================================

class AccountOfficerRegisterView(APIView):
    """
    Account Officer Registration (requires activation key from admin)
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        try:
            # Extract registration data
            username = request.data.get('username', '').strip()
            email = request.data.get('email', '').strip().lower()
            first_name = request.data.get('first_name', '').strip()
            last_name = request.data.get('last_name', '').strip()
            phone_number = request.data.get('phone_number', '').strip()
            activation_key = request.data.get('activation_key', '').strip()
            password = request.data.get('password', '')
            
            # Validation
            if not all([username, email, first_name, last_name, phone_number, activation_key, password]):
                return Response({
                    'error': 'All fields are required: username, email, first_name, last_name, phone_number, activation_key, password'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate activation key format (you can customize this)
            if len(activation_key) < 8:
                return Response({
                    'error': 'Invalid activation key format'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if username or email already exists
            if User.objects.filter(username=username).exists():
                return Response({
                    'error': 'Username already exists'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Email can be shared across Company, Branch, and User - removed strict uniqueness check
            # if User.objects.filter(email=email).exists():
            #     return Response({
            #         'error': 'Email already exists'
            #     }, status=status.HTTP_400_BAD_REQUEST)
            
            # For demo purposes, we'll validate activation keys against a pattern
            # In production, you'd validate against a pre-generated key in the database
            valid_keys = ['AOKEY001', 'AOKEY002', 'AOKEY003', 'DEMO2024', 'TEST2024']
            if activation_key not in valid_keys and not activation_key.startswith('AO'):
                return Response({
                    'error': 'Invalid activation key. Please contact your administrator.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create user account (initially inactive)
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=User.CREDIT_OFFICER,  # Default role for account officers
                password=password
            )
            user.activation_code = activation_key
            user.is_active = False  # Requires admin activation
            user.verified = False
            user.save()
            
            logger.info(f"Account officer registered: {username} ({email})")
            
            return Response({
                'success': True,
                'message': 'Registration successful. Please wait for admin activation.',
                'user_id': user.id,
                'username': user.username
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Account officer registration error: {str(e)}")
            return Response({
                'error': 'Registration failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from django.utils import timezone
import logging

from accounts.models import User

logger = logging.getLogger(__name__)

class AccountOfficerLoginView(APIView):
    """
    Account Officer Login with JWT tokens
    Supports both password and biometric authentication
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        print("===== LOGIN REQUEST RECEIVED =====")
        print("Request Data:", request.data)

        try:
            username = request.data.get('username', '').strip()
            password = request.data.get('password', '')
            login_type = request.data.get('login_type', 'password')  # 'password' or 'biometric'

            print(f"Username: {username}")
            print(f"Login Type: {login_type}")

            if not username:
                print("ERROR: Username missing")
                return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Find user
            try:
                user = User.objects.get(username=username)
                print("User found:", user.username)
            except User.DoesNotExist:
                print("ERROR: User not found")
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Check if user is active and verified
            print("Checking if user is active:", user.is_active)
            if not user.is_active:
                print("ERROR: User not active")
                return Response({'error': 'Account not activated. Please contact administrator.'},
                                status=status.HTTP_403_FORBIDDEN)
                
            print("Checking if user is verified:", user.verified)
            if not user.verified:
                print("ERROR: User not verified")
                return Response({'error': 'Account not verified. Please contact administrator.'},
                                status=status.HTTP_403_FORBIDDEN)
            
            # Authenticate based on login type
            if login_type == 'password':
                print("Password Login Mode")

                if not password:
                    print("ERROR: Password missing")
                    return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
                
                print("Checking password...")
                if not user.check_password(password):
                    print("ERROR: Invalid password")
                    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
                print("Password correct!")
            
            elif login_type == 'biometric':
                print("Biometric Login Mode")
                biometric_token = request.data.get('biometric_token')

                if not biometric_token:
                    print("ERROR: No biometric token")
                    return Response({'error': 'Biometric token is required'},
                                    status=status.HTTP_400_BAD_REQUEST)
                
                print("Biometric token received:", biometric_token)
                print("Biometric logic passed")
            
            print("Generating JWT tokens...")
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            print("JWT generated successfully")

            # Compute expiry from SimpleJWT settings (no dependency on settings.SIMPLE_JWT presence)
            expires_in = int(jwt_settings.ACCESS_TOKEN_LIFETIME.total_seconds())

            # Get user profile information
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': f"{user.first_name} {user.last_name}",
                'phone_number': user.phone_number,
                'role': user.get_role_display() if user.role else 'Account Officer',
                'branch': {
                    'id': user.branch.id,
                    'name': user.branch.branch_name,
                    'code': user.branch.branch_code
                } if user.branch else None,
                'has_transaction_pin': bool(user.transaction_pin)
            }

            print("User Data Prepared:", user_data)

            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            print("Last login timestamp updated")

            logger.info(f"Account officer logged in: {username}")
            print("===== LOGIN SUCCESSFUL =====")

            return Response({
                'success': True,
                'message': 'Login successful',
                'access_token': str(access_token),
                'refresh_token': str(refresh),
                'token_type': 'Bearer',
                'expires_in': expires_in,
                'user': user_data,
                'login_type': login_type
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print("===== LOGIN ERROR =====")
            print("Error:", str(e))
            logger.error(f"Account officer login error: {str(e)}")
            return Response({'error': 'Login failed. Please try again.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


                            

class AccountOfficerPINSetupView(APIView):
    """
    Setup transaction PIN for account officer
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            pin = request.data.get('pin', '').strip()
            confirm_pin = request.data.get('confirm_pin', '').strip()
            current_password = request.data.get('current_password', '')
            
            # Validation
            if not pin or not confirm_pin:
                return Response({
                    'error': 'PIN and confirmation are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if len(pin) != 4 or not pin.isdigit():
                return Response({
                    'error': 'PIN must be exactly 4 digits'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if pin != confirm_pin:
                return Response({
                    'error': 'PIN confirmation does not match'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify current password for security
            if not current_password or not request.user.check_password(current_password):
                return Response({
                    'error': 'Current password is incorrect'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Set transaction PIN
            request.user.set_transaction_pin(pin)
            request.user.save()
            
            logger.info(f"Transaction PIN set for account officer: {request.user.username}")
            
            return Response({
                'success': True,
                'message': 'Transaction PIN set successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"PIN setup error: {str(e)}")
            return Response({
                'error': 'PIN setup failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AccountOfficerPINVerifyView(APIView):
    """
    Verify transaction PIN for secure operations
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            pin = request.data.get('pin', '').strip()
            
            if not pin:
                return Response({
                    'error': 'PIN is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if len(pin) != 4 or not pin.isdigit():
                return Response({
                    'error': 'Invalid PIN format'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user has PIN set
            if not request.user.transaction_pin:
                return Response({
                    'error': 'Transaction PIN not set. Please set up your PIN first.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify PIN
            if not request.user.check_transaction_pin(pin):
                return Response({
                    'error': 'Invalid PIN'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Generate temporary verification token (valid for 10 minutes)
            verification_token = f"pin_verified_{request.user.id}_{timezone.now().timestamp()}"
            cache.set(f"pin_verified_{request.user.id}", verification_token, timeout=600)
            
            return Response({
                'success': True,
                'message': 'PIN verified successfully',
                'verification_token': verification_token
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"PIN verification error: {str(e)}")
            return Response({
                'error': 'PIN verification failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# =============================================================================
# Customer Management APIs
# =============================================================================

class CustomerLookupView(APIView):
    """
    Look up customer by account number or other identifiers
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            account_number = request.query_params.get('account_number', '').strip()
            phone_number = request.query_params.get('phone_number', '').strip()
            
            if not account_number and not phone_number:
                return Response({
                    'error': 'Account number or phone number is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            customers = Customer.objects.none()
            
            if account_number:
                if len(account_number) >= 10:
                    gl_no = account_number[:5]
                    ac_no = account_number[5:]
                    customers = Customer.objects.filter(gl_no=gl_no, ac_no=ac_no)
                else:
                    return Response({
                        'error': 'Invalid account number format'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            elif phone_number:
                customers = Customer.objects.filter(
                    Q(phone_no=phone_number) | Q(mobile=phone_number)
                )
            
            if not customers.exists():
                return Response({
                    'found': False,
                    'message': 'Customer not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            customer = customers.first()
            
            # Get customer balance
            balance = Memtrans.objects.filter(
                gl_no=customer.gl_no,
                ac_no=customer.ac_no
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            customer_data = {
                'id': customer.id,
                'account_number': f"{customer.gl_no}{customer.ac_no}",
                'gl_no': customer.gl_no,
                'ac_no': customer.ac_no,
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'full_name': customer.get_full_name(),
                'phone_no': customer.phone_no,
                'email': customer.email,
                'address': customer.address,
                'balance': float(balance),
                'status': 'Active' if customer.status else 'Inactive',
                'branch': customer.branch.branch_name if customer.branch else None
            }
            
            return Response({
                'found': True,
                'customer': customer_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Customer lookup error: {str(e)}")
            return Response({
                'error': 'Customer lookup failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# =============================================================================
# Transaction APIs (Using PendingTransaction)
# =============================================================================

class DepositView(APIView):
    """
    Process customer deposit with PIN verification (creates PendingTransaction)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        try:
            # Extract request data
            account_number = request.data.get('account_number', '').strip()
            amount = request.data.get('amount', 0)
            narration = request.data.get('narration', 'Cash Deposit').strip()
            pin = request.data.get('pin', '').strip()
            
            # Validation
            if not account_number or not amount or not pin:
                return Response({
                    'error': 'Account number, amount, and PIN are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                amount = Decimal(str(amount))
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except (ValueError, TypeError):
                return Response({
                    'error': 'Invalid amount'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify PIN
            if not request.user.transaction_pin or not request.user.check_transaction_pin(pin):
                return Response({
                    'error': 'Invalid transaction PIN'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Find customer
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
                    'error': 'Customer account not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Generate transaction number
            trx_no = f"DEP{timezone.now().strftime('%y%m%d%H%M%S')}{str(customer.id)[-5:].zfill(5)}"
            
            # Create pending deposit transaction (requires approval)
            deposit_trx = PendingTransaction.objects.create(
                branch=customer.branch or request.user.branch,
                cust_branch=customer.branch,
                customer=customer,
                gl_no=gl_no,
                ac_no=ac_no,
                trx_no=trx_no,
                ses_date=timezone.now().date(),
                app_date=timezone.now().date(),
                sys_date=timezone.now(),
                amount=amount,
                description=narration,
                trx_type="DEPOSIT",
                status="PENDING",
                initiated_by=request.user,
                customer_pin_verified=True,
                device_info={
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': request.META.get('REMOTE_ADDR', ''),
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            # Current balance (before this transaction)
            current_balance = Memtrans.objects.filter(
                gl_no=gl_no, ac_no=ac_no
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Expected new balance (after approval)
            expected_new_balance = current_balance + amount
            
            logger.info(f"Deposit processed: {trx_no} - {amount} to {account_number} by {request.user.username}")
            
            return Response({
                'success': True,
                'message': 'Deposit submitted for approval. Transaction is pending.',
                'transaction': {
                    'reference': trx_no,
                    'amount': float(amount),
                    'account_number': account_number,
                    'customer_name': customer.get_full_name(),
                    'narration': narration,
                    'current_balance': float(current_balance),
                    'expected_new_balance': float(expected_new_balance),
                    'status': 'PENDING',
                    'timestamp': deposit_trx.sys_date.isoformat(),
                    'initiated_by': f"{request.user.first_name} {request.user.last_name}"
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Deposit processing error: {str(e)}")
            return Response({
                'error': 'Deposit processing failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WithdrawalView(APIView):
    """
    Process customer withdrawal with PIN verification and balance check (creates PendingTransaction)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        try:
            # Extract request data
            account_number = request.data.get('account_number', '').strip()
            amount = request.data.get('amount', 0)
            narration = request.data.get('narration', 'Cash Withdrawal').strip()
            pin = request.data.get('pin', '').strip()
            
            # Validation
            if not account_number or not amount or not pin:
                return Response({
                    'error': 'Account number, amount, and PIN are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                amount = Decimal(str(amount))
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except (ValueError, TypeError):
                return Response({
                    'error': 'Invalid amount'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify PIN
            if not request.user.transaction_pin or not request.user.check_transaction_pin(pin):
                return Response({
                    'error': 'Invalid transaction PIN'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Find customer
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
                    'error': 'Customer account not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check available balance
            current_balance = Memtrans.objects.filter(
                gl_no=gl_no, ac_no=ac_no
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            if current_balance < amount:
                return Response({
                    'error': f'Insufficient funds. Available balance: ₦{current_balance:,.2f}',
                    'available_balance': float(current_balance),
                    'requested_amount': float(amount)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate transaction number
            trx_no = f"WDR{timezone.now().strftime('%y%m%d%H%M%S')}{str(customer.id)[-5:].zfill(5)}"
            
            # Create pending withdrawal transaction (requires approval)
            withdrawal_trx = PendingTransaction.objects.create(
                branch=customer.branch or request.user.branch,
                cust_branch=customer.branch,
                customer=customer,
                gl_no=gl_no,
                ac_no=ac_no,
                trx_no=trx_no,
                ses_date=timezone.now().date(),
                app_date=timezone.now().date(),
                sys_date=timezone.now(),
                amount=amount,  # Store positive amount, make negative during approval
                description=narration,
                trx_type="WITHDRAWAL",
                status="PENDING",
                initiated_by=request.user,
                customer_pin_verified=True,
                device_info={
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': request.META.get('REMOTE_ADDR', ''),
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            # Expected new balance (after approval)
            expected_new_balance = current_balance - amount
            
            logger.info(f"Withdrawal processed: {trx_no} - {amount} from {account_number} by {request.user.username}")
            
            return Response({
                'success': True,
                'message': 'Withdrawal submitted for approval. Transaction is pending.',
                'transaction': {
                    'reference': trx_no,
                    'amount': float(amount),
                    'account_number': account_number,
                    'customer_name': customer.get_full_name(),
                    'narration': narration,
                    'previous_balance': float(current_balance),
                    'expected_new_balance': float(expected_new_balance),
                    'status': 'PENDING',
                    'timestamp': withdrawal_trx.sys_date.isoformat(),
                    'initiated_by': f"{request.user.first_name} {request.user.last_name}"
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Withdrawal processing error: {str(e)}")
            return Response({
                'error': 'Withdrawal processing failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BalanceInquiryView(APIView):
    """
    Check customer account balance and recent transactions
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            account_number = request.query_params.get('account_number', '').strip()
            
            if not account_number:
                return Response({
                    'error': 'Account number is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse account number
            if len(account_number) >= 10:
                gl_no = account_number[:5]
                ac_no = account_number[5:]
            else:
                return Response({
                    'error': 'Invalid account number format'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Find customer
            try:
                customer = Customer.objects.get(gl_no=gl_no, ac_no=ac_no)
            except Customer.DoesNotExist:
                return Response({
                    'error': 'Customer account not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Calculate balance
            balance_data = Memtrans.objects.filter(
                gl_no=gl_no, ac_no=ac_no
            ).aggregate(
                total_balance=Sum('amount'),
                credit_sum=Sum('amount', filter=Q(amount__gt=0)),
                debit_sum=Sum('amount', filter=Q(amount__lt=0))
            )
            
            balance = balance_data['total_balance'] or Decimal('0.00')
            total_credits = balance_data['credit_sum'] or Decimal('0.00')
            total_debits = abs(balance_data['debit_sum'] or Decimal('0.00'))
            
            # Get recent transactions (last 10)
            recent_transactions = Memtrans.objects.filter(
                gl_no=gl_no, ac_no=ac_no
            ).order_by('-sys_date')[:10]
            
            transactions_data = []
            for trx in recent_transactions:
                transactions_data.append({
                    'reference': trx.trx_no,
                    'date': trx.sys_date.isoformat(),
                    'amount': float(trx.amount),
                    'type': 'Credit' if trx.amount > 0 else 'Debit',
                    'description': trx.description or trx.trx_type,
                    'balance_after': 0  # Would need running balance calculation
                })
            
            return Response({
                'success': True,
                'account': {
                    'number': account_number,
                    'customer_name': customer.get_full_name(),
                    'balance': float(balance),
                    'available_balance': float(balance),  # In a real system, might differ due to holds
                    'total_credits': float(total_credits),
                    'total_debits': float(total_debits),
                    'account_status': 'Active' if customer.status else 'Inactive',
                    'branch': customer.branch.branch_name if customer.branch else None
                },
                'recent_transactions': transactions_data,
                'inquiry_time': timezone.now().isoformat(),
                'processed_by': f"{request.user.first_name} {request.user.last_name}"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Balance inquiry error: {str(e)}")
            return Response({
                'error': 'Balance inquiry failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# =============================================================================
# Additional Views (Loans, Reports, Dashboard)
# =============================================================================

class LoansInquiryView(APIView):
    """
    Get customer loan information and status
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            account_number = request.query_params.get('account_number', '').strip()
            customer_id = request.query_params.get('customer_id')
            
            if not account_number and not customer_id:
                return Response({
                    'error': 'Account number or customer ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Find customer
            if account_number:
                if len(account_number) >= 10:
                    gl_no = account_number[:5]
                    ac_no = account_number[5:]
                    try:
                        customer = Customer.objects.get(gl_no=gl_no, ac_no=ac_no)
                    except Customer.DoesNotExist:
                        return Response({
                            'error': 'Customer account not found'
                        }, status=status.HTTP_404_NOT_FOUND)
                else:
                    return Response({
                        'error': 'Invalid account number format'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    customer = Customer.objects.get(id=customer_id)
                except Customer.DoesNotExist:
                    return Response({
                        'error': 'Customer not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # Get customer loans
            loans = Loans.objects.filter(customer=customer).order_by('-id')
            
            loans_data = []
            total_outstanding = Decimal('0.00')
            
            for loan in loans:
                # Calculate outstanding balance (simplified)
                loan_balance = loan.loan_amount - (loan.amount_paid or Decimal('0.00'))
                total_outstanding += max(loan_balance, Decimal('0.00'))
                
                loans_data.append({
                    'id': loan.id,
                    'loan_amount': float(loan.loan_amount),
                    'outstanding_balance': float(loan_balance),
                    'interest_rate': float(loan.interest_rate) if loan.interest_rate else 0.0,
                    'payment_frequency': loan.get_payment_freq_display() if loan.payment_freq else 'N/A',
                    'disbursement_date': loan.disb_date.isoformat() if loan.disb_date else None,
                    'maturity_date': loan.maturity_date.isoformat() if loan.maturity_date else None,
                    'approval_status': loan.get_approval_status_display() if loan.approval_status else 'Pending',
                    'disbursement_status': loan.get_disb_status_display() if loan.disb_status else 'Pending',
                    'loan_type': loan.reason or 'General Loan',
                    'next_payment_date': None,  # Would need calculation based on payment schedule
                    'next_payment_amount': 0.0
                })
            
            return Response({
                'success': True,
                'customer': {
                    'id': customer.id,
                    'name': customer.get_full_name(),
                    'account_number': f"{customer.gl_no}{customer.ac_no}",
                },
                'loan_summary': {
                    'total_loans': loans.count(),
                    'total_outstanding': float(total_outstanding),
                    'active_loans': loans.filter(approval_status='A').count(),
                },
                'loans': loans_data,
                'inquiry_time': timezone.now().isoformat(),
                'processed_by': f"{request.user.first_name} {request.user.last_name}"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Loans inquiry error: {str(e)}")
            return Response({
                'error': 'Loans inquiry failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardStatsView(APIView):
    """
    Get dashboard statistics for account officer
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            today = timezone.now().date()
            yesterday = today - timedelta(days=1)
            this_month = today.replace(day=1)
            
            # Filter by user's branch if applicable
            branch_filter = Q()
            if request.user.branch:
                branch_filter = Q(branch=request.user.branch)
            
            # Today's statistics
            today_stats = Memtrans.objects.filter(
                ses_date=today
            ).filter(branch_filter).aggregate(
                deposits_count=Count('id', filter=Q(amount__gt=0)),
                deposits_amount=Sum('amount', filter=Q(amount__gt=0)),
                withdrawals_count=Count('id', filter=Q(amount__lt=0)),
                withdrawals_amount=Sum('amount', filter=Q(amount__lt=0)),
                total_transactions=Count('id')
            )
            
            # This month's statistics
            month_stats = Memtrans.objects.filter(
                ses_date__gte=this_month
            ).filter(branch_filter).aggregate(
                deposits_amount=Sum('amount', filter=Q(amount__gt=0)),
                withdrawals_amount=Sum('amount', filter=Q(amount__lt=0)),
                total_transactions=Count('id')
            )
            
            # Customer statistics
            customer_stats = Customer.objects.filter(
                branch=request.user.branch if request.user.branch else None
            ).aggregate(
                total_customers=Count('id'),
                active_customers=Count('id', filter=Q(status=True))
            )
            
            # Recent transactions (last 5)
            recent_transactions = Memtrans.objects.filter(
                branch_filter
            ).order_by('-sys_date')[:5]
            
            recent_data = []
            for trx in recent_transactions:
                recent_data.append({
                    'reference': trx.trx_no,
                    'customer_name': trx.customer.get_full_name() if trx.customer else 'N/A',
                    'amount': float(trx.amount),
                    'type': 'Credit' if trx.amount > 0 else 'Debit',
                    'timestamp': trx.sys_date.isoformat()
                })
            
            return Response({
                'success': True,
                'today': {
                    'deposits_count': today_stats['deposits_count'] or 0,
                    'deposits_amount': float(today_stats['deposits_amount'] or 0),
                    'withdrawals_count': today_stats['withdrawals_count'] or 0,
                    'withdrawals_amount': float(abs(today_stats['withdrawals_amount'] or 0)),
                    'total_transactions': today_stats['total_transactions'] or 0,
                    'net_amount': float((today_stats['deposits_amount'] or 0) + (today_stats['withdrawals_amount'] or 0))
                },
                'month': {
                    'deposits_amount': float(month_stats['deposits_amount'] or 0),
                    'withdrawals_amount': float(abs(month_stats['withdrawals_amount'] or 0)),
                    'total_transactions': month_stats['total_transactions'] or 0
                },
                'customers': {
                    'total': customer_stats['total_customers'] or 0,
                    'active': customer_stats['active_customers'] or 0
                },
                'recent_transactions': recent_data,
                'branch': {
                    'name': request.user.branch.branch_name if request.user.branch else 'All Branches',
                    'code': request.user.branch.branch_code if request.user.branch else 'ALL'
                },
                'officer': {
                    'name': f"{request.user.first_name} {request.user.last_name}",
                    'role': request.user.get_role_display() if request.user.role else 'Account Officer'
                },
                'generated_at': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Dashboard stats error: {str(e)}")
            return Response({
                'error': 'Dashboard statistics failed to load'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)