from django.http import HttpRequest
from audit_trail.models import AuditCategory

def get_client_ip(request):
    """Get the real IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def should_track_request(request):
    """Determine if we should track this request"""
    
    # Skip static files and media
    if request.path.startswith('/static/') or request.path.startswith('/media/'):
        return False
    
    # Skip admin pages (since we're not using admin)
    if request.path.startswith('/admin/'):
        return False
    
    # Skip API health checks
    if 'health' in request.path.lower():
        return False
    
    # Skip favicon
    if 'favicon' in request.path.lower():
        return False
    
    # Skip AJAX requests that are just status checks
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Allow important AJAX requests but skip status checks
        if any(skip in request.path.lower() for skip in ['status', 'ping', 'heartbeat']):
            return False
    
    return True

def determine_category(request):
    """Determine the audit category based on the request path"""
    
    path = request.path.lower()
    
    # Authentication
    if any(auth in path for auth in ['login', 'logout', 'auth', 'register']):
        return AuditCategory.AUTHENTICATION
    
    # Customer operations
    if any(customer in path for customer in ['customer', 'client']):
        return AuditCategory.CUSTOMER
    
    # Account operations
    if any(account in path for account in ['account', 'profile']):
        return AuditCategory.ACCOUNT
    
    # Transactions
    if any(trans in path for trans in ['transaction', 'deposit', 'withdrawal', 'transfer']):
        return AuditCategory.TRANSACTION
    
    # Loans
    if 'loan' in path:
        return AuditCategory.LOAN
    
    # Reports
    if 'report' in path:
        return AuditCategory.REPORT
    
    # CBN Returns
    if 'cbn' in path:
        return AuditCategory.CBN_RETURNS
    
    # Fixed Assets
    if 'fixed_asset' in path or 'asset' in path:
        return AuditCategory.FIXED_ASSETS
    
    # Fixed Deposits
    if 'fixed_deposit' in path or 'fixed_dep' in path:
        return AuditCategory.FIXED_DEPOSIT
    
    # Admin operations
    if any(admin in path for admin in ['admin', 'settings', 'config', 'user_admin']):
        return AuditCategory.ADMIN
    
    # Bulk operations
    if any(bulk in path for bulk in ['bulk', 'upload', 'import', 'batch']):
        return AuditCategory.BULK_OPERATIONS
    
    return AuditCategory.ADMIN  # Default category

def format_currency(amount):
    """Format currency for display"""
    if amount is None:
        return ""
    return f"₦{amount:,.2f}"

def mask_sensitive_data(data, sensitive_fields=None):
    """Mask sensitive data in audit logs"""
    if sensitive_fields is None:
        sensitive_fields = ['password', 'pin', 'ssn', 'account_number', 'card_number']
    
    if isinstance(data, dict):
        masked_data = {}
        for key, value in data.items():
            if any(field in key.lower() for field in sensitive_fields):
                masked_data[key] = "*" * len(str(value)) if value else None
            else:
                masked_data[key] = value
        return masked_data
    
    return data

def create_audit_log(user, action, category, description, **kwargs):
    """Helper function to manually create audit logs"""
    from audit_trail.models import AuditTrail
    
    return AuditTrail.objects.create(
        user=user,
        action=action,
        category=category,
        description=description,
        **kwargs
    )