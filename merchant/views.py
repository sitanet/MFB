"""
Merchant Views

This module contains views for:
1. FinanceFlex Admin - Managing merchants
2. Merchant Portal - Merchant's own interface
"""

import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.db import transaction

from .models import (
    Merchant, MerchantTransaction, MerchantActivityLog,
    MerchantCommission, MerchantServiceConfig
)
from .forms import (
    MerchantRegistrationForm, MerchantUpdateForm, MerchantLoginForm,
    MerchantPinChangeForm, CustomerRegistrationForm, DepositForm,
    WithdrawalForm, TransferForm, InternalTransferForm, BillPaymentForm,
    AirtimeForm, DataForm, MerchantServiceConfigForm
)
from .utils import (
    generate_merchant_id, generate_merchant_code, generate_transaction_ref,
    get_merchant_float_balance, get_customer_balance, find_customer_by_account,
    create_merchant_user, create_merchant_float_account, log_merchant_activity,
    process_merchant_deposit, process_merchant_withdrawal, get_merchant_dashboard_stats
)


# ==============================================================================
# FINANCEFLEX ADMIN VIEWS - For managing merchants from the main system
# ==============================================================================

@login_required
def merchant_dashboard(request):
    """Main merchant dashboard for FinanceFlex Admin - Overview of all merchants"""
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    # Merchant counts
    total_merchants = Merchant.objects.count()
    active_merchants = Merchant.objects.filter(status='active').count()
    pending_merchants = Merchant.objects.filter(status='pending').count()
    suspended_merchants = Merchant.objects.filter(status='suspended').count()
    
    # Today's transaction stats
    today_stats = MerchantTransaction.objects.filter(
        created_at__date=today,
        status='completed'
    ).aggregate(
        count=Count('id'),
        total_amount=Sum('amount'),
        total_commission=Sum('commission'),
        total_charge=Sum('charge')
    )
    
    # This month's transaction stats
    month_stats = MerchantTransaction.objects.filter(
        created_at__date__gte=month_start,
        status='completed'
    ).aggregate(
        count=Count('id'),
        total_amount=Sum('amount'),
        total_commission=Sum('commission'),
        total_charge=Sum('charge')
    )
    
    # Transaction type breakdown (this month)
    type_breakdown = MerchantTransaction.objects.filter(
        created_at__date__gte=month_start,
        status='completed'
    ).values('transaction_type').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    # Top 10 merchants by transaction volume (this month)
    top_merchants = Merchant.objects.annotate(
        trx_count=Count('transactions', filter=Q(
            transactions__status='completed',
            transactions__created_at__date__gte=month_start
        )),
        trx_volume=Sum('transactions__amount', filter=Q(
            transactions__status='completed',
            transactions__created_at__date__gte=month_start
        )),
        trx_commission=Sum('transactions__commission', filter=Q(
            transactions__status='completed',
            transactions__created_at__date__gte=month_start
        ))
    ).filter(trx_count__gt=0).order_by('-trx_volume')[:10]
    
    # Recent transactions
    recent_transactions = MerchantTransaction.objects.select_related('merchant').order_by('-created_at')[:10]
    
    # Recent merchants
    recent_merchants = Merchant.objects.order_by('-created_at')[:5]
    
    # Daily transaction trend (last 7 days)
    from datetime import timedelta
    daily_trend = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        day_stats = MerchantTransaction.objects.filter(
            created_at__date=date,
            status='completed'
        ).aggregate(
            count=Count('id'),
            total=Sum('amount')
        )
        daily_trend.append({
            'date': date,
            'count': day_stats['count'] or 0,
            'total': day_stats['total'] or 0
        })
    
    context = {
        'total_merchants': total_merchants,
        'active_merchants': active_merchants,
        'pending_merchants': pending_merchants,
        'suspended_merchants': suspended_merchants,
        'today_stats': today_stats,
        'month_stats': month_stats,
        'type_breakdown': type_breakdown,
        'top_merchants': top_merchants,
        'recent_transactions': recent_transactions,
        'recent_merchants': recent_merchants,
        'daily_trend': daily_trend,
    }
    return render(request, 'merchant/admin/dashboard.html', context)


