# ninepsb/views.py
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .utils import create_virtual_account
from .services import WAASService


def test_virtual_account(request):
    try:
        result = create_virtual_account(
            name="Test Customer",
            amount=100.00,
            account_type="STATIC",  # or "DYNAMIC"
            amount_type="EXACT"
        )
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required(login_url='login')
@staff_member_required
def wallet_enquiry_view(request):
    """
    9PSB Wallet Enquiry - Fetch wallet details by account number.
    """
    wallet_data = None
    account_no = None
    error_message = None
    
    if request.method == 'POST':
        account_no = request.POST.get('account_no', '').strip()
        
        if not account_no:
            error_message = "Please enter a wallet account number"
        elif len(account_no) != 10:
            error_message = "Wallet account number must be 10 digits"
        else:
            try:
                waas = WAASService()
                result = waas.wallet_enquiry(account_no)
                wallet_data = result.get('data', result)
                messages.success(request, "Wallet enquiry successful")
            except Exception as e:
                error_message = str(e)
                messages.error(request, f"Wallet enquiry failed: {error_message}")
    
    context = {
        'wallet_data': wallet_data,
        'account_no': account_no,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/wallet_enquiry.html', context)


@login_required(login_url='login')
@staff_member_required
def wallet_status_view(request):
    """
    9PSB Wallet Status - Fetch wallet status by account number.
    """
    status_data = None
    account_no = None
    error_message = None
    
    if request.method == 'POST':
        account_no = request.POST.get('account_no', '').strip()
        
        if not account_no:
            error_message = "Please enter a wallet account number"
        else:
            try:
                waas = WAASService()
                result = waas.wallet_status(account_no)
                status_data = result.get('data', result)
                messages.success(request, "Wallet status fetched successfully")
            except Exception as e:
                error_message = str(e)
                messages.error(request, f"Failed to fetch wallet status: {error_message}")
    
    context = {
        'status_data': status_data,
        'account_no': account_no,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/wallet_status.html', context)


@login_required(login_url='login')
@staff_member_required
def change_wallet_status_view(request):
    """
    9PSB Change Wallet Status - Activate or Suspend a wallet.
    """
    result_data = None
    account_no = None
    new_status = None
    error_message = None
    
    if request.method == 'POST':
        account_no = request.POST.get('account_no', '').strip()
        new_status = request.POST.get('new_status', '').strip().upper()
        
        if not account_no:
            error_message = "Please enter a wallet account number"
        elif new_status not in ['ACTIVE', 'SUSPENDED']:
            error_message = "Status must be ACTIVE or SUSPENDED"
        else:
            try:
                waas = WAASService()
                result = waas.change_wallet_status(account_no, new_status)
                result_data = result.get('data', result)
                messages.success(request, f"Wallet status changed to {new_status}")
            except Exception as e:
                error_message = str(e)
                messages.error(request, f"Failed to change wallet status: {error_message}")
    
    context = {
        'result_data': result_data,
        'account_no': account_no,
        'new_status': new_status,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/change_wallet_status.html', context)


@login_required(login_url='login')
@staff_member_required  
def wallet_transactions_view(request):
    """
    9PSB Wallet Transaction History - Fetch transaction history for a wallet.
    """
    transactions = None
    account_no = None
    from_date = None
    to_date = None
    error_message = None
    
    if request.method == 'POST':
        account_no = request.POST.get('account_no', '').strip()
        from_date = request.POST.get('from_date', '')
        to_date = request.POST.get('to_date', '')
        num_items = request.POST.get('num_items', '50')
        
        if not account_no:
            error_message = "Please enter a wallet account number"
        elif not from_date or not to_date:
            error_message = "Please enter both from and to dates"
        else:
            try:
                waas = WAASService()
                result = waas.wallet_transactions(account_no, from_date, to_date, int(num_items))
                transactions = result.get('data', result)
                messages.success(request, "Transaction history fetched successfully")
            except Exception as e:
                error_message = str(e)
                messages.error(request, f"Failed to fetch transaction history: {error_message}")
    
    context = {
        'transactions': transactions,
        'account_no': account_no,
        'from_date': from_date,
        'to_date': to_date,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/wallet_transactions.html', context)


@login_required(login_url='login')
@staff_member_required
def get_banks_view(request):
    """
    9PSB Get Banks - Fetch list of all banks.
    """
    banks = []
    error_message = None
    
    try:
        waas = WAASService()
        result = waas.get_banks()
        # Handle different response formats
        banks_data = result.get('data', result)
        if isinstance(banks_data, dict):
            banks = banks_data.get('bankList', banks_data.get('banks', []))
        elif isinstance(banks_data, list):
            banks = banks_data
        else:
            banks = []
        
        if not isinstance(banks, list):
            banks = []
    except Exception as e:
        error_message = str(e)
        messages.error(request, f"Failed to fetch banks: {error_message}")
    
    context = {
        'banks': banks,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/get_banks.html', context)


@login_required(login_url='login')
@staff_member_required
def other_bank_enquiry_view(request):
    """
    9PSB Other Bank Enquiry - Verify account details of other bank's account.
    """
    account_data = None
    account_no = None
    bank_code = None
    error_message = None
    banks = []
    
    # Always fetch banks for the dropdown
    try:
        waas = WAASService()
        result = waas.get_banks()
        # Handle different response formats
        banks_data = result.get('data', result)
        if isinstance(banks_data, dict):
            banks = banks_data.get('bankList', banks_data.get('banks', []))
        elif isinstance(banks_data, list):
            banks = banks_data
        else:
            banks = []
        
        if not isinstance(banks, list):
            banks = []
    except Exception as e:
        messages.warning(request, f"Could not load banks list: {str(e)}")
        banks = []
    
    if request.method == 'POST':
        account_no = request.POST.get('account_no', '').strip()
        bank_code = request.POST.get('bank_code', '').strip()
        
        if not account_no:
            error_message = "Please enter an account number"
        elif not bank_code:
            error_message = "Please select a bank"
        else:
            try:
                waas = WAASService()
                result = waas.other_bank_enquiry(account_no, bank_code)
                account_data = result.get('data', result)
                messages.success(request, "Account enquiry successful")
            except Exception as e:
                error_message = str(e)
                messages.error(request, f"Account enquiry failed: {error_message}")
    
    context = {
        'account_data': account_data,
        'account_no': account_no,
        'bank_code': bank_code,
        'banks': banks,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/other_bank_enquiry.html', context)


# ==============================================================================
# 9PSB WEBHOOK HANDLERS
# ==============================================================================

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import base64
import logging

logger = logging.getLogger(__name__)


def verify_basic_auth(request):
    """Verify Basic Auth credentials for webhook."""
    from django.conf import settings
    
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Basic '):
        return False
    
    try:
        encoded_credentials = auth_header[6:]  # Remove 'Basic '
        decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
        username, password = decoded_credentials.split(':', 1)
        
        # Get expected credentials from settings
        expected_username = getattr(settings, 'NINEPSB_WEBHOOK_USERNAME', '')
        expected_password = getattr(settings, 'NINEPSB_WEBHOOK_PASSWORD', '')
        
        return username == expected_username and password == expected_password
    except Exception as e:
        logger.error(f"Basic auth verification failed: {e}")
        return False


@csrf_exempt
@require_POST
def psb_webhook_handler(request):
    """
    9PSB Webhook Handler - Receives notifications for transfers and account upgrades.
    
    Query params:
    - event=transfer : Inflow credit notification
    - event=account-upgrade : Account upgrade notification
    """
    from decimal import Decimal
    from django.utils import timezone
    from merchant.models import Merchant
    from transactions.models import Memtrans
    
    # Verify Basic Auth
    if not verify_basic_auth(request):
        logger.warning("Webhook received with invalid authentication")
        return JsonResponse({
            'success': False,
            'code': '401',
            'status': 'FAILED',
            'message': 'Unauthorized'
        }, status=401)
    
    event_type = request.GET.get('event', 'transfer')
    
    try:
        payload = json.loads(request.body)
        logger.info(f"9PSB Webhook received - Event: {event_type}, Payload: {payload}")
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        return JsonResponse({
            'success': False,
            'code': '400',
            'status': 'FAILED',
            'message': 'Invalid JSON'
        }, status=400)
    
    if event_type == 'transfer':
        return handle_transfer_webhook(payload)
    elif event_type == 'account-upgrade':
        return handle_account_upgrade_webhook(payload)
    else:
        logger.warning(f"Unknown webhook event type: {event_type}")
        return JsonResponse({
            'success': True,
            'code': '00',
            'status': 'SUCCESS',
            'message': 'Acknowledged'
        })


def handle_transfer_webhook(payload):
    """Handle inflow/transfer notification webhook."""
    from decimal import Decimal
    from django.utils import timezone
    from django.db import transaction as db_transaction
    from merchant.models import Merchant
    from transactions.models import Memtrans
    from .models import WebhookNotification
    from .services import WAASService
    
    try:
        # Extract data from payload (handle both short and long format)
        account_number = payload.get('accountnumber') or payload.get('accountNumber')
        amount = Decimal(str(payload.get('amount', '0')))
        sender_account = payload.get('sourceaccount') or payload.get('source_account')
        sender_name = payload.get('sendername') or payload.get('sender_name', '')
        sender_bank = payload.get('sourcebank') or payload.get('source_bank', '')
        narration = payload.get('narration', '')
        transaction_ref = payload.get('transactionref') or payload.get('orderref', '')
        session_id = payload.get('nipsessionid') or payload.get('externalreference', '')
        order_ref = payload.get('orderref', '')
        
        logger.info(f"Processing inflow: Account={account_number}, Amount={amount}, Ref={transaction_ref}, Session={session_id}")
        
        # Check for duplicate webhook notification
        existing_notification = WebhookNotification.objects.filter(
            session_id=session_id,
            account_number=account_number
        ).first()
        
        if existing_notification:
            if existing_notification.status == 'processed':
                logger.info(f"Webhook {session_id} already processed, acknowledging")
                return JsonResponse({
                    'success': True,
                    'code': '00',
                    'status': 'SUCCESS',
                    'message': 'Acknowledged'
                })
            # Update retry count
            existing_notification.retry_count += 1
            existing_notification.last_retry_at = timezone.now()
            existing_notification.save(update_fields=['retry_count', 'last_retry_at'])
            notification = existing_notification
        else:
            # Create new notification record
            notification = WebhookNotification.objects.create(
                event_type='transfer',
                session_id=session_id,
                transaction_ref=transaction_ref,
                order_ref=order_ref,
                account_number=account_number,
                amount=amount,
                sender_account=sender_account,
                sender_name=sender_name,
                sender_bank=sender_bank,
                narration=narration,
                raw_payload=payload,
                status='received'
            )
        
        # Find the merchant with this wallet account
        merchant = Merchant.all_objects.filter(psb_wallet_account=account_number).first()
        
        if not merchant:
            logger.warning(f"No merchant found for wallet account: {account_number}")
            notification.status = 'failed'
            notification.error_message = 'No merchant found for wallet account'
            notification.save()
            return JsonResponse({
                'success': True,
                'code': '00',
                'status': 'SUCCESS',
                'message': 'Acknowledged'
            })
        
        # Verify notification with 9PSB (recommended by documentation)
        try:
            waas = WAASService()
            verification = waas.notification_requery(session_id, account_number)
            notification.verified = True
            notification.verified_at = timezone.now()
            notification.verification_response = verification
            notification.save()
            logger.info(f"Notification {session_id} verified with 9PSB")
        except Exception as verify_error:
            logger.warning(f"Failed to verify notification {session_id}: {verify_error}")
            # Continue processing even if verification fails - we still got the webhook
        
        # Check if this transaction was already processed (duplicate check by reference)
        existing = Memtrans.all_objects.filter(
            reference=transaction_ref,
            branch=merchant.branch
        ).exists()
        
        if existing:
            logger.info(f"Transaction {transaction_ref} already processed")
            notification.status = 'duplicate'
            notification.save()
            return JsonResponse({
                'success': True,
                'code': '00',
                'status': 'SUCCESS',
                'message': 'Acknowledged'
            })
        
        notification.status = 'processing'
        notification.save()
        
        # Process inflow: Credit merchant account, Debit float account
        with db_transaction.atomic():
            # 1. CREDIT merchant's main FinanceFlex account (money received)
            if merchant.gl_no and merchant.ac_no:
                Memtrans.all_objects.create(
                    branch=merchant.branch,
                    gl_no=merchant.gl_no,
                    ac_no=merchant.ac_no,
                    trx_date=timezone.now().date(),
                    ses_date=timezone.now().date(),
                    app_date=timezone.now().date(),
                    amount=amount,  # Positive for credit
                    description=f"9PSB Inflow: {narration or 'Transfer from ' + sender_name}",
                    reference=transaction_ref,
                    trx_type='CR',
                    error='A',
                    posted_by=f"9PSB-WEBHOOK",
                )
                logger.info(f"Credited merchant {merchant.merchant_id} main account with {amount}")
            
            # 2. DEBIT float account (wallet balance increased)
            if merchant.float_gl_no and merchant.float_ac_no:
                Memtrans.all_objects.create(
                    branch=merchant.branch,
                    gl_no=merchant.float_gl_no,
                    ac_no=merchant.float_ac_no,
                    trx_date=timezone.now().date(),
                    ses_date=timezone.now().date(),
                    app_date=timezone.now().date(),
                    amount=-amount,  # Negative for debit
                    description=f"9PSB Inflow: {narration or 'Transfer from ' + sender_name}",
                    reference=transaction_ref + "-FLT",
                    trx_type='DR',
                    error='A',
                    posted_by=f"9PSB-WEBHOOK",
                )
                logger.info(f"Debited merchant {merchant.merchant_id} float account with {amount} (wallet inflow)")
        
        # Mark notification as processed
        notification.status = 'processed'
        notification.processed_at = timezone.now()
        notification.save()
        
        return JsonResponse({
            'success': True,
            'code': '00',
            'status': 'SUCCESS',
            'message': 'Acknowledged',
            'transactionRef': transaction_ref
        })
        
    except Exception as e:
        logger.error(f"Error processing transfer webhook: {e}", exc_info=True)
        # Try to update notification status if it exists
        try:
            if 'notification' in locals() and notification:
                notification.status = 'failed'
                notification.error_message = str(e)
                notification.save()
        except:
            pass
        # Still acknowledge to prevent retries
        return JsonResponse({
            'success': True,
            'code': '00',
            'status': 'SUCCESS',
            'message': 'Acknowledged'
        })


def handle_account_upgrade_webhook(payload):
    """Handle account upgrade notification webhook."""
    from merchant.models import Merchant
    
    try:
        account_number = payload.get('accountNumber')
        status = payload.get('status', '').lower()
        message = payload.get('message', '')
        
        logger.info(f"Account upgrade notification: Account={account_number}, Status={status}")
        
        # Find the merchant
        merchant = Merchant.all_objects.filter(psb_wallet_account=account_number).first()
        
        if merchant:
            if status == 'approved':
                # Update wallet tier (assume tier 2 or 3)
                merchant.psb_wallet_tier = '2'  # Or determine from message
                merchant.save(update_fields=['psb_wallet_tier'])
                logger.info(f"Merchant {merchant.merchant_id} wallet upgraded")
        
        return JsonResponse({
            'success': True,
            'code': '00',
            'status': 'SUCCESS',
            'message': 'Acknowledged'
        })
        
    except Exception as e:
        logger.error(f"Error processing account upgrade webhook: {e}", exc_info=True)
        return JsonResponse({
            'success': True,
            'code': '00',
            'status': 'SUCCESS',
            'message': 'Acknowledged'
        })

