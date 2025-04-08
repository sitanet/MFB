from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog
import json

User = get_user_model()

class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.path.startswith('/admin/') or request.path.startswith('/static/') or request.path.startswith('/media/'):
            return response
            
        user = None
        if request.user.is_authenticated:
            user = request.user
            
        action = 'ACCESS'
        if request.method == 'GET':
            action = 'VIEW'
        elif request.method == 'POST':
            action = 'CREATE'
        elif request.method in ['PUT', 'PATCH']:
            action = 'UPDATE'
        elif request.method == 'DELETE':
            action = 'DELETE'
            
        AuditLog.objects.create(
            user=user,
            action=action,
            ip_address=self.get_client_ip(request),
            message=f"{request.method} {request.path}"
        )
        
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip