from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import json
from functools import wraps

User = get_user_model()

# Permission Utilities
def check_audit_log_permission(permission_codename):
    """Decorator to check specific audit log permissions"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.has_perm(f'audit_trail.{permission_codename}'):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def user_can_view_audit_logs(user):
    """Check if user has view permission"""
    return user.has_perm('audit_trail.can_view_auditlog')

def user_can_delete_audit_logs(user):
    """Check if user has delete permission"""
    return user.has_perm('audit_trail.can_delete_auditlog')

def user_can_export_audit_logs(user):
    """Check if user has export permission"""
    return user.has_perm('audit_trail.can_export_auditlog')

# Filtering Utilities
def apply_audit_log_filters(queryset, filters):
    """
    Apply filters to audit log queryset
    Args:
        filters: {
            'date_range': 'today|week|month|year',
            'start_date': date,
            'end_date': date,
            'action': str,
            'user_id': int,
            'role': str,
            'branch': str,
            'search': str
        }
    """
    if not filters:
        return queryset
    
    # Date filtering
    date_ranges = {
        'today': lambda: timezone.now().date(),
        'week': lambda: timezone.now().date() - timedelta(days=7),
        'month': lambda: timezone.now().date() - timedelta(days=30),
        'year': lambda: timezone.now().date() - timedelta(days=365),
    }
    
    if date_range := filters.get('date_range'):
        if date_range in date_ranges:
            date_value = date_ranges[date_range]()
            if date_range == 'today':
                queryset = queryset.filter(timestamp__date=date_value)
            else:
                queryset = queryset.filter(timestamp__date__gte=date_value)
    
    if start_date := filters.get('start_date'):
        queryset = queryset.filter(timestamp__date__gte=start_date)
    
    if end_date := filters.get('end_date'):
        queryset = queryset.filter(timestamp__date__lte=end_date)
    
    # Action filtering
    if action := filters.get('action'):
        queryset = queryset.filter(action=action)
    
    # User filtering
    if user_id := filters.get('user_id'):
        queryset = queryset.filter(user_id=user_id)
    
    # Role filtering
    if role := filters.get('role'):
        queryset = queryset.filter(user_role=role)
    
    # Branch filtering
    if branch := filters.get('branch'):
        queryset = queryset.filter(user_branch=branch)
    
    # Search
    if search := filters.get('search'):
        queryset = queryset.filter(
            Q(user__username__icontains=search) |
            Q(message__icontains=search) |
            Q(ip_address__icontains=search) |
            Q(object_id__icontains=search) |
            Q(user_role__icontains=search) |
            Q(user_branch__icontains=search)
        )
    
    return queryset

# JSON Utilities
class AuditLogEncoder(json.JSONEncoder):
    """Custom JSON encoder for audit log data"""
    def default(self, obj):
        if hasattr(obj, 'pk'):
            return {
                'model': f"{obj._meta.app_label}.{obj._meta.model_name}",
                'id': str(obj.pk),
                'str': str(obj),
                'fields': {
                    f.name: getattr(obj, f.name) 
                    for f in obj._meta.fields 
                    if f.name != 'password'
                }
            }
        return super().default(obj)

def serialize_audit_data(data):
    """Serialize data for audit logging"""
    try:
        return json.loads(json.dumps(data, cls=AuditLogEncoder))
    except:
        return str(data)

# Context Utilities
def get_audit_log_context(request=None):
    """Get context for audit logging from request"""
    context = {
        'user': None,
        'ip_address': None,
        'user_agent': None
    }
    
    if request:
        context.update({
            'user': request.user if request.user.is_authenticated else None,
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255]
        })
    return context

def capture_user_context(user):
    """Capture user context without modifying User model"""
    context = {
        'user_role': None,
        'user_branch': None
    }
    
    if user and user.is_authenticated:
        # Get role display if available
        if hasattr(user, 'get_role_display'):
            context['user_role'] = user.get_role_display()
        
        # Get branch if available
        if hasattr(user, 'branch') and user.branch:
            context['user_branch'] = str(user.branch)
    
    return context

# Export Utilities
def generate_audit_log_csv(queryset):
    """Generate CSV data from audit log queryset"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Timestamp', 'User', 'Role', 'Branch', 'Action', 
        'Object Type', 'Object ID', 'IP Address', 'Message'
    ])
    
    # Write data
    for log in queryset:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.user.username if log.user else 'System',
            log.user_role,
            log.user_branch,
            log.get_action_display(),
            log.content_type.model if log.content_type else '',
            log.object_id,
            log.ip_address,
            log.message,
        ])
    
    return output.getvalue()

# Maintenance Utilities
def cleanup_old_audit_logs(days=365):
    """Delete audit logs older than specified days"""
    from .models import AuditLog
    cutoff_date = timezone.now() - timedelta(days=days)
    deleted_count, _ = AuditLog.objects.filter(
        timestamp__lte=cutoff_date
    ).delete()
    return deleted_count