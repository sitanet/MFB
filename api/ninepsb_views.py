"""
9PSB Views - Django REST Framework views for 9PSB integration
This module provides the API endpoints that Flutter app calls for 9PSB operations
"""

import logging
from decimal import Decimal
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.ninepsb_service import ninepsb_service

logger = logging.getLogger(__name__)


class VerifyAccountView(APIView):
    """
    Verify bank account using 9PSB account enquiry
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            account_number = request.data.get('account_number')
            bank_code = request.data.get('bank_code')
            
            if not account_number or not bank_code:
                return Response({
                    'success': False,
                    'error': 'account_number and bank_code are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"[VERIFY_ACCOUNT] Verifying {account_number} at bank {bank_code}")
            
            # Call 9PSB service
            result = ninepsb_service.account_enquiry(account_number, bank_code)
            
            logger.info(f"[VERIFY_ACCOUNT] 9PSB response: {result}")
            
            if result.get('success'):
                account_info = result.get('account', {})
                account_name = account_info.get('name', 'Unknown Account')
                
                logger.info(f"[VERIFY_ACCOUNT] Raw account_info from 9PSB: {account_info}")
                logger.info(f"[VERIFY_ACCOUNT] Retrieved account name: '{account_name}'")
                logger.info(f"[VERIFY_ACCOUNT] Account name type: {type(account_name)}")
                logger.info(f"[VERIFY_ACCOUNT] Account name length: {len(account_name) if account_name else 0}")
                
                # Ensure account name is not None or empty
                if not account_name or account_name.strip() == '' or account_name == 'Unknown Account':
                    logger.warning(f"[VERIFY_ACCOUNT] Account name is empty/unknown, trying alternative fields")
                    # Try different possible field names
                    account_name = (account_info.get('accountName') or 
                                  account_info.get('accountname') or
                                  account_info.get('customer_name') or
                                  account_info.get('Name') or
                                  'Account Name Not Available')
                    logger.info(f"[VERIFY_ACCOUNT] Alternative account name: '{account_name}'")
                
                response_data = {
                    'success': True,
                    'account': {
                        'number': account_info.get('number', account_number),
                        'bank': account_info.get('bank', bank_code), 
                        'name': account_name,
                        'bvn': account_info.get('bvn', ''),
                        'senderaccountnumber': account_info.get('senderaccountnumber'),
                        'sendername': account_info.get('sendername'),
                        'kyc': account_info.get('kyc', '0')
                    },
                    'code': result.get('code'),
                    'message': result.get('message', 'Account verification successful'),
                    # Add debug information
                    'debug': {
                        'raw_account_info': account_info,
                        'extracted_name': account_name,
                        'response_structure_valid': True
                    }
                }
                
                logger.info(f"[VERIFY_ACCOUNT] Final response structure:")
                logger.info(f"  success: {response_data['success']}")
                logger.info(f"  account.name: '{response_data['account']['name']}'")
                logger.info(f"  account.number: '{response_data['account']['number']}'")
                logger.info(f"  account.bank: '{response_data['account']['bank']}'")
                
                return Response(response_data)
            else:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Account verification failed'),
                    'code': result.get('code')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"[VERIFY_ACCOUNT] Error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': f'Account verification failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TransferView(APIView):
    """
    Fund transfer using 9PSB
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Get customer from authenticated user
            customer = getattr(request.user, 'customer', None)
            if not customer:
                return Response({
                    'success': False,
                    'error': 'Customer profile not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Extract transfer parameters (support both formats)
            data = request.data
            sender_account_number = data.get('sender_account_number')
            dest_account_number = data.get('dest_account_number')
            dest_account_name = data.get('dest_account_name', 'Unknown Account')
            bank_code = data.get('bank_code')
            amount = data.get('amount')
            narration = data.get('narration', 'Transfer')
            reference = data.get('reference')
            
            # Validate required fields
            if not all([sender_account_number, dest_account_number, bank_code, amount]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: sender_account_number, dest_account_number, bank_code, amount'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Convert amount to Decimal
            try:
                amount = Decimal(str(amount))
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except (ValueError, TypeError) as e:
                return Response({
                    'success': False,
                    'error': f'Invalid amount: {amount}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate reference if not provided
            if not reference:
                reference = f"FF{int(timezone.now().timestamp() * 1000)}"
            
            # Prepare sender name
            sender_name = f"{customer.first_name} {customer.last_name}".strip()
            
            logger.info(f"[TRANSFER] Processing transfer: {sender_account_number} -> {dest_account_number}, Amount: {amount}")
            
            # Log the parsed fields for debugging
            logger.debug(f"[DEBUG] Parsed fields:")
            logger.debug(f"  sender_account_number: '{sender_account_number}'")
            logger.debug(f"  dest_account_number: '{dest_account_number}'")
            logger.debug(f"  bank_code: '{bank_code}'")
            logger.debug(f"  amount: {amount}")
            
            # Log the exact parameters being sent to 9PSB
            transfer_params = {
                'reference': reference,
                'amount': amount,
                'currency': 'NGN',
                'description': narration,
                'country': 'NGA',
                'recipient_account': dest_account_number,
                'recipient_bank': bank_code,
                'recipient_name': dest_account_name,
                'sender_account': sender_account_number,
                'sender_name': sender_name
            }
            logger.debug(f"[DEBUG] Calling fund_transfer with exact parameters: {transfer_params}")
            
            # Call 9PSB fund transfer
            result = ninepsb_service.fund_transfer(**transfer_params)
            
            logger.debug(f"[DEBUG] 9PSB Transfer response: {result}")
            
            if result.get('success'):
                transaction_info = result.get('transaction', {})
                return Response({
                    'success': True,
                    'message': result.get('message', 'Transfer successful'),
                    'reference': reference,
                    'transaction': transaction_info,
                    'code': result.get('code')
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Transfer failed'),
                    'code': result.get('code'),
                    'message': result.get('message')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"[TRANSFER] Error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': f'Transfer failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TransferStatusView(APIView):
    """
    Check transfer status using 9PSB
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            reference = request.query_params.get('reference')
            
            if not reference:
                return Response({
                    'success': False,
                    'error': 'reference parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"[TRANSFER_STATUS] Checking status for reference: {reference}")
            
            # Call 9PSB transfer status query
            result = ninepsb_service.transfer_status_query(reference)
            
            if result.get('success'):
                return Response({
                    'success': True,
                    'transaction': result.get('transaction'),
                    'order': result.get('order'),
                    'customer': result.get('customer'),
                    'code': result.get('code'),
                    'message': result.get('message')
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Status query failed'),
                    'code': result.get('code')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"[TRANSFER_STATUS] Error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': f'Status query failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BankListView(APIView):
    """
    Get list of available banks from 9PSB
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            logger.info("[BANK_LIST] Fetching bank list from 9PSB")
            
            # Call 9PSB bank list
            result = ninepsb_service.get_bank_list()
            
            if result.get('success'):
                return Response({
                    'success': True,
                    'banks': result.get('banks', []),
                    'count': result.get('count', 0),
                    'code': result.get('code'),
                    'message': result.get('message')
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Failed to fetch bank list'),
                    'code': result.get('code')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"[BANK_LIST] Error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': f'Bank list fetch failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HealthCheckView(APIView):
    """
    Health check for 9PSB service
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            # Test authentication
            auth_result = ninepsb_service.authenticate()
            
            return Response({
                'success': auth_result.get('success', False),
                'service': '9PSB',
                'timestamp': timezone.now().isoformat(),
                'message': auth_result.get('message', 'Authentication test'),
                'error': auth_result.get('error') if not auth_result.get('success') else None
            })
            
        except Exception as e:
            logger.error(f"[HEALTH_CHECK] Error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'service': '9PSB',
                'timestamp': timezone.now().isoformat(),
                'error': f'Health check failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Function-based view alternatives for compatibility
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_account(request):
    """Function-based view for account verification"""
    view = VerifyAccountView()
    return view.post(request)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def transfer(request):
    """Function-based view for fund transfer"""
    view = TransferView()
    return view.post(request)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def transfer_status(request):
    """Function-based view for transfer status"""
    view = TransferStatusView()
    return view.get(request)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def banks(request):
    """Function-based view for bank list"""
    view = BankListView()
    return view.get(request)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def health(request):
    """Function-based view for health check"""
    view = HealthCheckView()
    return view.get(request)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])  
def debug_account_verification(request):
    """Debug endpoint to test account verification with detailed logging"""
    try:
        account_number = request.data.get('account_number', '1100000024')  # Default test account
        bank_code = request.data.get('bank_code', '120001')  # Default test bank
        
        logger.info(f"[DEBUG_VERIFY] Testing with account: {account_number}, bank: {bank_code}")
        
        # Test the raw 9PSB service call
        result = ninepsb_service.account_enquiry(account_number, bank_code)
        
        response_data = {
            'debug_info': {
                'test_account': account_number,
                'test_bank': bank_code,
                'raw_9psb_response': result,
                'account_info_extracted': result.get('account', {}) if result.get('success') else None,
                'account_name_extracted': result.get('account', {}).get('name') if result.get('success') else None,
                'expected_flutter_structure': {
                    'success': True,
                    'account': {
                        'name': 'EXPECTED_NAME_HERE',
                        'number': account_number,
                        'bank': bank_code
                    }
                }
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"[DEBUG_VERIFY] Error: {str(e)}", exc_info=True)
        return Response({
            'error': str(e),
            'debug_info': 'Account verification debug failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)