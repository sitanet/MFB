"""
Tenant View Decorators and Mixins

Decorators and mixins for tenant-aware views.
"""

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def tenant_required(view_func):
    """
    Decorator that ensures user is authenticated and has a valid tenant (branch).
    
    Usage:
        @login_required
        @tenant_required
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        branch_id = getattr(request.user, 'branch_id', None)
        if not branch_id:
            messages.error(request, "You are not assigned to any branch. Please contact administrator.")
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def validate_object_tenant(view_func):
    """
    Decorator that validates the object being accessed belongs to user's tenant.
    
    Use on detail/edit/delete views. Expects 'pk' or 'id' in kwargs.
    
    Usage:
        @login_required
        @validate_object_tenant
        def customer_detail(request, pk):
            customer = Customer.objects.get(pk=pk)  # Already filtered by tenant
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # The TenantManager will automatically filter, so if object
        # doesn't exist in tenant's scope, it will raise DoesNotExist
        return view_func(request, *args, **kwargs)
    
    return wrapper


def set_tenant_on_save(model_class, branch_field='branch'):
    """
    Decorator for views that create objects. Automatically sets the tenant.
    
    Usage:
        @login_required
        @set_tenant_on_save(Customer, 'branch')
        def create_customer(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Store the branch setting function in request
            def set_branch_on_instance(instance):
                if hasattr(instance, branch_field):
                    from company.models import Branch
                    branch_id = getattr(request.user, 'branch_id', None)
                    if branch_id:
                        try:
                            branch = Branch.objects.get(id=branch_id)
                            setattr(instance, branch_field, branch)
                        except Branch.DoesNotExist:
                            pass
                return instance
            
            request.set_branch_on_instance = set_branch_on_instance
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


class TenantViewMixin:
    """
    Mixin for class-based views that provides tenant filtering.
    
    Usage:
        class CustomerListView(TenantViewMixin, ListView):
            model = Customer
    """
    
    def get_queryset(self):
        """Automatically filter by tenant"""
        qs = super().get_queryset()
        # TenantManager should handle this, but as fallback:
        from profit_solutions.tenant_utils import filter_queryset_by_tenant
        return filter_queryset_by_tenant(qs, self.request.user)
    
    def get_tenant_branch(self):
        """Get the user's branch from vendor DB"""
        from profit_solutions.tenant_utils import get_user_branch
        return get_user_branch(self.request.user)
    
    def get_tenant_company(self):
        """Get the user's company from vendor DB"""
        from profit_solutions.tenant_utils import get_user_company
        return get_user_company(self.request.user)


class TenantCreateMixin:
    """
    Mixin for CreateView that automatically sets branch on new objects.
    
    Usage:
        class CustomerCreateView(TenantCreateMixin, CreateView):
            model = Customer
            branch_field = 'branch'  # Optional, defaults to 'branch'
    """
    branch_field = 'branch'
    
    def form_valid(self, form):
        """Set branch before saving"""
        instance = form.save(commit=False)
        
        branch_id = getattr(self.request.user, 'branch_id', None)
        if branch_id and hasattr(instance, self.branch_field):
            try:
                from company.models import Branch
                branch = Branch.objects.get(id=branch_id)
                setattr(instance, self.branch_field, branch)
            except Exception:
                pass
        
        instance.save()
        return super().form_valid(form)


def get_tenant_branch_for_form(request):
    """
    Helper to get branch for use in forms.
    
    Usage in view:
        def create_customer(request):
            if request.method == 'POST':
                form = CustomerForm(request.POST)
                if form.is_valid():
                    customer = form.save(commit=False)
                    customer.branch = get_tenant_branch_for_form(request)
                    customer.save()
    """
    from profit_solutions.tenant_utils import get_user_branch
    return get_user_branch(request.user)


def assign_tenant_to_instance(instance, user, branch_field='branch'):
    """
    Helper to assign tenant branch to any model instance.
    
    Usage:
        customer = Customer(...)
        assign_tenant_to_instance(customer, request.user)
        customer.save()
    """
    branch_id = getattr(user, 'branch_id', None)
    if branch_id and hasattr(instance, branch_field):
        try:
            from company.models import Branch
            branch = Branch.objects.get(id=branch_id)
            setattr(instance, branch_field, branch)
        except Exception:
            pass
    return instance
