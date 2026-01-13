import time
import json
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import resolve
from django.http import JsonResponse
from audit_trail.models import AuditTrail, AuditAction, AuditCategory, AuditConfiguration
from audit_trail.utils import get_client_ip, should_track_request, determine_category

User = get_user_model()

class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to automatically track user activities for audit trail
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Start timing the request"""
        request._audit_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Log the request after processing"""
        
        # Skip if audit configuration doesn't exist or tracking is disabled
        try:
            config = AuditConfiguration.objects.first()
            if not config:
                return response
        except:
            return response
        
        # Skip if we shouldn't track this request
        if not should_track_request(request):
            return response
        
        # Calculate request duration
        duration_ms = None
        if hasattr(request, '_audit_start_time'):
            duration_ms = int((time.time() - request._audit_start_time) * 1000)
        
        # Get request details
        user = request.user if request.user.is_authenticated else None
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        session_key = request.session.session_key
        
        # Get branch_id from user
        branch_id = None
        if user and hasattr(user, 'branch_id'):
            branch_id = user.branch_id
        
        # Determine action and category
        action = self._determine_action(request, response)
        category = determine_category(request)
        
        # Create description
        description = self._create_description(request, response, action)
        
        # Determine success status
        success = 200 <= response.status_code < 400
        error_message = '' if success else f"HTTP {response.status_code}"
        
        # Create audit trail entry
        try:
            AuditTrail.objects.create(
                user=user,
                session_key=session_key,
                branch_id=branch_id,
                action=action,
                category=category,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request.method,
                request_path=request.path,
                success=success,
                error_message=error_message,
                duration_ms=duration_ms,
                compliance_level=self._determine_compliance_level(request, action, category)
            )
        except Exception as e:
            # Fail silently to avoid breaking the application
            print(f"Audit logging error: {e}")
        
        return response
    
    def _determine_action(self, request, response):
        """Determine the audit action based on request method and URL"""
        
        method = request.method.upper()
        path = request.path.lower()
        
        # Authentication actions
        if 'login' in path:
            return AuditAction.LOGIN
        elif 'logout' in path:
            return AuditAction.LOGOUT
        
        # CRUD actions
        if method == 'POST':
            if 'create' in path or 'add' in path:
                return AuditAction.CREATE
            elif 'transaction' in path:
                return AuditAction.TRANSACTION
            elif 'approve' in path:
                return AuditAction.APPROVE
            elif 'reject' in path:
                return AuditAction.REJECT
            else:
                return AuditAction.CREATE
        
        elif method == 'PUT' or method == 'PATCH':
            return AuditAction.UPDATE
        
        elif method == 'DELETE':
            return AuditAction.DELETE
        
        elif method == 'GET':
            if 'export' in path or 'download' in path:
                return AuditAction.EXPORT
            elif 'report' in path:
                return AuditAction.VIEW
            else:
                return AuditAction.VIEW
        
        return AuditAction.VIEW
    
    def _create_description(self, request, response, action):
        """Create a human-readable description of the action"""
        
        path = request.path
        method = request.method
        
        # Extract meaningful parts from URL
        url_resolver = resolve(path)
        view_name = url_resolver.view_name or 'Unknown View'
        
        # Create base description
        if action == AuditAction.LOGIN:
            return "User login attempt"
        elif action == AuditAction.LOGOUT:
            return "User logout"
        elif action == AuditAction.CREATE:
            return f"Create operation - {view_name}"
        elif action == AuditAction.UPDATE:
            return f"Update operation - {view_name}"
        elif action == AuditAction.DELETE:
            return f"Delete operation - {view_name}"
        elif action == AuditAction.TRANSACTION:
            return f"Transaction operation - {view_name}"
        elif action == AuditAction.VIEW:
            if 'report' in path:
                return f"Viewed report - {view_name}"
            else:
                return f"Accessed - {view_name}"
        elif action == AuditAction.EXPORT:
            return f"Export operation - {view_name}"
        
        return f"{method} {view_name}"
    
    def _determine_compliance_level(self, request, action, category):
        """Determine compliance level based on action and category"""
        
        # Critical compliance actions
        if action in [AuditAction.DELETE, AuditAction.APPROVE, AuditAction.REJECT]:
            return 'CRITICAL'
        
        # High compliance categories
        if category in [AuditCategory.TRANSACTION, AuditCategory.LOAN, AuditCategory.CBN_RETURNS]:
            return 'HIGH'
        
        # Medium compliance actions
        if action in [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.TRANSACTION]:
            return 'MEDIUM'
        
        # Authentication failures
        if category == AuditCategory.AUTHENTICATION and 'login' in request.path:
            return 'HIGH'
        
        return 'LOW'