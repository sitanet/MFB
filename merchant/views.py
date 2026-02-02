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
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.db import transaction

from .models import (
    Merchant, MerchantTransaction, MerchantActivityLog,
    MerchantCommission, MerchantServiceConfig, MerchantNotification,
    MerchantNotificationRead, MerchantChatConversation, MerchantChatMessage
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
    branch = request.user.get_branch()
    
    if request.method == 'POST':
        form = MerchantRegistrationForm(request.POST, branch=branch)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Generate unique IDs
                    merchant_id = generate_merchant_id()
                    merchant_code = generate_merchant_code()
                    
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
                    
                    # Set GL account from form selection (ac_no auto-generated in model save)
                    gl_account = form.cleaned_data.get('gl_account')
                    if gl_account:
                        merchant.gl_no = gl_account
                    
                    # Set Float GL account for 9PSB wallet transactions
                    float_gl_account = form.cleaned_data.get('float_gl_account')
                    if float_gl_account:
                        merchant.float_gl_no = float_gl_account
                    
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
                    
                    # Set transaction PIN
                    merchant.set_transaction_pin(form.cleaned_data['transaction_pin'])
                    
                    merchant.save()
                    
                    # Create 9PSB Wallet for merchant
                    wallet_created = False
                    wallet_error = None
                    try:
                        from ninepsb.services import create_merchant_wallet
                        wallet_result = create_merchant_wallet(merchant)
                        
                        # Update merchant with wallet details
                        merchant.psb_wallet_account = wallet_result.get('account_number')
                        merchant.psb_wallet_name = wallet_result.get('account_name')
                        merchant.psb_wallet_status = wallet_result.get('status', 'active')
                        merchant.psb_wallet_tier = wallet_result.get('tier', '1')
                        merchant.psb_wallet_created_at = timezone.now()
                        merchant.save(update_fields=[
                            'psb_wallet_account', 'psb_wallet_name', 
                            'psb_wallet_status', 'psb_wallet_tier', 'psb_wallet_created_at'
                        ])
                        wallet_created = True
                    except Exception as wallet_e:
                        wallet_error = str(wallet_e)
                        # Log the error but don't fail merchant creation
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to create 9PSB wallet for merchant {merchant_id}: {wallet_e}")
                    
                    # Prepare success message
                    if wallet_created:
                        messages.success(
                            request, 
                            f'Merchant created successfully. Merchant ID: {merchant_id}. '
                            f'9PSB Wallet: {merchant.psb_wallet_account}'
                        )
                    else:
                        messages.warning(
                            request, 
                            f'Merchant created successfully. Merchant ID: {merchant_id}. '
                            f'However, 9PSB wallet creation failed: {wallet_error}. '
                            f'You can retry wallet creation from the merchant detail page.'
                        )
                    
                    return redirect('merchant:merchant_detail', merchant_id=merchant.id)
                    
            except Exception as e:
                messages.error(request, f'Error creating merchant: {str(e)}')
    else:
        form = MerchantRegistrationForm(branch=branch)
    
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
    
    # Get 9PSB wallet balance if wallet exists
    psb_wallet_balance = None
    psb_wallet_error = None
    if merchant.psb_wallet_account:
        try:
            from ninepsb.services import WAASService
            waas = WAASService()
            wallet_info = waas.wallet_enquiry(merchant.psb_wallet_account)
            wallet_data = wallet_info.get('data', {})
            psb_wallet_balance = wallet_data.get('availableBalance') or wallet_data.get('balance', '0.00')
        except Exception as e:
            psb_wallet_error = str(e)
    
    context = {
        'merchant': merchant,
        'stats': stats,
        'recent_transactions': recent_transactions,
        'recent_activity': recent_activity,
        'psb_wallet_balance': psb_wallet_balance,
        'psb_wallet_error': psb_wallet_error,
    }
    return render(request, 'merchant/admin/merchant_detail.html', context)


@login_required
@require_POST
def merchant_create_wallet(request, merchant_id):
    """Retry creating 9PSB wallet for merchant (FinanceFlex Admin)"""
    merchant = get_object_or_404(Merchant, id=merchant_id)
    
    if merchant.psb_wallet_account:
        messages.warning(request, 'Merchant already has a 9PSB wallet')
        return redirect('merchant:merchant_detail', merchant_id=merchant.id)
    
    # Check required fields
    if not merchant.bvn and not merchant.nin:
        messages.error(request, 'BVN or NIN is required for wallet creation')
        return redirect('merchant:merchant_detail', merchant_id=merchant.id)
    
    if not merchant.date_of_birth:
        messages.error(request, 'Date of Birth is required for wallet creation')
        return redirect('merchant:merchant_detail', merchant_id=merchant.id)
    
    if not merchant.business_phone:
        messages.error(request, 'Business phone is required for wallet creation')
        return redirect('merchant:merchant_detail', merchant_id=merchant.id)
    
    try:
        from ninepsb.services import create_merchant_wallet
        wallet_result = create_merchant_wallet(merchant)
        
        # Update merchant with wallet details
        merchant.psb_wallet_account = wallet_result.get('account_number')
        merchant.psb_wallet_name = wallet_result.get('account_name')
        merchant.psb_wallet_status = wallet_result.get('status', 'active')
        merchant.psb_wallet_tier = wallet_result.get('tier', '1')
        merchant.psb_wallet_created_at = timezone.now()
        merchant.save(update_fields=[
            'psb_wallet_account', 'psb_wallet_name',
            'psb_wallet_status', 'psb_wallet_tier', 'psb_wallet_created_at'
        ])
        
        messages.success(
            request,
            f'9PSB Wallet created successfully. Account: {merchant.psb_wallet_account}'
        )
    except Exception as e:
        messages.error(request, f'Failed to create 9PSB wallet: {str(e)}')
    
    return redirect('merchant:merchant_detail', merchant_id=merchant.id)


@login_required
@require_GET
def merchant_wallet_balance(request, merchant_id):
    """Get merchant 9PSB wallet balance (API endpoint)"""
    merchant = get_object_or_404(Merchant, id=merchant_id)
    
    if not merchant.psb_wallet_account:
        return JsonResponse({'success': False, 'message': 'No wallet found'})
    
    try:
        from ninepsb.services import WAASService
        waas = WAASService()
        wallet_info = waas.wallet_enquiry(merchant.psb_wallet_account)
        wallet_data = wallet_info.get('data', {})
        
        return JsonResponse({
            'success': True,
            'balance': wallet_data.get('availableBalance') or wallet_data.get('balance', '0.00'),
            'account_name': wallet_data.get('accountName'),
            'account_number': merchant.psb_wallet_account,
            'status': wallet_data.get('status'),
            'tier': wallet_data.get('tier'),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def merchant_update(request, merchant_id):
    """Update merchant details (FinanceFlex Admin)"""
    merchant = get_object_or_404(Merchant, id=merchant_id)
    branch = request.user.get_branch()
    had_wallet = bool(merchant.psb_wallet_account)
    
    if request.method == 'POST':
        form = MerchantUpdateForm(request.POST, instance=merchant, branch=branch)
        if form.is_valid():
            # Handle GL account selection for merchants without gl_no/ac_no
            gl_account = form.cleaned_data.get('gl_account')
            if gl_account and not merchant.gl_no:
                merchant.gl_no = gl_account
                # ac_no will be auto-generated in model save()
            
            merchant = form.save()
            
            # Check if wallet was manually entered
            if merchant.psb_wallet_account and not had_wallet:
                # Admin manually entered wallet account - just save it
                merchant.psb_wallet_status = 'active'
                merchant.psb_wallet_created_at = timezone.now()
                merchant.save(update_fields=['psb_wallet_status', 'psb_wallet_created_at'])
                messages.success(request, f'Merchant updated. 9PSB Wallet linked: {merchant.psb_wallet_account}')
                return redirect('merchant:merchant_detail', merchant_id=merchant.id)
            
            # If merchant doesn't have wallet yet, try to create one
            if not had_wallet and not merchant.psb_wallet_account:
                # Check if we have required fields for wallet creation
                has_bvn_or_nin = bool(merchant.bvn or merchant.nin)
                has_dob = bool(merchant.date_of_birth)
                has_gender = bool(merchant.gender)
                has_phone = bool(merchant.business_phone)
                has_address = bool(merchant.address or merchant.business_address)
                
                can_create_wallet = has_bvn_or_nin and has_dob and has_gender and has_phone and has_address
                
                if can_create_wallet:
                    try:
                        from ninepsb.services import create_merchant_wallet
                        wallet_result = create_merchant_wallet(merchant)
                        
                        # Update merchant with wallet details
                        account_number = wallet_result.get('account_number')
                        if account_number:
                            merchant.psb_wallet_account = account_number
                            merchant.psb_wallet_name = wallet_result.get('account_name') or merchant.merchant_name
                            merchant.psb_wallet_status = wallet_result.get('status', 'active')
                            merchant.psb_wallet_tier = wallet_result.get('tier', '1')
                            merchant.psb_wallet_created_at = timezone.now()
                            merchant.save(update_fields=[
                                'psb_wallet_account', 'psb_wallet_name',
                                'psb_wallet_status', 'psb_wallet_tier', 'psb_wallet_created_at'
                            ])
                            
                            messages.success(
                                request,
                                f'Merchant updated successfully. 9PSB Wallet created: {merchant.psb_wallet_account}'
                            )
                        else:
                            messages.warning(
                                request,
                                f'Merchant updated. Wallet API returned no account number. Response: {wallet_result.get("message", "Unknown")}'
                            )
                    except Exception as wallet_e:
                        import logging
                        import traceback
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to create 9PSB wallet for merchant {merchant.merchant_id}: {wallet_e}")
                        logger.error(traceback.format_exc())
                        messages.warning(
                            request,
                            f'Merchant updated successfully. However, 9PSB wallet creation failed: {str(wallet_e)}'
                        )
                else:
                    messages.success(request, 'Merchant updated successfully')
                    # Show what's missing
                    missing = []
                    if not has_bvn_or_nin:
                        missing.append("BVN or NIN")
                    if not has_dob:
                        missing.append("Date of Birth")
                    if not has_gender:
                        missing.append("Gender")
                    if not has_phone:
                        missing.append("Business Phone")
                    if not has_address:
                        missing.append("Address")
                    
                    if missing:
                        messages.info(
                            request,
                            f'To create 9PSB wallet, please provide: {", ".join(missing)}'
                        )
            else:
                messages.success(request, 'Merchant updated successfully')
            
            return redirect('merchant:merchant_detail', merchant_id=merchant.id)
    else:
        form = MerchantUpdateForm(instance=merchant, branch=branch)
    
    context = {
        'form': form,
        'merchant': merchant,
        'has_wallet': had_wallet,
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

@csrf_exempt
def merchant_login(request):
    """Merchant portal login"""
    # Check if this is an API request (mobile app)
    is_api_request = (
        request.content_type == 'application/json' or
        request.headers.get('Accept') == 'application/json' or
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )
    
    if request.method == 'POST':
        # Handle JSON request body for API
        if is_api_request:
            try:
                data = json.loads(request.body)
                username = data.get('username', '')
                password = data.get('password', '')
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
        else:
            form = MerchantLoginForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
            else:
                if is_api_request:
                    return JsonResponse({'success': False, 'message': 'Invalid form data'}, status=400)
                return render(request, 'merchant/portal/login.html', {'form': form})
        
        # Try to find user by username first, then authenticate with email
        try:
            from accounts.models import User
            merchant_user = User.objects.get(username=username)
            print(f"[DEBUG] Found user: {merchant_user.username}, email: {merchant_user.email}")
            user = authenticate(request, email=merchant_user.email, password=password)
            print(f"[DEBUG] Authentication result: {user}")
        except User.DoesNotExist:
            print(f"[DEBUG] User not found with username: {username}")
            user = None
        
        if user is not None:
            # Check if user has merchant profile
            try:
                merchant = user.merchant_profile
                if merchant.status != 'active':
                    if is_api_request:
                        return JsonResponse({'success': False, 'message': 'Your merchant account is not active'}, status=403)
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
                
                if is_api_request:
                    return JsonResponse({
                        'success': True,
                        'message': 'Login successful',
                        'merchant': {
                            'id': merchant.id,
                            'merchant_id': merchant.merchant_id,
                            'merchant_code': merchant.merchant_code,
                            'merchant_name': merchant.merchant_name,
                            'business_name': merchant.business_name,
                            'status': merchant.status,
                            'wallet_number': merchant.psb_wallet_account,
                            'financeflex_account': merchant.get_account_number(),
                        }
                    })
                
                return redirect('merchant:portal_dashboard')
            except Merchant.DoesNotExist:
                if is_api_request:
                    return JsonResponse({'success': False, 'message': 'No merchant account found for this user'}, status=404)
                messages.error(request, 'No merchant account found for this user')
        else:
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
            
            if is_api_request:
                return JsonResponse({'success': False, 'message': 'Invalid username or password'}, status=401)
            messages.error(request, 'Invalid username or password')
    else:
        form = MerchantLoginForm()
    
    if is_api_request:
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
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
        # Check if this is an API request
        is_api_request = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.content_type == 'application/json' or
            request.headers.get('Accept') == 'application/json' or
            '/api/' in request.path
        )
        
        if not request.user.is_authenticated:
            if is_api_request:
                return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
            return redirect('merchant:portal_login')
        
        try:
            merchant = request.user.merchant_profile
            if merchant.status != 'active':
                if is_api_request:
                    return JsonResponse({'success': False, 'message': 'Merchant account is not active'}, status=403)
                messages.error(request, 'Your merchant account is not active')
                return redirect('merchant:portal_login')
            request.merchant = merchant
        except Merchant.DoesNotExist:
            if is_api_request:
                return JsonResponse({'success': False, 'message': 'No merchant account found'}, status=403)
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
    
    # Get 9PSB wallet balance if wallet exists
    psb_wallet_balance = None
    psb_wallet_error = None
    if merchant.psb_wallet_account:
        try:
            from ninepsb.services import WAASService
            waas = WAASService()
            wallet_info = waas.wallet_enquiry(merchant.psb_wallet_account)
            wallet_data = wallet_info.get('data', {})
            psb_wallet_balance = wallet_data.get('availableBalance') or wallet_data.get('balance', '0.00')
        except Exception as e:
            psb_wallet_error = str(e)
    
    context = {
        'merchant': merchant,
        'stats': stats,
        'recent_transactions': recent_transactions,
        'psb_wallet_balance': psb_wallet_balance,
        'psb_wallet_error': psb_wallet_error,
    }
    return render(request, 'merchant/portal/dashboard.html', context)


from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib import messages

@merchant_required
def portal_deposit(request):
    """Customer deposit - TEMPORARILY DISABLED"""
    merchant = request.merchant
    
    context = {
        'merchant': merchant,
        'float_balance': get_merchant_float_balance(merchant),
        'coming_soon': True,
    }

    return render(request, 'merchant/portal/deposit.html', context)


@merchant_required
def portal_withdrawal(request):
    """Customer withdrawal - Step 1: Initiate and send OTP"""
    merchant = request.merchant
    
    if request.method == 'POST':
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            account_number = form.cleaned_data['customer_account']
            amount = form.cleaned_data['amount']
            narration = form.cleaned_data.get('narration', '')
            pin = request.POST.get('transaction_pin', '')
            
            # Verify merchant PIN
            if not merchant.check_transaction_pin(pin):
                messages.error(request, 'Invalid transaction PIN')
                return redirect('merchant:portal_withdrawal')
            
            # Find customer
            customer = find_customer_by_account(merchant.branch, account_number)
            if not customer:
                messages.error(request, 'Customer account not found')
                return redirect('merchant:portal_withdrawal')
            
            # Check if customer has phone number
            if not customer.phone_no:
                messages.error(request, 'Customer does not have a phone number registered')
                return redirect('merchant:portal_withdrawal')
            
            # Generate OTP and send SMS
            from .models import MerchantWithdrawalOTP
            from accounts.utils import send_sms
            from datetime import timedelta
            
            otp_code = MerchantWithdrawalOTP.generate_otp()
            expires_at = timezone.now() + timedelta(minutes=5)
            
            # Create OTP record
            otp_record = MerchantWithdrawalOTP.objects.create(
                merchant=merchant,
                customer_account=account_number,
                customer_phone=customer.phone_no,
                amount=amount,
                narration=narration,
                otp_code=otp_code,
                expires_at=expires_at
            )
            
            # Send OTP via SMS and Email
            sms_message = f"Your withdrawal OTP is {otp_code}. Amount: NGN{amount}. Valid for 5 minutes. Do not share with anyone."
            sms_sent = False
            email_sent = False
            
            # Send SMS
            try:
                send_sms(customer.phone_no, sms_message)
                sms_sent = True
            except Exception as e:
                print(f"SMS sending failed: {e}")
            
            # Send Email
            if customer.email:
                try:
                    from django.core.mail import EmailMessage
                    from django.conf import settings
                    
                    email_subject = "Withdrawal OTP - FinanceFlex"
                    email_body = f"""
Dear {customer.first_name},

Your withdrawal OTP is: {otp_code}

Transaction Details:
- Amount: NGN {amount:,.2f}
- Merchant: {merchant.merchant_name}

This OTP is valid for 5 minutes. Do not share this code with anyone.

If you did not initiate this transaction, please contact us immediately.

Best regards,
FinanceFlex Team
                    """
                    email = EmailMessage(
                        email_subject,
                        email_body.strip(),
                        settings.DEFAULT_FROM_EMAIL,
                        [customer.email]
                    )
                    email.send()
                    email_sent = True
                except Exception as e:
                    print(f"Email sending failed: {e}")
            
            # Check if at least one delivery method succeeded
            if not sms_sent and not email_sent:
                messages.error(request, 'Failed to send OTP. Please try again.')
                otp_record.delete()
                return redirect('merchant:portal_withdrawal')
            
            # Build notification message
            notifications = []
            if sms_sent:
                notifications.append(f"phone ...{customer.phone_no[-4:]}")
            if email_sent:
                notifications.append(f"email ...{customer.email[-10:]}" if len(customer.email) > 10 else "email")
            
            messages.info(request, f'OTP sent to customer {" and ".join(notifications)}')
            return redirect('merchant:portal_withdrawal_verify', otp_id=otp_record.id)
    else:
        form = WithdrawalForm()
    
    context = {
        'merchant': merchant,
        'form': form,
        'float_balance': get_merchant_float_balance(merchant),
    }
    return render(request, 'merchant/portal/withdrawal.html', context)


@merchant_required
def portal_withdrawal_verify(request, otp_id):
    """Customer withdrawal - Step 2: Verify OTP and complete withdrawal"""
    merchant = request.merchant
    
    from .models import MerchantWithdrawalOTP
    
    try:
        otp_record = MerchantWithdrawalOTP.objects.get(id=otp_id, merchant=merchant)
    except MerchantWithdrawalOTP.DoesNotExist:
        messages.error(request, 'Invalid or expired OTP session')
        return redirect('merchant:portal_withdrawal')
    
    # Check if OTP is still valid
    if not otp_record.is_valid():
        messages.error(request, 'OTP has expired. Please initiate a new withdrawal.')
        return redirect('merchant:portal_withdrawal')
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '')
        
        if otp_record.verify(otp_code):
            # OTP verified, process withdrawal
            customer = find_customer_by_account(merchant.branch, otp_record.customer_account)
            if not customer:
                messages.error(request, 'Customer account not found')
                return redirect('merchant:portal_withdrawal')
            
            try:
                trx = process_merchant_withdrawal(
                    merchant, 
                    customer, 
                    otp_record.amount, 
                    otp_record.narration, 
                    request
                )
                messages.success(request, f'Withdrawal successful. Reference: {trx.transaction_ref}')
                return redirect('merchant:portal_transaction_detail', trx_ref=trx.transaction_ref)
            except Exception as e:
                messages.error(request, str(e))
                return redirect('merchant:portal_withdrawal')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
    
    # Mask phone number for display
    masked_phone = f"***{otp_record.customer_phone[-4:]}" if len(otp_record.customer_phone) >= 4 else "****"
    
    context = {
        'merchant': merchant,
        'otp_record': otp_record,
        'masked_phone': masked_phone,
        'float_balance': get_merchant_float_balance(merchant),
    }
    return render(request, 'merchant/portal/withdrawal_verify.html', context)


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
    stats = get_merchant_dashboard_stats(merchant)
    
    # Get 9PSB wallet balance if wallet exists
    psb_wallet_balance = None
    if merchant.psb_wallet_account:
        try:
            from ninepsb.services import WAASService
            waas = WAASService()
            wallet_info = waas.wallet_enquiry(merchant.psb_wallet_account)
            wallet_data = wallet_info.get('data', {})
            psb_wallet_balance = wallet_data.get('availableBalance') or wallet_data.get('balance', '0.00')
        except Exception:
            psb_wallet_balance = "0.00"
    
    context = {
        'merchant': merchant,
        'stats': stats,
        'psb_wallet_balance': psb_wallet_balance,
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
        'balance': str(balance),
        'wallet_number': merchant.psb_wallet_account,
        'financeflex_account': merchant.get_account_number(),
    })


# ==============================================================================
# MOBILE APP API ENDPOINTS
# ==============================================================================

@csrf_exempt
@require_POST
def api_withdrawal_initiate(request):
    """API: Initiate withdrawal and send OTP to customer"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    if merchant.status != 'active':
        return JsonResponse({'success': False, 'message': 'Merchant account is not active'}, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    
    account_number = data.get('customer_account', '')
    amount = data.get('amount')
    narration = data.get('narration', '')
    pin = data.get('transaction_pin', '')
    
    # Validate inputs
    if not account_number or not amount or not pin:
        return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)
    
    # Verify merchant PIN
    if not merchant.check_transaction_pin(pin):
        return JsonResponse({'success': False, 'message': 'Invalid transaction PIN'}, status=400)
    
    # Find customer
    customer = find_customer_by_account(merchant.branch, account_number)
    if not customer:
        return JsonResponse({'success': False, 'message': 'Customer account not found'}, status=404)
    
    # Check if customer has phone number
    if not customer.phone_no:
        return JsonResponse({'success': False, 'message': 'Customer has no phone number registered'}, status=400)
    
    # Generate OTP
    from .models import MerchantWithdrawalOTP
    from accounts.utils import send_sms
    from datetime import timedelta
    
    otp_code = MerchantWithdrawalOTP.generate_otp()
    expires_at = timezone.now() + timedelta(minutes=5)
    
    otp_record = MerchantWithdrawalOTP.objects.create(
        merchant=merchant,
        customer_account=account_number,
        customer_phone=customer.phone_no,
        amount=amount,
        narration=narration,
        otp_code=otp_code,
        expires_at=expires_at
    )
    
    # Send OTP via SMS and Email
    sms_message = f"Your withdrawal OTP is {otp_code}. Amount: NGN{amount}. Valid for 5 minutes."
    sms_sent = False
    email_sent = False
    
    try:
        send_sms(customer.phone_no, sms_message)
        sms_sent = True
    except:
        pass
    
    if customer.email:
        try:
            from django.core.mail import EmailMessage
            from django.conf import settings
            
            email = EmailMessage(
                "Withdrawal OTP - FinanceFlex",
                f"Your withdrawal OTP is: {otp_code}\nAmount: NGN {amount:,.2f}\nValid for 5 minutes.",
                settings.DEFAULT_FROM_EMAIL,
                [customer.email]
            )
            email.send()
            email_sent = True
        except:
            pass
    
    if not sms_sent and not email_sent:
        otp_record.delete()
        return JsonResponse({'success': False, 'message': 'Failed to send OTP'}, status=500)
    
    masked_phone = f"***{customer.phone_no[-4:]}" if len(customer.phone_no) >= 4 else "****"
    
    return JsonResponse({
        'success': True,
        'message': 'OTP sent successfully',
        'otp_id': otp_record.id,
        'masked_phone': masked_phone,
        'customer_name': f"{customer.first_name} {customer.last_name}",
        'amount': str(amount),
        'expires_in': 300  # seconds
    })


@csrf_exempt
@require_POST
def api_withdrawal_verify(request):
    """API: Verify OTP and complete withdrawal"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    
    otp_id = data.get('otp_id')
    otp_code = data.get('otp_code', '')
    
    if not otp_id or not otp_code:
        return JsonResponse({'success': False, 'message': 'OTP ID and code required'}, status=400)
    
    from .models import MerchantWithdrawalOTP
    
    try:
        otp_record = MerchantWithdrawalOTP.objects.get(id=otp_id, merchant=merchant)
    except MerchantWithdrawalOTP.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid OTP session'}, status=404)
    
    if not otp_record.is_valid():
        return JsonResponse({'success': False, 'message': 'OTP has expired'}, status=400)
    
    if not otp_record.verify(otp_code):
        return JsonResponse({'success': False, 'message': 'Invalid OTP code'}, status=400)
    
    # Process withdrawal
    customer = find_customer_by_account(merchant.branch, otp_record.customer_account)
    if not customer:
        return JsonResponse({'success': False, 'message': 'Customer not found'}, status=404)
    
    try:
        trx = process_merchant_withdrawal(
            merchant, customer, otp_record.amount, otp_record.narration, request
        )
        return JsonResponse({
            'success': True,
            'message': 'Withdrawal successful',
            'transaction_ref': trx.transaction_ref,
            'amount': str(trx.amount),
            'customer_name': f"{customer.first_name} {customer.last_name}"
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@csrf_exempt
def api_dashboard(request):
    """API: Get merchant dashboard data"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    stats = get_merchant_dashboard_stats(merchant)
    
    # Recent transactions
    recent_transactions = MerchantTransaction.all_objects.filter(
        merchant=merchant
    ).order_by('-created_at')[:10]
    
    transactions_data = [{
        'id': t.id,
        'reference': t.transaction_ref,
        'type': t.transaction_type,
        'type_display': t.get_transaction_type_display(),
        'amount': str(t.amount),
        'status': t.status,
        'customer_name': t.customer_name,
        'created_at': t.created_at.isoformat(),
    } for t in recent_transactions]
    
    return JsonResponse({
        'success': True,
        'merchant': {
            'id': merchant.id,
            'merchant_id': merchant.merchant_id,
            'merchant_code': merchant.merchant_code,
            'merchant_name': merchant.merchant_name,
            'business_name': merchant.business_name,
            'status': merchant.status,
            'wallet_number': merchant.psb_wallet_account,
            'financeflex_account': merchant.get_account_number(),
        },
        'float_balance': str(get_merchant_float_balance(merchant)),
        'stats': stats,
        'recent_transactions': transactions_data,
    })


@csrf_exempt
def api_transactions(request):
    """API: Get merchant transactions list"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    transactions = MerchantTransaction.all_objects.filter(merchant=merchant)
    
    # Filters
    trx_type = request.GET.get('type')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    
    if trx_type:
        transactions = transactions.filter(transaction_type=trx_type)
    if status:
        transactions = transactions.filter(status=status)
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)
    
    transactions = transactions.order_by('-created_at')
    
    # Pagination
    total = transactions.count()
    offset = (page - 1) * limit
    transactions = transactions[offset:offset + limit]
    
    transactions_data = [{
        'id': t.id,
        'reference': t.transaction_ref,
        'type': t.transaction_type,
        'type_display': t.get_transaction_type_display(),
        'amount': str(t.amount),
        'charge': str(t.charge),
        'commission': str(t.commission),
        'status': t.status,
        'customer_name': t.customer_name,
        'customer_account': t.customer_account,
        'narration': t.narration,
        'created_at': t.created_at.isoformat(),
    } for t in transactions]
    
    # Get today's stats
    today = timezone.now().date()
    today_transactions = MerchantTransaction.all_objects.filter(
        merchant=merchant,
        created_at__date=today,
        status='completed'
    )
    today_count = today_transactions.count()
    today_commission = today_transactions.aggregate(total=Sum('commission'))['total'] or Decimal('0.00')
    
    return JsonResponse({
        'success': True,
        'transactions': transactions_data,
        'stats': {
            'today_count': today_count,
            'today_commission': str(today_commission),
        },
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': (total + limit - 1) // limit,
        }
    })


@csrf_exempt
def api_transaction_detail(request, trx_ref):
    """API: Get transaction details"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    try:
        trx = MerchantTransaction.objects.get(merchant=merchant, transaction_ref=trx_ref)
    except MerchantTransaction.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Transaction not found'}, status=404)
    
    return JsonResponse({
        'success': True,
        'transaction': {
            'id': trx.id,
            'reference': trx.transaction_ref,
            'type': trx.transaction_type,
            'type_display': trx.get_transaction_type_display(),
            'amount': str(trx.amount),
            'charge': str(trx.charge),
            'commission': str(trx.commission),
            'status': trx.status,
            'customer_name': trx.customer_name,
            'customer_account': trx.customer_account,
            'customer_phone': trx.customer_phone,
            'narration': trx.narration,
            'float_balance_before': str(trx.float_balance_before) if trx.float_balance_before else None,
            'float_balance_after': str(trx.float_balance_after) if trx.float_balance_after else None,
            'created_at': trx.created_at.isoformat(),
            'completed_at': trx.completed_at.isoformat() if trx.completed_at else None,
        }
    })


@csrf_exempt
def api_profile(request):
    """API: Get/Update merchant profile"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    return JsonResponse({
        'success': True,
        'profile': {
            'merchant_id': merchant.merchant_id,
            'merchant_code': merchant.merchant_code,
            'merchant_name': merchant.merchant_name,
            'merchant_type': merchant.merchant_type,
            'business_name': merchant.business_name,
            'business_address': merchant.business_address,
            'business_phone': merchant.business_phone,
            'business_email': merchant.business_email,
            'contact_person_name': merchant.contact_person_name,
            'contact_person_phone': merchant.contact_person_phone,
            'state': merchant.state,
            'lga': merchant.lga,
            'city': merchant.city,
            'status': merchant.status,
            'daily_transaction_limit': str(merchant.daily_transaction_limit),
            'single_transaction_limit': str(merchant.single_transaction_limit),
            'created_at': merchant.created_at.isoformat(),
        }
    })


@csrf_exempt
@require_POST
def api_change_pin(request):
    """API: Change transaction PIN"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    
    current_pin = data.get('current_pin', '')
    new_pin = data.get('new_pin', '')
    
    if not current_pin or not new_pin:
        return JsonResponse({'success': False, 'message': 'Current and new PIN required'}, status=400)
    
    if not merchant.check_transaction_pin(current_pin):
        return JsonResponse({'success': False, 'message': 'Current PIN is incorrect'}, status=400)
    
    if len(new_pin) < 4:
        return JsonResponse({'success': False, 'message': 'PIN must be at least 4 digits'}, status=400)
    
    merchant.set_transaction_pin(new_pin)
    merchant.save()
    
    log_merchant_activity(
        merchant=merchant,
        activity_type='pin_change',
        description='Transaction PIN changed via API',
        request=request
    )
    
    return JsonResponse({'success': True, 'message': 'PIN changed successfully'})


@csrf_exempt
@require_POST
def api_change_password(request):
    """API: Change merchant user password"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not current_password or not new_password:
        return JsonResponse({'success': False, 'message': 'Current and new password required'}, status=400)
    
    if not request.user.check_password(current_password):
        return JsonResponse({'success': False, 'message': 'Current password is incorrect'}, status=400)
    
    if len(new_password) < 8:
        return JsonResponse({'success': False, 'message': 'Password must be at least 8 characters'}, status=400)
    
    request.user.set_password(new_password)
    request.user.save()
    
    try:
        merchant = request.user.merchant_profile
        log_merchant_activity(
            merchant=merchant,
            activity_type='profile_update',
            description='Password changed via API',
            request=request
        )
    except:
        pass
    
    return JsonResponse({'success': True, 'message': 'Password changed successfully'})


# ==============================================================================
# NOTIFICATION MANAGEMENT (ADMIN)
# ==============================================================================

@login_required
def notification_list(request):
    """List all notifications sent by admin"""
    notifications = MerchantNotification.objects.filter(
        branch=request.user.branch
    ).order_by('-created_at')
    
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page', 1)
    notifications = paginator.get_page(page)
    
    return render(request, 'merchant/admin/notification_list.html', {
        'notifications': notifications,
    })


@login_required
def notification_create(request):
    """Create and send a new notification"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        notification_type = request.POST.get('notification_type', 'info')
        target_type = request.POST.get('target_type', 'all')
        merchant_ids = request.POST.getlist('merchant_ids')
        
        if not title or not message:
            messages.error(request, 'Title and message are required')
            return redirect('merchant:notification_create')
        
        if target_type == 'all':
            # Broadcast to all merchants
            MerchantNotification.objects.create(
                title=title,
                message=message,
                notification_type=notification_type,
                merchant=None,
                branch=request.user.branch,
                created_by=request.user,
            )
            messages.success(request, 'Notification sent to all merchants')
        else:
            # Send to selected merchants
            if not merchant_ids:
                messages.error(request, 'Please select at least one merchant')
                return redirect('merchant:notification_create')
            
            merchants = Merchant.objects.filter(id__in=merchant_ids, branch=request.user.branch)
            count = 0
            for merchant in merchants:
                MerchantNotification.objects.create(
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    merchant=merchant,
                    branch=request.user.branch,
                    created_by=request.user,
                )
                count += 1
            messages.success(request, f'Notification sent to {count} merchant(s)')
        
        return redirect('merchant:notification_list')
    
    merchants = Merchant.objects.filter(branch=request.user.branch, status='active')
    return render(request, 'merchant/admin/notification_create.html', {
        'merchants': merchants,
        'notification_types': MerchantNotification.NOTIFICATION_TYPES,
    })


# ==============================================================================
# NOTIFICATION API (MOBILE APP)
# ==============================================================================

@csrf_exempt
def api_notifications(request):
    """API: Get notifications for merchant"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    # Get notifications for this merchant (specific + broadcast)
    notifications = MerchantNotification.objects.filter(
        Q(merchant=merchant) | Q(merchant__isnull=True, branch=merchant.branch)
    ).order_by('-created_at')[:50]
    
    # Get read notification IDs
    read_ids = set(MerchantNotificationRead.objects.filter(
        merchant=merchant
    ).values_list('notification_id', flat=True))
    
    notifications_data = [{
        'id': n.id,
        'uuid': str(n.uuid),
        'title': n.title,
        'message': n.message,
        'type': n.notification_type,
        'is_read': n.id in read_ids,
        'created_at': n.created_at.isoformat(),
    } for n in notifications]
    
    unread_count = len([n for n in notifications_data if not n['is_read']])
    
    return JsonResponse({
        'success': True,
        'notifications': notifications_data,
        'unread_count': unread_count,
    })


