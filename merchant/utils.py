"""
Utility functions for the merchant app
"""

import random
import string
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from django.db import transaction


def generate_merchant_id():
    """Generate a unique merchant ID"""
    timestamp = datetime.now().strftime('%y%m%d')
    random_part = ''.join(random.choices(string.digits, k=6))
    return f"MRC{timestamp}{random_part}"


def generate_merchant_code():
    """Generate a short merchant code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def generate_transaction_ref(prefix='TRX'):
    """Generate a unique transaction reference"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}{timestamp}{random_part}"


def get_merchant_float_balance(merchant):
    """Get current float balance for a merchant"""
    from transactions.models import Memtrans
    from django.db.models import Sum
    
    if not merchant.float_gl_no or not merchant.float_ac_no:
        return Decimal('0.00')
    
    balance = Memtrans.all_objects.filter(
        branch=merchant.branch,
        gl_no=merchant.float_gl_no,
        ac_no=merchant.float_ac_no,
        error='A'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    return balance


def get_customer_balance(branch, gl_no, ac_no):
    """Get customer account balance"""
    from transactions.models import Memtrans
    from django.db.models import Sum
    
    balance = Memtrans.all_objects.filter(
        branch=branch,
        gl_no=gl_no,
        ac_no=ac_no,
        error='A'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    return balance


def find_customer_by_account(branch, account_number):
    """Find customer by account number (gl_no + ac_no)"""
    from customers.models import Customer
    
    # Account number format: GLNOAC_NO (e.g., 201011)
    if len(account_number) < 6:
        return None
    
    # Try to split account number - first 5 digits as GL, rest as AC
    gl_no = account_number[:5]
    ac_no = account_number[5:]
    
    try:
        return Customer.all_objects.get(
            branch=branch,
            gl_no=gl_no,
            ac_no=ac_no
        )
    except Customer.DoesNotExist:
        return None


def create_merchant_user(merchant_data, branch, created_by):
    """Create user account for merchant portal login"""
    from accounts.models import User
    
    username = f"MRC_{merchant_data['merchant_code']}"
    email = merchant_data.get('business_email') or merchant_data.get('contact_person_email', '')
    
    user = User.objects.create_user(
        first_name=merchant_data['merchant_name'].split()[0] if merchant_data['merchant_name'] else 'Merchant',
        last_name=merchant_data['merchant_name'].split()[-1] if len(merchant_data['merchant_name'].split()) > 1 else '',
        username=username,
        email=email,
        role=User.CUSTOMER,  # Use customer role for merchants
        branch_id=str(branch.id),
        password=merchant_data['password']
    )
    
    return user


def create_merchant_float_account(merchant, branch):
    """Create float account for merchant"""
    from customers.models import Customer
    from accounts_admin.models import Account
    
    # Use a dedicated GL for merchant float accounts (e.g., 20501 - Accounts Payable)
    float_gl_no = '20501'  # You can make this configurable
    
    # Generate unique account number
    last_customer = Customer.all_objects.filter(
        branch=branch,
        gl_no=float_gl_no
    ).order_by('-ac_no').first()
    
    if last_customer and last_customer.ac_no:
        try:
            ac_no = str(int(last_customer.ac_no) + 1).zfill(5)
        except ValueError:
            ac_no = '00001'
    else:
        ac_no = '00001'
    
    # Create float customer account
    float_customer = Customer.all_objects.create(
        branch=branch,
        gl_no=float_gl_no,
        ac_no=ac_no,
        first_name=f"FLOAT - {merchant.merchant_name}",
        internal=True,
        status='A',
        reg_date=timezone.now().date()
    )
    
    return float_gl_no, ac_no


def log_merchant_activity(merchant, activity_type, description, request=None, transaction=None):
    """Log merchant activity"""
    from .models import MerchantActivityLog
    
    ip_address = None
    user_agent = None
    
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    MerchantActivityLog.all_objects.create(
        merchant=merchant,
        activity_type=activity_type,
        description=description,
        transaction=transaction,
        ip_address=ip_address,
        user_agent=user_agent
    )


def process_merchant_deposit(merchant, customer, amount, narration=None, request=None):
    """
    Process customer deposit through merchant
    - Debit merchant float account
    - Credit customer account
    """
    from transactions.models import Memtrans
    from .models import MerchantTransaction, MerchantServiceConfig
    
    # Get service config
    service_config = MerchantServiceConfig.all_objects.filter(
        branch=merchant.branch,
        service_type='deposit',
        is_enabled=True
    ).first()
    
    # Calculate charges and commission
    charge = Decimal('0.00')
    commission = Decimal('0.00')
    
    if service_config:
        charge = service_config.calculate_charge(amount)
        commission = service_config.calculate_commission(amount)
    
    # Get float balance before
    float_balance_before = get_merchant_float_balance(merchant)
    
    # Check if merchant has sufficient float
    total_debit = amount
    if float_balance_before < total_debit:
        raise ValueError(f"Insufficient float balance. Available: {float_balance_before}")
    
    transaction_ref = generate_transaction_ref('DEP')
    session_date = merchant.branch.session_date or timezone.now().date()
    
    with transaction.atomic():
        # Debit merchant float account
        Memtrans.all_objects.create(
            branch=merchant.branch,
            cust_branch=merchant.branch,
            gl_no=merchant.float_gl_no,
            ac_no=merchant.float_ac_no,
            amount=-amount,
            description=f'Merchant Deposit - {customer.first_name} {customer.last_name}',
            error='A',
            type='D',
            account_type='L',
            ses_date=session_date,
            app_date=session_date,
            trx_no=transaction_ref,
            code='MDP',
            trx_type='MERCHANT_DEPOSIT'
        )
        
        # Credit customer account
        Memtrans.all_objects.create(
            branch=merchant.branch,
            cust_branch=customer.branch,
            customer=customer,
            gl_no=customer.gl_no,
            ac_no=customer.ac_no,
            amount=amount,
            description=narration or f'Deposit via Merchant {merchant.merchant_code}',
            error='A',
            type='C',
            account_type='S',
            ses_date=session_date,
            app_date=session_date,
            trx_no=transaction_ref,
            code='MDP',
            trx_type='MERCHANT_DEPOSIT'
        )
        
        # Get float balance after
        float_balance_after = get_merchant_float_balance(merchant)
        
        # Create merchant transaction record
        merchant_trx = MerchantTransaction.all_objects.create(
            merchant=merchant,
            branch=merchant.branch,
            transaction_ref=transaction_ref,
            transaction_type='deposit',
            amount=amount,
            charge=charge,
            commission=commission,
            customer=customer,
            customer_name=f"{customer.first_name} {customer.last_name}",
            customer_phone=customer.phone_no,
            customer_account=f"{customer.gl_no}{customer.ac_no}",
            narration=narration or 'Customer Deposit',
            status='completed',
            float_balance_before=float_balance_before,
            float_balance_after=float_balance_after,
            completed_at=timezone.now()
        )
        
        # Log activity
        log_merchant_activity(
            merchant=merchant,
            activity_type='transaction',
            description=f'Deposit of {amount} to customer {customer.first_name} {customer.last_name}',
            request=request,
            transaction=merchant_trx
        )
        
        return merchant_trx


def process_merchant_withdrawal(merchant, customer, amount, narration=None, request=None):
    """
    Process customer withdrawal through merchant
    - Debit customer account
    - Credit merchant float account
    """
    from transactions.models import Memtrans
    from .models import MerchantTransaction, MerchantServiceConfig
    
    # Check customer balance
    customer_balance = get_customer_balance(customer.branch, customer.gl_no, customer.ac_no)
    if customer_balance < amount:
        raise ValueError(f"Customer has insufficient balance. Available: {customer_balance}")
    
    # Get service config
    service_config = MerchantServiceConfig.all_objects.filter(
        branch=merchant.branch,
        service_type='withdrawal',
        is_enabled=True
    ).first()
    
    # Calculate charges and commission
    charge = Decimal('0.00')
    commission = Decimal('0.00')
    
    if service_config:
        charge = service_config.calculate_charge(amount)
        commission = service_config.calculate_commission(amount)
    
    # Get float balance before
    float_balance_before = get_merchant_float_balance(merchant)
    
    transaction_ref = generate_transaction_ref('WDL')
    session_date = merchant.branch.session_date or timezone.now().date()
    
    with transaction.atomic():
        # Debit customer account
        Memtrans.all_objects.create(
            branch=merchant.branch,
            cust_branch=customer.branch,
            customer=customer,
            gl_no=customer.gl_no,
            ac_no=customer.ac_no,
            amount=-amount,
            description=narration or f'Withdrawal via Merchant {merchant.merchant_code}',
            error='A',
            type='D',
            account_type='S',
            ses_date=session_date,
            app_date=session_date,
            trx_no=transaction_ref,
            code='MWD',
            trx_type='MERCHANT_WITHDRAWAL'
        )
        
        # Credit merchant float account
        Memtrans.all_objects.create(
            branch=merchant.branch,
            cust_branch=merchant.branch,
            gl_no=merchant.float_gl_no,
            ac_no=merchant.float_ac_no,
            amount=amount,
            description=f'Merchant Withdrawal - {customer.first_name} {customer.last_name}',
            error='A',
            type='C',
            account_type='L',
            ses_date=session_date,
            app_date=session_date,
            trx_no=transaction_ref,
            code='MWD',
            trx_type='MERCHANT_WITHDRAWAL'
        )
        
        # Get float balance after
        float_balance_after = get_merchant_float_balance(merchant)
        
        # Create merchant transaction record
        merchant_trx = MerchantTransaction.all_objects.create(
            merchant=merchant,
            branch=merchant.branch,
            transaction_ref=transaction_ref,
            transaction_type='withdrawal',
            amount=amount,
            charge=charge,
            commission=commission,
            customer=customer,
            customer_name=f"{customer.first_name} {customer.last_name}",
            customer_phone=customer.phone_no,
            customer_account=f"{customer.gl_no}{customer.ac_no}",
            narration=narration or 'Customer Withdrawal',
            status='completed',
            float_balance_before=float_balance_before,
            float_balance_after=float_balance_after,
            completed_at=timezone.now()
        )
        
        # Log activity
        log_merchant_activity(
            merchant=merchant,
            activity_type='transaction',
            description=f'Withdrawal of {amount} for customer {customer.first_name} {customer.last_name}',
            request=request,
            transaction=merchant_trx
        )
        
        return merchant_trx


def get_merchant_dashboard_stats(merchant):
    """Get dashboard statistics for a merchant"""
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncDate
    from .models import MerchantTransaction
    
    today = timezone.now().date()
    
    # Today's stats
    today_transactions = MerchantTransaction.all_objects.filter(
        merchant=merchant,
        created_at__date=today,
        status='completed'
    )
    
    today_stats = today_transactions.aggregate(
        count=Count('id'),
        total_amount=Sum('amount'),
        total_commission=Sum('commission')
    )
    
    # This month's stats
    month_start = today.replace(day=1)
    month_transactions = MerchantTransaction.all_objects.filter(
        merchant=merchant,
        created_at__date__gte=month_start,
        status='completed'
    )
    
    month_stats = month_transactions.aggregate(
        count=Count('id'),
        total_amount=Sum('amount'),
        total_commission=Sum('commission')
    )
    
    # Transaction breakdown by type
    type_breakdown = MerchantTransaction.all_objects.filter(
        merchant=merchant,
        created_at__date__gte=month_start,
        status='completed'
    ).values('transaction_type').annotate(
        count=Count('id'),
        total=Sum('amount')
    )
    
    # Float balance
    float_balance = get_merchant_float_balance(merchant)
    
    return {
        'float_balance': float_balance,
        'today': {
            'count': today_stats['count'] or 0,
            'amount': today_stats['total_amount'] or Decimal('0.00'),
            'commission': today_stats['total_commission'] or Decimal('0.00')
        },
        'month': {
            'count': month_stats['count'] or 0,
            'amount': month_stats['total_amount'] or Decimal('0.00'),
            'commission': month_stats['total_commission'] or Decimal('0.00')
        },
        'type_breakdown': list(type_breakdown)
    }