@login_required
def merchant_list(request):
    """List all merchants (FinanceFlex Admin)"""
    merchants = Merchant.objects.all()
    
    # Filters
    status = request.GET.get('status')
    merchant_type = request.GET.get('type')
    search = request.GET.get('search')
    
    if status:
        merchants = merchants.filter(status=status)
    if merchant_type:
        merchants = merchants.filter(merchant_type=merchant_type)
    if search:
        merchants = merchants.filter(
            Q(merchant_name__icontains=search) |
            Q(merchant_id__icontains=search) |
            Q(merchant_code__icontains=search) |
            Q(business_name__icontains=search)
        )
    
    paginator = Paginator(merchants, 20)
    page = request.GET.get('page', 1)
    merchants = paginator.get_page(page)
    
    context = {
        'merchants': merchants,
        'status_choices': Merchant.STATUS_CHOICES,
        'type_choices': Merchant.MERCHANT_TYPE_CHOICES,
    }
    return render(request, 'merchant/admin/merchant_list.html', context)


@login_required
def merchant_create(request):
    """Create a new merchant (FinanceFlex Admin)"""
    if request.method == 'POST':
        form = MerchantRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Generate unique IDs
                    merchant_id = generate_merchant_id()
                    merchant_code = generate_merchant_code()
                    
                    # Get branch from logged-in user
                    branch = request.user.get_branch()
                    if not branch:
                        messages.error(request, 'Unable to determine branch')
                        return redirect('merchant:merchant_list')
                    
                    # Create merchant instance
                    merchant = form.save(commit=False)
                    merchant.merchant_id = merchant_id
                    merchant.merchant_code = merchant_code
                    merchant.branch = branch
                    merchant.created_by = request.user
                    merchant.status = 'pending'
                    
                    # Create user account for merchant portal
                    user_data = {
                        'merchant_name': form.cleaned_data['merchant_name'],
                        'merchant_code': merchant_code,
                        'password': form.cleaned_data['password'],
                        'business_email': form.cleaned_data.get('business_email'),
                        'contact_person_email': form.cleaned_data.get('contact_person_email'),
                    }
                    user = create_merchant_user(user_data, branch, request.user)
                    merchant.user = user
                    
                    # Create float account
                    float_gl_no, float_ac_no = create_merchant_float_account(merchant, branch)
                    merchant.float_gl_no = float_gl_no
                    merchant.float_ac_no = float_ac_no
                    
                    # Set transaction PIN
                    merchant.set_transaction_pin(form.cleaned_data['transaction_pin'])
                    
                    merchant.save()
                    
                    messages.success(request, f'Merchant created successfully. Merchant ID: {merchant_id}')
                    return redirect('merchant:merchant_detail', merchant_id=merchant.id)
                    
            except Exception as e:
                messages.error(request, f'Error creating merchant: {str(e)}')
    else:
        form = MerchantRegistrationForm()
    
    context = {'form': form}
    return render(request, 'merchant/admin/merchant_create.html', context)


@login_required
def merchant_detail(request, merchant_id):
    """View merchant details (FinanceFlex Admin)"""
    merchant = get_object_or_404(Merchant, id=merchant_id)
    
    # Get statistics
    stats = get_merchant_dashboard_stats(merchant)
    
    # Recent transactions
    recent_transactions = MerchantTransaction.all_objects.filter(
        merchant=merchant
    ).order_by('-created_at')[:10]
    
    # Recent activity
    recent_activity = MerchantActivityLog.all_objects.filter(
        merchant=merchant
    ).order_by('-created_at')[:10]
    
    context = {
        'merchant': merchant,
        'stats': stats,
        'recent_transactions': recent_transactions,
        'recent_activity': recent_activity,
    }
    return render(request, 'merchant/admin/merchant_detail.html', context)