@csrf_exempt
@require_POST
def api_notification_read(request):
    """API: Mark notification as read"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    
    notification_id = data.get('notification_id')
    if not notification_id:
        return JsonResponse({'success': False, 'message': 'Notification ID required'}, status=400)
    
    try:
        notification = MerchantNotification.objects.get(id=notification_id)
        MerchantNotificationRead.objects.get_or_create(
            notification=notification,
            merchant=merchant
        )
        return JsonResponse({'success': True, 'message': 'Marked as read'})
    except MerchantNotification.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Notification not found'}, status=404)


@csrf_exempt
@require_POST
def api_notifications_mark_all_read(request):
    """API: Mark all notifications as read"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    notifications = MerchantNotification.objects.filter(
        Q(merchant=merchant) | Q(merchant__isnull=True, branch=merchant.branch)
    )
    
    for notification in notifications:
        MerchantNotificationRead.objects.get_or_create(
            notification=notification,
            merchant=merchant
        )
    
    return JsonResponse({'success': True, 'message': 'All notifications marked as read'})


# ==============================================================================
# CHAT API (MOBILE APP)
# ==============================================================================

@csrf_exempt
def api_chat_conversations(request):
    """API: Get all chat conversations for merchant"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    conversations = MerchantChatConversation.objects.filter(merchant=merchant)
    
    conversations_data = []
    for conv in conversations:
        last_message = conv.get_last_message()
        conversations_data.append({
            'id': conv.id,
            'uuid': str(conv.uuid),
            'subject': conv.subject,
            'status': conv.status,
            'unread_count': conv.unread_count_for_merchant(),
            'last_message': last_message.content[:50] if last_message else None,
            'last_message_at': last_message.created_at.isoformat() if last_message else None,
            'created_at': conv.created_at.isoformat(),
            'updated_at': conv.updated_at.isoformat(),
        })
    
    total_unread = sum(c['unread_count'] for c in conversations_data)
    
    return JsonResponse({
        'success': True,
        'conversations': conversations_data,
        'total_unread': total_unread,
    })


@csrf_exempt
def api_chat_messages(request, conversation_id):
    """API: Get messages for a specific conversation"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    try:
        conversation = MerchantChatConversation.objects.get(id=conversation_id, merchant=merchant)
    except MerchantChatConversation.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Conversation not found'}, status=404)
    
    # Mark admin messages as read
    conversation.messages.filter(is_from_merchant=False, is_read=False).update(is_read=True)
    
    messages_list = conversation.messages.all()
    messages_data = [{
        'id': m.id,
        'uuid': str(m.uuid),
        'content': m.content,
        'is_from_merchant': m.is_from_merchant,
        'is_read': m.is_read,
        'created_at': m.created_at.isoformat(),
    } for m in messages_list]
    
    return JsonResponse({
        'success': True,
        'conversation': {
            'id': conversation.id,
            'uuid': str(conversation.uuid),
            'subject': conversation.subject,
            'status': conversation.status,
        },
        'messages': messages_data,
    })


