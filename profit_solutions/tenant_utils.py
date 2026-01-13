"""
Tenant Utility Functions

Helper functions for working with multi-tenant data.
"""

from functools import wraps
from django.core.exceptions import PermissionDenied


def get_tenant_from_request(request):
    """
    Extract tenant information from request.
    Returns tuple of (branch_id, company_id)
    """
    branch_id = getattr(request, 'tenant_branch_id', None)
    company_id = getattr(request, 'tenant_company_id', None)
    
    if not branch_id and request.user.is_authenticated:
        branch_id = getattr(request.user, 'branch_id', None)
        if branch_id:
            branch_id = str(branch_id)
    
    return branch_id, company_id


def get_user_branch(user):
    """Get the branch object for a user from vendor database"""
    if not user or not user.is_authenticated:
        return None
    
    branch_id = getattr(user, 'branch_id', None)
    if not branch_id:
        return None
    
    try:
        from company.models import Branch
        return Branch.objects.get(id=branch_id)
    except Exception:
        return None


def get_user_company(user):
    """Get the company object for a user from vendor database"""
    branch = get_user_branch(user)
    if branch:
        return branch.company
    return None


def get_company_branches(company_id):
    """Get all branches for a company"""
    try:
        from company.models import Branch
        return Branch.objects.filter(company_id=company_id)
    except Exception:
        return []


def get_tenant_branch_ids(user):
    """
    Get list of branch IDs the user has access to.
    - Regular users: only their own branch
    - Company admins: all branches in their company
    - Super admins: all branches
    """
    if not user or not user.is_authenticated:
        return []
    
    # Super admin sees all
    if getattr(user, 'is_superadmin', False):
        try:
            from company.models import Branch
            return [str(b.id) for b in Branch.objects.all()]
        except Exception:
            return []
    
    branch_id = getattr(user, 'branch_id', None)
    if not branch_id:
        return []
    
    # Check if user is a company-level admin (role 1 or 2)
    user_role = getattr(user, 'role', None)
    if user_role in [1, 2]:  # System Admin or General Manager
        try:
            from company.models import Branch
            branch = Branch.objects.get(id=branch_id)
            if branch.company:
                company_branches = Branch.objects.filter(
                    company=branch.company
                )
                return [str(b.id) for b in company_branches]
        except Exception:
            pass
    
    # Regular user - only their branch
    return [str(branch_id)]


def tenant_required(view_func):
    """
    Decorator that ensures a tenant context exists.
    Use on views that require tenant isolation.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from profit_solutions.tenant_middleware import get_current_tenant
        
        if not get_current_tenant():
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('login')
            
            # User is authenticated but has no branch
            branch_id = getattr(request.user, 'branch_id', None)
            if not branch_id:
                raise PermissionDenied("User is not assigned to any branch.")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def validate_tenant_access(user, obj):
    """
    Validate that a user has access to a specific object based on tenant.
    Returns True if access is allowed, False otherwise.
    """
    if not user or not user.is_authenticated:
        return False
    
    # Super admin has access to everything
    if getattr(user, 'is_superadmin', False):
        return True
    
    user_branch_ids = get_tenant_branch_ids(user)
    
    # Get object's branch_id
    obj_branch_id = None
    if hasattr(obj, 'branch_id'):
        obj_branch_id = str(obj.branch_id) if obj.branch_id else None
    elif hasattr(obj, 'branch'):
        obj_branch_id = str(obj.branch_id) if obj.branch_id else None
    
    if not obj_branch_id:
        return True  # No branch restriction on object
    
    return obj_branch_id in user_branch_ids


def filter_queryset_by_tenant(queryset, user):
    """
    Filter a queryset by the user's tenant access.
    Use this in views/serializers when you need explicit filtering.
    """
    if not user or not user.is_authenticated:
        return queryset.none()
    
    # Super admin sees all
    if getattr(user, 'is_superadmin', False):
        return queryset
    
    branch_ids = get_tenant_branch_ids(user)
    
    if not branch_ids:
        return queryset.none()
    
    model = queryset.model
    
    # Determine the correct filter field
    if hasattr(model, 'branch'):
        return queryset.filter(branch_id__in=branch_ids)
    elif hasattr(model, 'branch_id'):
        return queryset.filter(branch_id__in=branch_ids)
    elif hasattr(model, 'cust_branch'):
        return queryset.filter(cust_branch_id__in=branch_ids)
    
    return queryset


class TenantMixin:
    """
    Mixin for class-based views that require tenant awareness.
    Automatically filters querysets by tenant.
    """
    
    def get_queryset(self):
        """Filter queryset by tenant"""
        qs = super().get_queryset()
        return filter_queryset_by_tenant(qs, self.request.user)
    
    def get_tenant_branch_id(self):
        """Get the current tenant branch ID"""
        return getattr(self.request, 'tenant_branch_id', None)
    
    def get_tenant_company_id(self):
        """Get the current tenant company ID"""
        return getattr(self.request, 'tenant_company_id', None)