@login_required
def merchant_update(request, merchant_id):
    """Update merchant details (FinanceFlex Admin)"""
    merchant = get_object_or_404(Merchant, id=merchant_id)
    
    if request.method == 'POST':
        form = MerchantUpdateForm(request.POST, instance=merchant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Merchant updated successfully')
            return redirect('merchant:merchant_detail', merchant_id=merchant.id)
    else:
        form = MerchantUpdateForm(instance=merchant)
    
    context = {
        'form': form,
        'merchant': merchant,
    }
    return render(request, 'merchant/admin/merchant_update.html', context)


@login_required
@require_POST
def merchant_activate(request, merchant_id):
    """Activate a merchant (FinanceFlex Admin)"""
    merchant = get_object_or_404(Merchant, id=merchant_id)
    
    if merchant.status == 'active':
        messages.warning(request, 'Merchant is already active')
    else:
        merchant.status = 'active'
        merchant.activated_by = request.user
        merchant.activated_at = timezone.now()
        merchant.save()
        messages.success(request, f'Merchant {merchant.merchant_name} activated successfully')
    
    return redirect('merchant:merchant_detail', merchant_id=merchant.id)


@login_required
@require_POST
def merchant_suspend(request, merchant_id):
    """Suspend a merchant (FinanceFlex Admin)"""
    merchant = get_object_or_404(Merchant, id=merchant_id)
    
    merchant.status = 'suspended'
    merchant.save()
    messages.success(request, f'Merchant {merchant.merchant_name} has been suspended')
    
    return redirect('merchant:merchant_detail', merchant_id=merchant.id)


@login_required
def merchant_transactions_admin(request, merchant_id):
    """View merchant transactions (FinanceFlex Admin)"""
    merchant = get_object_or_404(Merchant, id=merchant_id)
    
    transactions = MerchantTransaction.all_objects.filter(merchant=merchant)
    
    # Filters
    trx_type = request.GET.get('type')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if trx_type:
        transactions = transactions.filter(transaction_type=trx_type)
    if status:
        transactions = transactions.filter(status=status)
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)
    
    transactions = transactions.order_by('-created_at')
    
    paginator = Paginator(transactions, 50)
    page = request.GET.get('page', 1)
    transactions = paginator.get_page(page)
    
    context = {
        'merchant': merchant,
        'transactions': transactions,
        'transaction_types': MerchantTransaction.TRANSACTION_TYPES,
        'status_choices': MerchantTransaction.STATUS_CHOICES,
    }
    return render(request, 'merchant/admin/merchant_transactions.html', context)


@login_required
def merchant_activity_admin(request, merchant_id):
    """View merchant activity log (FinanceFlex Admin)"""
    merchant = get_object_or_404(Merchant, id=merchant_id)
    
    activities = MerchantActivityLog.all_objects.filter(
        merchant=merchant
    ).order_by('-created_at')
    
    paginator = Paginator(activities, 50)
    page = request.GET.get('page', 1)
    activities = paginator.get_page(page)
    
    context = {
        'merchant': merchant,
        'activities': activities,
    }
    return render(request, 'merchant/admin/merchant_activity.html', context)


@login_required
def all_merchant_transactions(request):
    """View all merchant transactions across all merchants (FinanceFlex Admin)"""
    transactions = MerchantTransaction.objects.all()
    
    # Filters
    merchant_id = request.GET.get('merchant')
    trx_type = request.GET.get('type')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if merchant_id:
        transactions = transactions.filter(merchant_id=merchant_id)
    if trx_type:
        transactions = transactions.filter(transaction_type=trx_type)
    if status:
        transactions = transactions.filter(status=status)
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)
    
    transactions = transactions.order_by('-created_at')
    
    # Summary stats
    summary = transactions.aggregate(
        total_count=Count('id'),
        total_amount=Sum('amount'),
        total_commission=Sum('commission')
    )
    
    paginator = Paginator(transactions, 50)
    page = request.GET.get('page', 1)
    transactions = paginator.get_page(page)
    
    # Get merchant list for filter
    merchants = Merchant.objects.all()
    
    context = {
        'transactions': transactions,
        'merchants': merchants,
        'summary': summary,
        'transaction_types': MerchantTransaction.TRANSACTION_TYPES,
        'status_choices': MerchantTransaction.STATUS_CHOICES,
    }
    return render(request, 'merchant/admin/all_transactions.html', context)


