# adverts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django.shortcuts import get_object_or_404
from .models import AdvertThumbnail
from .serializers import AdvertThumbnailSerializer

class AdvertListAPIView(APIView):
    """API endpoint to get adverts for mobile app."""
    # TEMPORARILY REMOVE AUTHENTICATION FOR DEBUGGING
    # authentication_classes = [TokenAuthentication, SessionAuthentication]
    # permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get list of adverts with optional limit."""
        try:
            # Get query parameters
            limit = int(request.GET.get('limit', 10))
            
            # Get all adverts, newest first
            adverts = AdvertThumbnail.objects.all().order_by('-uploaded_at')
            
            # Apply limit if specified
            if limit > 0:
                adverts = adverts[:limit]
            
            # Serialize adverts
            serializer = AdvertThumbnailSerializer(adverts, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'data': serializer.data,
                'count': len(serializer.data)
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdvertViewAPIView(APIView):
    """API endpoint to track advert views."""
    # TEMPORARILY REMOVE AUTHENTICATION FOR DEBUGGING
    # authentication_classes = [TokenAuthentication, SessionAuthentication]
    # permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        """Track an advert view event."""
        try:
            advert = get_object_or_404(AdvertThumbnail, pk=pk)
            
            # You can add view tracking logic here if needed
            # For now, just acknowledge the view
            
            return Response({
                'success': True,
                'message': 'View tracked successfully',
                'advert_id': advert.id
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)