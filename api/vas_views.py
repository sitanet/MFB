# api/vas_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import logging

from .vas_services import VASService

logger = logging.getLogger(__name__)

# Initialize VAS service
vas_service = VASService()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detect_network(request):
    """Detect network for phone number"""
    try:
        phone_number = request.data.get('phone_number')
        
        if not phone_number:
            return Response({
                'success': False,
                'error': 'Phone number is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        result = vas_service.detect_network(phone_number)
        
        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Network detection API error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_airtime(request):
    """Purchase airtime"""
    try:
        phone_number = request.data.get('phone_number')
        amount = request.data.get('amount')
        
        if not phone_number or not amount:
            return Response({
                'success': False,
                'error': 'Phone number and amount are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(amount)
            if amount < 50 or amount > 500000:
                return Response({
                    'success': False,
                    'error': 'Amount must be between ₦50 and ₦500,000'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'error': 'Invalid amount format'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get customer ID from JWT token
        customer_id = getattr(request.user, 'customer_id', None)
        
        result = vas_service.purchase_airtime(
            phone_number=phone_number,
            amount=amount,
            customer_id=customer_id
        )
        
        response_status = status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST
        return Response(result, status=response_status)

    except Exception as e:
        logger.error(f"Airtime purchase API error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_data_plans(request):
    """Get data plans"""
    try:
        network = request.query_params.get('network')
        
        result = vas_service.get_data_plans(network=network)
        
        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Get data plans API error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'plans': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_data(request):
    """Purchase data plan"""
    try:
        phone_number = request.data.get('phone_number')
        plan_id = request.data.get('plan_id')
        network = request.data.get('network')
        
        if not phone_number or not plan_id:
            return Response({
                'success': False,
                'error': 'Phone number and plan ID are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get customer ID from JWT token
        customer_id = getattr(request.user, 'customer_id', None)
        
        result = vas_service.purchase_data(
            phone_number=phone_number,
            plan_id=plan_id,
            network=network,
            customer_id=customer_id
        )
        
        response_status = status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST
        return Response(result, status=response_status)

    except Exception as e:
        logger.error(f"Data purchase API error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transaction_history(request):
    """Get VAS transaction history"""
    try:
        # Get customer ID from JWT token
        customer_id = getattr(request.user, 'customer_id', None)
        transaction_type = request.query_params.get('type')
        
        # Pagination params
        try:
            page = int(request.query_params.get('page', 1))
            per_page = min(int(request.query_params.get('per_page', 20)), 100)  # Max 100 per page
        except (ValueError, TypeError):
            page = 1
            per_page = 20

        result = vas_service.get_transaction_history(
            customer_id=customer_id,
            transaction_type=transaction_type,
            page=page,
            per_page=per_page
        )
        
        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Get transaction history API error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'transactions': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transaction_status(request, transaction_id):
    """Get single transaction status"""
    try:
        from .models import VASTransaction
        
        # Get customer ID from JWT token
        customer_id = getattr(request.user, 'customer_id', None)
        
        # Find transaction
        transaction = VASTransaction.objects.filter(
            id=transaction_id,
            customer_id=customer_id if customer_id else None
        ).first()
        
        if not transaction:
            return Response({
                'success': False,
                'error': 'Transaction not found'
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'success': True,
            'transaction': {
                'id': str(transaction.id),
                'reference': transaction.transaction_reference,
                'type': transaction.transaction_type,
                'phone_number': transaction.phone_number,
                'network': transaction.network,
                'amount': float(transaction.amount),
                'charges': float(transaction.charges),
                'cashback': float(transaction.cashback_amount),
                'status': transaction.status,
                'data_bundle': transaction.data_bundle,
                'error_message': transaction.error_message,
                'created_at': transaction.created_at.isoformat(),
                'completed_at': transaction.completed_at.isoformat() if transaction.completed_at else None
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Get transaction status API error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bills_categories(request):
    """Get bills payment categories"""
    try:
        result = vas_service.get_bills_categories()
        
        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Get bills categories API error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'categories': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bills_billers(request, category_id):
    """Get billers for category"""
    try:
        from .models import BillsBiller
        
        billers = BillsBiller.objects.filter(
            category_id=category_id,
            is_active=True
        ).order_by('name')
        
        biller_list = []
        for biller in billers:
            biller_list.append({
                'id': biller.id,
                'name': biller.name,
                'code': biller.code,
                'description': biller.description,
                'logo_url': biller.logo_url,
                'minimum_amount': float(biller.minimum_amount),
                'maximum_amount': float(biller.maximum_amount),
            })

        return Response({
            'success': True,
            'billers': biller_list
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Get bills billers API error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'billers': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Coming Soon endpoints for bills payment
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_bill_payment(request):
    """Validate bill payment (Coming Soon)"""
    return Response({
        'success': False,
        'error': 'Bills payment validation coming soon',
        'coming_soon': True
    }, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_bill(request):
    """Pay bill (Coming Soon)"""
    return Response({
        'success': False,
        'error': 'Bills payment coming soon',
        'coming_soon': True
    }, status=status.HTTP_501_NOT_IMPLEMENTED)