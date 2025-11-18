import json
import hmac
import hashlib
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from transactions.models import Memtrans

# Import fee models
try:
    from api.models.global_transfer_fees import GlobalTransferFeeTransaction
except ImportError:
    GlobalTransferFeeTransaction = None

logger = logging.getLogger(__name__)

# Get webhook secret from settings
NINEPSB_WEBHOOK_SECRET = getattr(settings, 'NINEPSB_WEBHOOK_SECRET', 'your-webhook-secret-key')

@csrf_exempt
@require_POST
def ninepsb_webhook_handler(request):
    """
    Handle incoming webhooks from 9PSB API
    
    POST /api/v1/webhooks/9psb/transaction-status/
    """
    
    try:
        print("=== 9PSB WEBHOOK RECEIVED ===")
        print(f"Headers: {dict(request.headers)}")
        print(f"Body: {request.body.decode('utf-8')}")
        
        # Parse webhook payload
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON payload'
            }, status=400)
        
        # Validate webhook signature (security)
        signature = request.headers.get('X-9PSB-Signature') or payload.get('signature')
        if not validate_webhook_signature(request.body, signature):
            logger.warning("Invalid webhook signature - potential security breach")
            return JsonResponse({
                'success': False,
                'error': 'Invalid signature'
            }, status=401)
        
        # Extract webhook data
        event_type = payload.get('event_type')
        transaction_reference = payload.get('transaction_reference')
        external_reference = payload.get('external_reference')
        status = payload.get('status')
        status_code = payload.get('status_code')
        message = payload.get('message', '')
        
        # Validate required fields
        required_fields = {
            'event_type': event_type,
            'transaction_reference': transaction_reference,
            'external_reference': external_reference,
            'status': status,
            'status_code': status_code
        }
        
        missing_fields = [k for k, v in required_fields.items() if not v]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        print(f"[WEBHOOK] Processing {event_type} for transaction {external_reference}")
        print(f"[WEBHOOK] Status: {status} ({status_code}) - {message}")
        
        # Process the webhook
        result = process_transaction_webhook(
            transaction_reference, external_reference, status, status_code, message, payload
        )
        
        if result['success']:
            print(f"✅ Webhook processed successfully: {result['message']}")
            return JsonResponse({
                'success': True,
                'message': 'Webhook processed successfully',
                'transaction_reference': external_reference,
                'status': status
            }, status=200)
        else:
            print(f"❌ Webhook processing failed: {result['error']}")
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=400)
    
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


def validate_webhook_signature(payload_body, received_signature):
    """Validate webhook signature"""
    if not received_signature:
        return True  # Skip validation for testing
    
    try:
        expected_signature = hmac.new(
            NINEPSB_WEBHOOK_SECRET.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(
            f"sha256={expected_signature}",
            received_signature
        )
    except Exception as e:
        logger.error(f"Signature validation error: {e}")
        return False


def process_transaction_webhook(transaction_reference, external_reference, 
                              status, status_code, message, payload):
    """Process webhook and update Memtrans records"""
    
    try:
        with transaction.atomic():
            # Find Memtrans entries
            memtrans_entries = Memtrans.objects.filter(trx_no=external_reference)
            
            if not memtrans_entries.exists():
                return {
                    'success': False,
                    'error': f'Transaction not found: {external_reference}'
                }
            
            print(f"[WEBHOOK] Found {memtrans_entries.count()} Memtrans entries for {external_reference}")
            
            # Process based on status
            if status.lower() == 'successful' and status_code == '00':
                return handle_successful_transaction(memtrans_entries, transaction_reference)
                
            elif status.lower() == 'failed' or status_code == '99':
                return handle_failed_transaction(memtrans_entries, transaction_reference, message)
                
            elif status.lower() == 'pending' or status_code == '09':
                return handle_pending_transaction(memtrans_entries, transaction_reference)
                
            else:
                return {
                    'success': False,
                    'error': f'Unknown status: {status} ({status_code})'
                }
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Processing error: {str(e)}'
        }


def handle_successful_transaction(memtrans_entries, ninepsb_ref):
    """Handle successful transaction"""
    
    print(f"✅ Processing SUCCESSFUL transaction: {ninepsb_ref}")
    
    updated_count = memtrans_entries.update(
        error='S',
        description=memtrans_entries.first().description + f" [9PSB: {ninepsb_ref}]"
    )
    
    print(f"✅ Updated {updated_count} Memtrans entries with success status")
    
    return {
        'success': True,
        'message': f'Transaction {ninepsb_ref} marked as successful',
        'updated_entries': updated_count
    }


def handle_failed_transaction(memtrans_entries, ninepsb_ref, error_message):
    """Handle failed transaction - create reversals"""
    
    print(f"❌ Processing FAILED transaction: {ninepsb_ref}")
    print(f"❌ Error: {error_message}")
    
    reversal_count = 0
    for entry in memtrans_entries:
        # Create reversal entry
        reversal_entry = Memtrans.objects.create(
            branch=entry.branch,
            cust_branch=entry.cust_branch,
            customer=entry.customer,
            gl_no=entry.gl_no,
            ac_no=entry.ac_no,
            trx_no=f"REV{entry.trx_no}",
            ses_date=timezone.now().date(),
            app_date=timezone.now().date(),
            sys_date=timezone.now(),
            amount=-entry.amount,  # Opposite amount
            description=f"REVERSAL: {entry.description} [9PSB FAILED: {ninepsb_ref}]",
            error='R',
            type='T',
            account_type=entry.account_type,
            user=entry.user,
            trx_type=f"REVERSAL_{entry.trx_type}",
        )
        reversal_count += 1
        print(f"🔄 Created reversal entry: {reversal_entry.trx_no}")
    
    # Mark original as failed
    memtrans_entries.update(
        error='F',
        description=memtrans_entries.first().description + f" [9PSB FAILED: {ninepsb_ref}]"
    )
    
    return {
        'success': True,
        'message': f'Transaction {ninepsb_ref} failed and reversed',
        'reversal_entries': reversal_count
    }


def handle_pending_transaction(memtrans_entries, ninepsb_ref):
    """Handle pending transaction"""
    
    print(f"⏳ Processing PENDING transaction: {ninepsb_ref}")
    
    updated_count = memtrans_entries.update(
        error='P',
        description=memtrans_entries.first().description + f" [9PSB PENDING: {ninepsb_ref}]"
    )
    
    return {
        'success': True,
        'message': f'Transaction {ninepsb_ref} marked as pending',
        'updated_entries': updated_count
    }


@csrf_exempt
def ninepsb_webhook_health(request):
    """Health check endpoint"""
    return JsonResponse({
        'success': True,
        'message': '9PSB webhook endpoint is healthy',
        'timestamp': timezone.now().isoformat()
    }, status=200)