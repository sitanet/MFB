from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import AuditTrail, AuditAction, AuditCategory
from .utils import get_client_ip

User = get_user_model()

def get_user_full_name(user):
    """Helper function to get user's full name"""
    if user:
        full_name = f"{user.first_name} {user.last_name}".strip()
        return full_name if full_name else user.username
    return "Unknown"

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log successful user login"""
    AuditTrail.objects.create(
        user=user,
        session_key=request.session.session_key,
        action=AuditAction.LOGIN,
        category=AuditCategory.AUTHENTICATION,
        description=f"User {get_user_full_name(user)} logged in successfully",
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        request_method='POST',
        request_path=request.path,
        success=True,
        compliance_level='HIGH'
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout"""
    AuditTrail.objects.create(
        user=user,
        session_key=request.session.session_key if request.session.session_key else '',
        action=AuditAction.LOGOUT,
        category=AuditCategory.AUTHENTICATION,
        description=f"User {get_user_full_name(user) if user else 'Unknown'} logged out",
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        request_method='POST',
        request_path=request.path,
        success=True,
        compliance_level='MEDIUM'
    )

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """Log failed login attempts"""
    AuditTrail.objects.create(
        user=None,
        session_key=request.session.session_key,
        action=AuditAction.LOGIN,
        category=AuditCategory.AUTHENTICATION,
        description=f"Failed login attempt for {credentials.get('username', 'Unknown')}",
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        request_method='POST',
        request_path=request.path,
        success=False,
        error_message="Invalid credentials",
        compliance_level='CRITICAL'
    )