@csrf_exempt
@require_POST
def api_chat_send_message(request):
    """API: Send a message in a conversation"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    
    conversation_id = data.get('conversation_id')
    content = data.get('content', '').strip()
    
    if not content:
        return JsonResponse({'success': False, 'message': 'Message content is required'}, status=400)
    
    try:
        conversation = MerchantChatConversation.objects.get(id=conversation_id, merchant=merchant)
    except MerchantChatConversation.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Conversation not found'}, status=404)
    
    if conversation.status == 'closed':
        return JsonResponse({'success': False, 'message': 'This conversation is closed'}, status=400)
    
    message = MerchantChatMessage.objects.create(
        conversation=conversation,
        content=content,
        is_from_merchant=True,
    )
    
    # Update conversation timestamp
    conversation.save()
    
    return JsonResponse({
        'success': True,
        'message': {
            'id': message.id,
            'uuid': str(message.uuid),
            'content': message.content,
            'is_from_merchant': message.is_from_merchant,
            'created_at': message.created_at.isoformat(),
        }
    })


@csrf_exempt
@require_POST
def api_chat_create_conversation(request):
    """API: Create a new conversation"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    try:
        merchant = request.user.merchant_profile
    except Merchant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Merchant account not found'}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    
    subject = data.get('subject', '').strip()
    initial_message = data.get('message', '').strip()
    
    if not subject:
        return JsonResponse({'success': False, 'message': 'Subject is required'}, status=400)
    
    if not initial_message:
        return JsonResponse({'success': False, 'message': 'Initial message is required'}, status=400)
    
    conversation = MerchantChatConversation.objects.create(
        merchant=merchant,
        subject=subject,
    )
    
    MerchantChatMessage.objects.create(
        conversation=conversation,
        content=initial_message,
        is_from_merchant=True,
    )
    
    return JsonResponse({
        'success': True,
        'conversation': {
            'id': conversation.id,
            'uuid': str(conversation.uuid),
            'subject': conversation.subject,
            'status': conversation.status,
            'created_at': conversation.created_at.isoformat(),
        }
    })