@login_required
def merchant_reports_admin(request):
    """Merchant reports dashboard (FinanceFlex Admin)"""
    # Overall stats
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    # Active merchants
    active_merchants = Merchant.objects.filter(status='active').count()
    total_merchants = Merchant.objects.count()
    
    # Today's transactions
    today_transactions = MerchantTransaction.objects.filter(
        created_at__date=today,
        status='completed'
    ).aggregate(
        count=Count('id'),
        total_amount=Sum('amount'),
        total_commission=Sum('commission')
    )
    
    # This month's transactions
    month_transactions = MerchantTransaction.objects.filter(
        created_at__date__gte=month_start,
        status='completed'
    ).aggregate(
        count=Count('id'),
        total_amount=Sum('amount'),
        total_commission=Sum('commission')
    )
    
    # Top merchants by transaction volume
    top_merchants = Merchant.objects.annotate(
        trx_count=Count('transactions', filter=Q(
            transactions__status='completed',
            transactions__created_at__date__gte=month_start
        )),
        trx_volume=Sum('transactions__amount', filter=Q(
            transactions__status='completed',
            transactions__created_at__date__gte=month_start
        ))
    ).order_by('-trx_volume')[:10]
    
    # Transaction type breakdown
    type_breakdown = MerchantTransaction.objects.filter(
        created_at__date__gte=month_start,
        status='completed'
    ).values('transaction_type').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    context = {
        'active_merchants': active_merchants,
        'total_merchants': total_merchants,
        'today': today_transactions,
        'month': month_transactions,
        'top_merchants': top_merchants,
        'type_breakdown': type_breakdown,
    }
    return render(request, 'merchant/admin/reports.html', context)


@login_required
def merchant_service_config(request):
    """Configure merchant services (FinanceFlex Admin)"""
    branch = request.user.get_branch()
    
    if request.method == 'POST':
        form = MerchantServiceConfigForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.branch = branch
            config.save()
            messages.success(request, 'Service configuration saved')
            return redirect('merchant:service_config')
    else:
        form = MerchantServiceConfigForm()
    
    configs = MerchantServiceConfig.objects.filter(branch=branch)
    
    context = {
        'form': form,
        'configs': configs,
    }
    return render(request, 'merchant/admin/service_config.html', context)


# ==============================================================================
# MERCHANT PORTAL VIEWS - For merchant's own interface
# ==============================================================================

def merchant_login(request):
    """Merchant portal login"""
    if request.method == 'POST':
        form = MerchantLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Try to find user by username first, then authenticate with email
            try:
                from accounts.models import User
                merchant_user = User.objects.get(username=username)
                user = authenticate(request, email=merchant_user.email, password=password)
            except User.DoesNotExist:
                user = None
            
            if user is not None:
                # Check if user has merchant profile
                try:
                    merchant = user.merchant_profile
                    if merchant.status != 'active':
                        messages.error(request, 'Your merchant account is not active')
                        return redirect('merchant:portal_login')
                    
                    login(request, user)
                    
                    # Log activity
                    log_merchant_activity(
                        merchant=merchant,
                        activity_type='login',
                        description='Logged in to merchant portal',
                        request=request
                    )
                    
                    return redirect('merchant:portal_dashboard')
                except Merchant.DoesNotExist:
                    messages.error(request, 'No merchant account found for this user')
            else:
                messages.error(request, 'Invalid username or password')
                
                # Try to log failed login
                try:
                    from accounts.models import User
                    user = User.objects.get(username=username)
                    if hasattr(user, 'merchant_profile'):
                        log_merchant_activity(
                            merchant=user.merchant_profile,
                            activity_type='failed_login',
                            description='Failed login attempt',
                            request=request
                        )
                except:
                    pass
    else:
        form = MerchantLoginForm()
    
    return render(request, 'merchant/portal/login.html', {'form': form})


def merchant_logout(request):
    """Merchant portal logout"""
    if request.user.is_authenticated:
        try:
            merchant = request.user.merchant_profile
            log_merchant_activity(
                merchant=merchant,
                activity_type='logout',
                description='Logged out of merchant portal',
                request=request
            )
        except:
            pass
    
    logout(request)
    return redirect('merchant:portal_login')


def merchant_required(view_func):
    """Decorator to ensure user is a merchant"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('merchant:portal_login')
        
        try:
            merchant = request.user.merchant_profile
            if merchant.status != 'active':
                messages.error(request, 'Your merchant account is not active')
                return redirect('merchant:portal_login')
            request.merchant = merchant
        except Merchant.DoesNotExist:
            messages.error(request, 'No merchant account found')
            return redirect('merchant:portal_login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


@merchant_required
def portal_dashboard(request):
    """Merchant portal dashboard"""
    merchant = request.merchant
    stats = get_merchant_dashboard_stats(merchant)
    
    # Recent transactions
    recent_transactions = MerchantTransaction.all_objects.filter(
        merchant=merchant
    ).order_by('-created_at')[:5]
    
    context = {
        'merchant': merchant,
        'stats': stats,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'merchant/portal/dashboard.html', context)


@merchant_required
def portal_deposit(request):
    """Customer deposit"""
    merchant = request.merchant
    
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            account_number = form.cleaned_data['customer_account']
            amount = form.cleaned_data['amount']
            narration = form.cleaned_data.get('narration', '')
            pin = form.cleaned_data['transaction_pin']
            
            # Verify PIN
            if not merchant.check_transaction_pin(pin):
                messages.error(request, 'Invalid transaction PIN')
                return redirect('merchant:portal_deposit')
            
            # Find customer
            customer = find_customer_by_account(merchant.branch, account_number)
            if not customer:
                messages.error(request, 'Customer account not found')
                return redirect('merchant:portal_deposit')
            
            try:
                trx = process_merchant_deposit(merchant, customer, amount, narration, request)
                messages.success(request, f'Deposit successful. Reference: {trx.transaction_ref}')
                return redirect('merchant:portal_transaction_detail', trx_ref=trx.transaction_ref)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = DepositForm()
    
    context = {
        'merchant': merchant,
        'form': form,
        'float_balance': get_merchant_float_balance(merchant),
    }
    return render(request, 'merchant/portal/deposit.html', context)


@merchant_required
def portal_withdrawal(request):
    """Customer withdrawal"""
    merchant = request.merchant
    
    if request.method == 'POST':
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            account_number = form.cleaned_data['customer_account']
            amount = form.cleaned_data['amount']
            narration = form.cleaned_data.get('narration', '')
            pin = form.cleaned_data['transaction_pin']
            
            # Verify PIN
            if not merchant.check_transaction_pin(pin):
                messages.error(request, 'Invalid transaction PIN')
                return redirect('merchant:portal_withdrawal')
            
            # Find customer
            customer = find_customer_by_account(merchant.branch, account_number)
            if not customer:
                messages.error(request, 'Customer account not found')
                return redirect('merchant:portal_withdrawal')
            
            try:
                trx = process_merchant_withdrawal(merchant, customer, amount, narration, request)
                messages.success(request, f'Withdrawal successful. Reference: {trx.transaction_ref}')
                return redirect('merchant:portal_transaction_detail', trx_ref=trx.transaction_ref)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = WithdrawalForm()
    
    context = {
        'merchant': merchant,
        'form': form,
        'float_balance': get_merchant_float_balance(merchant),
    }
    return render(request, 'merchant/portal/withdrawal.html', context)


@merchant_required
def portal_transfer(request):
    """Fund transfer (external)"""
    merchant = request.merchant
    
    # Get bank list
    from ninepsb.models import PsbBank
    banks = PsbBank.objects.filter(active=True).order_by('bank_name')
    
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            # TODO: Implement external transfer using 9PSB
            messages.info(request, 'External transfer coming soon')
    else:
        form = TransferForm()
    
    context = {
        'merchant': merchant,
        'form': form,
        'banks': banks,
        'float_balance': get_merchant_float_balance(merchant),
    }
    return render(request, 'merchant/portal/transfer.html', context)


@merchant_required
def portal_internal_transfer(request):
    """FinanceFlex internal transfer"""
    merchant = request.merchant
    
    if request.method == 'POST':
        form = InternalTransferForm(request.POST)
        if form.is_valid():
            # TODO: Implement internal transfer
            messages.info(request, 'Internal transfer coming soon')
    else:
        form = InternalTransferForm()
    
    context = {
        'merchant': merchant,
        'form': form,
        'float_balance': get_merchant_float_balance(merchant),
    }
    return render(request, 'merchant/portal/internal_transfer.html', context)


@merchant_required
def portal_airtime(request):
    """Airtime purchase"""
    merchant = request.merchant
    
    if request.method == 'POST':
        form = AirtimeForm(request.POST)
        if form.is_valid():
            # TODO: Implement airtime purchase using VAS
            messages.info(request, 'Airtime purchase coming soon')
    else:
        form = AirtimeForm()
    
    context = {
        'merchant': merchant,
        'form': form,
        'float_balance': get_merchant_float_balance(merchant),
    }
    return render(request, 'merchant/portal/airtime.html', context)


@merchant_required
def portal_data(request):
    """Data purchase"""
    merchant = request.merchant
    
    if request.method == 'POST':
        form = DataForm(request.POST)
        if form.is_valid():
            # TODO: Implement data purchase using VAS
            messages.info(request, 'Data purchase coming soon')
    else:
        form = DataForm()
    
    context = {
        'merchant': merchant,
        'form': form,
        'float_balance': get_merchant_float_balance(merchant),
    }
    return render(request, 'merchant/portal/data.html', context)


@merchant_required
def portal_bills(request):
    """Bill payments"""
    merchant = request.merchant
    
    if request.method == 'POST':
        form = BillPaymentForm(request.POST)
        if form.is_valid():
            # TODO: Implement bill payment using VAS
            messages.info(request, 'Bill payment coming soon')
    else:
        form = BillPaymentForm()
    
    context = {
        'merchant': merchant,
        'form': form,
        'float_balance': get_merchant_float_balance(merchant),
    }
    return render(request, 'merchant/portal/bills.html', context)


@merchant_required
def portal_customer_register(request):
    """Register new customer"""
    merchant = request.merchant
    
    # Get account types
    from accounts_admin.models import CustomerAccountType
    account_types = CustomerAccountType.objects.filter(
        branch=merchant.branch,
        is_active=True,
        usage_type__in=['customer', 'both']
    )
    
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            pin = form.cleaned_data['transaction_pin']
            
            # Verify merchant PIN
            if not merchant.check_transaction_pin(pin):
                messages.error(request, 'Invalid transaction PIN')
                return redirect('merchant:portal_customer_register')
            
            # TODO: Implement customer registration
            messages.info(request, 'Customer registration coming soon')
    else:
        form = CustomerRegistrationForm()
    
    context = {
        'merchant': merchant,
        'form': form,
        'account_types': account_types,
    }
    return render(request, 'merchant/portal/customer_register.html', context)


@merchant_required
def portal_transactions(request):
    """View merchant's transactions"""
    merchant = request.merchant
    
    transactions = MerchantTransaction.all_objects.filter(merchant=merchant)
    
    # Filters
    trx_type = request.GET.get('type')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if trx_type:
        transactions = transactions.filter(transaction_type=trx_type)
    if status:
        transactions = transactions.filter(status=status)
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)
    
    transactions = transactions.order_by('-created_at')
    
    paginator = Paginator(transactions, 20)
    page = request.GET.get('page', 1)
    transactions = paginator.get_page(page)
    
    context = {
        'merchant': merchant,
        'transactions': transactions,
        'transaction_types': MerchantTransaction.TRANSACTION_TYPES,
        'status_choices': MerchantTransaction.STATUS_CHOICES,
    }
    return render(request, 'merchant/portal/transactions.html', context)


