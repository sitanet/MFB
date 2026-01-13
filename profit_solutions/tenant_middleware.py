"""
Multi-Tenant Middleware

This middleware automatically sets the current tenant (Branch/Company) 
based on the logged-in user. All tenant-aware querysets will automatically
filter by this tenant.
"""

import threading
from django.utils.deprecation import MiddlewareMixin

# Thread-local storage for tenant context
_tenant_context = threading.local()


def get_current_tenant():
    """Get the current tenant (branch_id) from thread-local storage"""
    return getattr(_tenant_context, 'branch_id', None)


def get_current_company():
    """Get the current company_id from thread-local storage"""
    return getattr(_tenant_context, 'company_id', None)


def get_current_user():
    """Get the current user from thread-local storage"""
    return getattr(_tenant_context, 'user', None)


def set_current_tenant(branch_id, company_id=None, user=None):
    """Manually set tenant context (useful for management commands, celery tasks)"""
    _tenant_context.branch_id = branch_id
    _tenant_context.company_id = company_id
    _tenant_context.user = user


def clear_tenant_context():
    """Clear the tenant context"""
    _tenant_context.branch_id = None
    _tenant_context.company_id = None
    _tenant_context.user = None


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware that sets the current tenant based on the authenticated user.
    
    The tenant is determined by the user's branch assignment. All subsequent
    database queries using TenantManager will automatically filter by this tenant.
    """
    
    def process_request(self, request):
        """Set tenant context at the start of each request"""
        clear_tenant_context()
        
        if request.user.is_authenticated:
            # Get branch_id from user (try both field names for compatibility)
            branch_id = getattr(request.user, 'branch_id', None) or getattr(request.user, 'branch', None)
            
            if branch_id:
                _tenant_context.branch_id = str(branch_id)
                _tenant_context.user = request.user
                
                # Try to get company_id from branch
                try:
                    from company.models import Branch
                    branch = Branch.objects.get(id=branch_id)
                    if branch.company:
                        _tenant_context.company_id = str(branch.company.id)
                except Exception:
                    pass
                
                # Store in request for easy access in views
                request.tenant_branch_id = _tenant_context.branch_id
                request.tenant_company_id = _tenant_context.company_id
    
    def process_response(self, request, response):
        """Clear tenant context at the end of each request"""
        clear_tenant_context()
        return response
    
    def process_exception(self, request, exception):
        """Clear tenant context on exception"""
        clear_tenant_context()
        return None


class TenantContextManager:
    """
    Context manager for temporarily setting tenant context.
    Useful for background tasks, management commands, etc.
    
    Usage:
        with TenantContextManager(branch_id='123', company_id='456'):
            # All queries here will be filtered by this tenant
            customers = Customer.objects.all()
    """
    
    def __init__(self, branch_id, company_id=None, user=None):
        self.branch_id = branch_id
        self.company_id = company_id
        self.user = user
        self.previous_branch_id = None
        self.previous_company_id = None
        self.previous_user = None
    
    def __enter__(self):
        self.previous_branch_id = get_current_tenant()
        self.previous_company_id = get_current_company()
        self.previous_user = get_current_user()
        set_current_tenant(self.branch_id, self.company_id, self.user)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        set_current_tenant(
            self.previous_branch_id, 
            self.previous_company_id, 
            self.previous_user
        )
        return False