# ==============================================================================
# CHAT MANAGEMENT (ADMIN)
# ==============================================================================

@login_required
def chat_list(request):
    """List all merchant chat conversations for admin"""
    status_filter = request.GET.get('status', '')
    
    conversations = MerchantChatConversation.objects.filter(
        merchant__branch=request.user.branch
    )
    
    if status_filter:
        conversations = conversations.filter(status=status_filter)
    
    conversations = conversations.order_by('-updated_at')
    
    paginator = Paginator(conversations, 20)
    page = request.GET.get('page', 1)
    conversations = paginator.get_page(page)
    
    return render(request, 'merchant/admin/chat_list.html', {
        'conversations': conversations,
        'status_filter': status_filter,
    })


@login_required
def chat_detail(request, conversation_id):
    """View and reply to a specific conversation"""
    conversation = get_object_or_404(
        MerchantChatConversation,
        id=conversation_id,
        merchant__branch=request.user.branch
    )
    
    # Mark merchant messages as read
    conversation.messages.filter(is_from_merchant=True, is_read=False).update(is_read=True)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        action = request.POST.get('action', '')
        
        if action == 'close':
            conversation.status = 'closed'
            conversation.save()
            messages.success(request, 'Conversation closed')
        elif action == 'reopen':
            conversation.status = 'open'
            conversation.save()
            messages.success(request, 'Conversation reopened')
        elif content:
            MerchantChatMessage.objects.create(
                conversation=conversation,
                content=content,
                is_from_merchant=False,
                admin_user=request.user,
            )
            conversation.save()
            messages.success(request, 'Reply sent')
        
        return redirect('merchant:chat_detail', conversation_id=conversation.id)
    
    return render(request, 'merchant/admin/chat_detail.html', {
        'conversation': conversation,
        'messages_list': conversation.messages.all(),
    })


