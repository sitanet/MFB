from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from .models import AuditLog
import json
import threading

User = get_user_model()

# Thread-local storage for request tracking
_request_locals = threading.local()

class RequestMiddleware:
    """Middleware to store request object in thread-local storage"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store request in thread-local storage
        _request_locals.request = request
        response = self.get_response(request)
        # Clean up after response
        if hasattr(_request_locals, 'request'):
            del _request_locals.request
        return response

def get_current_request():
    """Get current request from thread-local storage"""
    return getattr(_request_locals, 'request', None)

def capture_user_context():
    """Capture user context from current request"""
    request = get_current_request()
    context = {
        'user': None,
        'ip': None,
        'user_agent': None
    }
    
    if request and hasattr(request, 'user'):
        user = request.user if request.user.is_authenticated else None
        context.update({
            'user': user,
            'ip': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255]
        })
    
    return context

def create_audit_log(instance, action, before=None, after=None, message=None):
    """Centralized audit log creation"""
    context = capture_user_context()
    
    # Get content type for generic relation
    try:
        content_type = ContentType.objects.get_for_model(instance.__class__)
    except:
        content_type = None
    
    # Capture user role and branch if available
    user_role = None
    user_branch = None
    
    if context['user']:
        if hasattr(context['user'], 'get_role_display'):
            user_role = context['user'].get_role_display()
        if hasattr(context['user'], 'branch') and context['user'].branch:
            user_branch = str(context['user'].branch)
    
    # Create the log entry
    AuditLog.objects.create(
        user=context['user'],
        action=action,
        content_type=content_type,
        object_id=str(instance.pk),
        content_object=instance,
        before=before,
        after=after,
        message=message or f"{instance._meta.verbose_name} {action.lower()}d",
        ip_address=context['ip'],
        user_agent=context['user_agent'],
        user_role=user_role,
        user_branch=user_branch,
    )

@receiver(pre_save)
def capture_pre_save_state(sender, instance, **kwargs):
    """Capture state before save"""
    # Skip Django internal models and AuditLog itself
    if sender.__module__.startswith('django.') or sender == AuditLog:
        return
    
    # Only for existing instances (updates)
    if hasattr(instance, 'pk') and instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            before_data = {}
            for field in instance._meta.fields:
                # Skip sensitive fields
                if field.name not in ['password', 'last_login', 'session_key']:
                    before_data[field.name] = getattr(old_instance, field.name)
            
            setattr(instance, '_audit_pre_save_data', before_data)
        except ObjectDoesNotExist:
            pass

@receiver(post_save)
def log_create_update(sender, instance, created, **kwargs):
    """Log object creation/updates"""
    # Skip Django internal models and AuditLog itself
    if sender.__module__.startswith('django.') or sender == AuditLog:
        return
    
    action = AuditLog.ACTION_CREATE if created else AuditLog.ACTION_UPDATE
    before_data = getattr(instance, '_audit_pre_save_data', None)
    
    # Capture after state
    after_data = {}
    for field in instance._meta.fields:
        if field.name not in ['password', 'last_login', 'session_key']:
            after_data[field.name] = getattr(instance, field.name)
    
    create_audit_log(
        instance=instance,
        action=action,
        before=before_data,
        after=after_data
    )

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    """Log object deletions"""
    # Skip Django internal models and AuditLog itself
    if sender.__module__.startswith('django.') or sender == AuditLog:
        return
    
    # Capture before state
    before_data = {}
    for field in instance._meta.fields:
        if field.name not in ['password', 'last_login', 'session_key']:
            before_data[field.name] = getattr(instance, field.name)
    
    create_audit_log(
        instance=instance,
        action=AuditLog.ACTION_DELETE,
        before=before_data,
        message=f"{instance._meta.verbose_name} deleted"
    )

def create_audit_log(instance, action, before=None, after=None, message=None):
    """Centralized audit log creation"""
    context = capture_user_context()
    
    log_data = {
        'user': context['user'],
        'action': action,
        'content_object': instance,
        'before': before,
        'after': after,
        'message': message or f"{instance._meta.verbose_name} {action.lower()}d",
        'ip_address': context['ip'],
        # Make user_agent optional
        'user_agent': context.get('user_agent', None),
    }
    
    # Create the log entry
    AuditLog.objects.create(**log_data)