@merchant_required
def portal_transaction_detail(request, trx_ref):
    """View transaction details"""
    merchant = request.merchant
    
    trx = get_object_or_404(
        MerchantTransaction,
        merchant=merchant,
        transaction_ref=trx_ref
    )
    
    context = {
        'merchant': merchant,
        'transaction': trx,
    }
    return render(request, 'merchant/portal/transaction_detail.html', context)


@merchant_required
def portal_reports(request):
    """Merchant reports"""
    merchant = request.merchant
    stats = get_merchant_dashboard_stats(merchant)
    
    # Date range filter
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from and date_to:
        transactions = MerchantTransaction.all_objects.filter(
            merchant=merchant,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
            status='completed'
        )
    else:
        today = timezone.now().date()
        month_start = today.replace(day=1)
        transactions = MerchantTransaction.all_objects.filter(
            merchant=merchant,
            created_at__date__gte=month_start,
            status='completed'
        )
    
    # Summary
    summary = transactions.aggregate(
        total_count=Count('id'),
        total_amount=Sum('amount'),
        total_commission=Sum('commission')
    )
    
    # Type breakdown
    type_breakdown = transactions.values('transaction_type').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    context = {
        'merchant': merchant,
        'stats': stats,
        'summary': summary,
        'type_breakdown': type_breakdown,
    }
    return render(request, 'merchant/portal/reports.html', context)