# ==============================================================================
# NIN VERIFICATION
# ==============================================================================

import requests
from django.conf import settings
from .utils import process_nin_verification_charge

def check_nin_api_balance(api_key, required_amount):
    """Check if CheckMyNINBVN API has sufficient balance"""
    try:
        response = requests.get(
            'https://checkmyninbvn.com.ng/api/balance',
            headers={'x-api-key': api_key},
            timeout=15
        )
        result = response.json()
        if result.get('status') == 'success':
            balance = result.get('data', {}).get('balance', 0)
            return True, float(balance)
        return False, 0
    except Exception:
        return False, 0


@merchant_required
def portal_nin_verification(request):
    """NIN Verification and Print Slip"""
    merchant = request.merchant
    nin_data = None
    error_message = None
    merchant_charge = None
    api_balance = None
    
    # Get NIN config to show charge amount
    from .models import NINVerificationConfig
    try:
        nin_config = NINVerificationConfig.objects.get(branch=merchant.branch)
        merchant_charge = nin_config.merchant_charge
        api_cost = nin_config.api_cost
        if not nin_config.is_enabled:
            error_message = "NIN verification service is currently disabled."
    except NINVerificationConfig.DoesNotExist:
        error_message = "NIN verification service is not configured for this branch."
        api_cost = 0
    
    if request.method == 'POST' and not error_message:
        from .forms import NINVerificationForm
        form = NINVerificationForm(request.POST)
        if form.is_valid():
            search_type = form.cleaned_data['search_type']
            nin = form.cleaned_data.get('nin')
            phone = form.cleaned_data.get('phone')
            
            # Check API key first
            api_key = getattr(settings, 'CHECKMYNINBVN_API_KEY', None)
            if not api_key:
                error_message = "NIN verification API key not configured. Please contact admin."
            else:
                # Check API balance before processing
                balance_ok, api_balance = check_nin_api_balance(api_key, api_cost)
                if not balance_ok:
                    error_message = "Unable to verify API balance. Please try again."
                elif api_balance < float(api_cost):
                    error_message = f"Insufficient API balance. Please contact admin to top up. (API Balance: ₦{api_balance:,.2f})"
                else:
                    # Process merchant charge
                    success, charge_message, trx_ref = process_nin_verification_charge(merchant, request)
                    
                    if not success:
                        error_message = charge_message
                    else:
                        # Call CheckMyNINBVN API based on search type
                        try:
                            if search_type == 'nin':
                                api_url = 'https://checkmyninbvn.com.ng/api/nin-verification'
                                payload = {'nin': nin, 'consent': True}
                            else:  # phone
                                api_url = 'https://checkmyninbvn.com.ng/api/nin-phone'
                                payload = {'phone': phone, 'consent': True}
                            
                            response = requests.post(
                                api_url,
                                json=payload,
                                headers={
                                    'Content-Type': 'application/json',
                                    'x-api-key': api_key
                                },
                                timeout=30
                            )
                            result = response.json()
                            
                            if result.get('status') == 'success':
                                nin_data = result.get('data', {})
                                messages.success(request, f'NIN verified successfully. Charged: ₦{merchant_charge}')
                            else:
                                error_message = result.get('message', 'NIN verification failed')
                        except requests.exceptions.Timeout:
                            error_message = "Request timed out. Please try again."
                        except requests.exceptions.RequestException:
                            error_message = "Connection error. Please try again."
                        except Exception:
                            error_message = "An error occurred during verification."
    else:
        from .forms import NINVerificationForm
        form = NINVerificationForm()
    
    context = {
        'merchant': merchant,
        'form': form,
        'nin_data': nin_data,
        'error_message': error_message,
        'merchant_charge': merchant_charge,
        'float_balance': get_merchant_float_balance(merchant),
    }
    return render(request, 'merchant/portal/nin_verification.html', context)


# ==============================================================================
# NIN CONFIG (ADMIN)
# ==============================================================================

@login_required
@require_POST
def reverse_merchant_transaction(request, transaction_id):
    """Reverse a merchant transaction - debit where credited, credit where debited"""
    from transactions.models import Memtrans
    from .models import MerchantTransaction
    
    trx = get_object_or_404(MerchantTransaction, id=transaction_id)
    
    # Check if already reversed
    if trx.status == 'reversed':
        messages.error(request, 'This transaction has already been reversed.')
        return redirect('merchant:all_transactions')
    
    # Only completed transactions can be reversed
    if trx.status != 'completed':
        messages.error(request, 'Only completed transactions can be reversed.')
        return redirect('merchant:all_transactions')
    
    merchant = trx.merchant
    session_date = merchant.branch.session_date or timezone.now().date()
    reversal_ref = f"REV{trx.transaction_ref[:17]}"  # Keep within 20 chars
    
    try:
        with transaction.atomic():
            # Get original Memtrans entries for this transaction
            original_entries = list(Memtrans.all_objects.filter(trx_no=trx.transaction_ref))
            
            if original_entries:
                # Create reverse entries for each original entry
                for entry in original_entries:
                    # Swap type: D becomes C, C becomes D
                    reverse_type = 'C' if entry.type == 'D' else 'D'
                    # Swap amount sign
                    reverse_amount = -entry.amount
                    
                    Memtrans.all_objects.create(
                        branch=entry.branch,
                        cust_branch=entry.cust_branch,
                        customer=entry.customer,
                        gl_no=entry.gl_no,
                        ac_no=entry.ac_no,
                        amount=reverse_amount,
                        description=f'REVERSAL: {entry.description or trx.transaction_ref}',
                        error='A',
                        type=reverse_type,
                        account_type=entry.account_type,
                        ses_date=session_date,
                        app_date=session_date,
                        trx_no=reversal_ref,
                        code='REV',
                        trx_type=f'REV_{entry.trx_type or "TRX"}'
                    )
            else:
                # No original entries found - create basic reversal to merchant float
                Memtrans.all_objects.create(
                    branch=merchant.branch,
                    cust_branch=merchant.branch,
                    gl_no=merchant.float_gl_no,
                    ac_no=merchant.float_ac_no,
                    amount=trx.amount,
                    description=f'REVERSAL: {trx.transaction_ref}',
                    error='A',
                    type='C',
                    account_type='L',
                    ses_date=session_date,
                    app_date=session_date,
                    trx_no=reversal_ref,
                    code='REV',
                    trx_type='REVERSAL'
                )
            
            # Update transaction status
            trx.status = 'reversed'
            trx.response_message = f'Reversed by {request.user.username} on {timezone.now().strftime("%Y-%m-%d %H:%M")}'
            trx.save()
            
            # Log activity
            log_merchant_activity(
                merchant=merchant,
                activity_type='transaction',
                description=f'Transaction {trx.transaction_ref} (₦{trx.amount}) reversed by admin {request.user.username}',
                request=request,
                transaction=trx
            )
            
            messages.success(request, f'Transaction {trx.transaction_ref} has been reversed successfully.')
    
    except Exception as e:
        messages.error(request, f'Failed to reverse transaction: {str(e)}')
    
    return redirect('merchant:all_transactions')


@login_required
def nin_verification_config(request):
    """Configure NIN verification service settings"""
    from .models import NINVerificationConfig
    from .forms import NINVerificationConfigForm
    
    branch = request.user.branch
    config, created = NINVerificationConfig.objects.get_or_create(branch=branch)
    
    if request.method == 'POST':
        form = NINVerificationConfigForm(request.POST, instance=config, branch=branch)
        if form.is_valid():
            config = form.save()
            messages.success(request, 'NIN verification configuration updated successfully.')
            return redirect('merchant:nin_verification_config')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = NINVerificationConfigForm(instance=config, branch=branch)
    
    # Refresh config from database
    config.refresh_from_db()
    
    return render(request, 'merchant/admin/nin_verification_config.html', {
        'form': form,
        'config': config,
    })