@merchant_required
def portal_profile(request):
    """Merchant profile"""
    merchant = request.merchant
    
    context = {
        'merchant': merchant,
    }
    return render(request, 'merchant/portal/profile.html', context)


@merchant_required
def portal_change_pin(request):
    """Change transaction PIN"""
    merchant = request.merchant
    
    if request.method == 'POST':
        form = MerchantPinChangeForm(request.POST)
        if form.is_valid():
            current_pin = form.cleaned_data['current_pin']
            new_pin = form.cleaned_data['new_pin']
            
            if not merchant.check_transaction_pin(current_pin):
                messages.error(request, 'Current PIN is incorrect')
                return redirect('merchant:portal_change_pin')
            
            merchant.set_transaction_pin(new_pin)
            merchant.save()
            
            log_merchant_activity(
                merchant=merchant,
                activity_type='pin_change',
                description='Transaction PIN changed',
                request=request
            )
            
            messages.success(request, 'Transaction PIN changed successfully')
            return redirect('merchant:portal_profile')
    else:
        form = MerchantPinChangeForm()
    
    context = {
        'merchant': merchant,
        'form': form,
    }
    return render(request, 'merchant/portal/change_pin.html', context)


@merchant_required
def portal_change_password(request):
    """Change merchant user password"""
    merchant = request.merchant
    user = request.user
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('merchant:portal_change_password')
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
            return redirect('merchant:portal_change_password')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return redirect('merchant:portal_change_password')
        
        user.set_password(new_password)
        user.save()
        
        # Log activity
        log_merchant_activity(
            merchant=merchant,
            activity_type='profile_update',
            description='Password changed',
            request=request
        )
        
        messages.success(request, 'Password changed successfully. Please login again.')
        return redirect('merchant:portal_login')
    
    context = {
        'merchant': merchant,
    }
    return render(request, 'merchant/portal/change_password.html', context)


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@merchant_required
@require_GET
def api_validate_customer(request):
    """Validate customer account"""
    merchant = request.merchant
    account_number = request.GET.get('account')
    
    if not account_number:
        return JsonResponse({'success': False, 'message': 'Account number required'})
    
    customer = find_customer_by_account(merchant.branch, account_number)
    
    if customer:
        balance = get_customer_balance(customer.branch, customer.gl_no, customer.ac_no)
        return JsonResponse({
            'success': True,
            'customer': {
                'name': f"{customer.first_name} {customer.last_name}",
                'account': f"{customer.gl_no}{customer.ac_no}",
                'phone': customer.phone_no,
                'balance': str(balance)
            }
        })
    else:
        return JsonResponse({'success': False, 'message': 'Customer not found'})


@merchant_required
@require_GET
def api_get_float_balance(request):
    """Get merchant float balance"""
    merchant = request.merchant
    balance = get_merchant_float_balance(merchant)
    
    return JsonResponse({
        'success': True,
        'balance': str(balance)
    })
