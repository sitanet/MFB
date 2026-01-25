from django import template

register = template.Library()


def _user_has_permission(user, permission_code):
    """Check if a user has a specific permission"""
    from accounts.models import RolePermission
    
    if not user or not user.is_authenticated:
        return False
    
    # System Administrator (role=1) has all permissions
    if user.role == 1 or user.is_superadmin or user.is_admin:
        return True
    
    # Check role-based permissions
    try:
        role_perm = RolePermission.objects.get(role=user.role)
        return permission_code in role_perm.permissions
    except RolePermission.DoesNotExist:
        return False


@register.simple_tag(takes_context=True)
def has_perm(context, permission_code):
    """Template tag to check if the current user has a specific permission.
    Usage: {% has_perm 'view_dashboard' as can_view %}{% if can_view %}...{% endif %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return False
    return _user_has_permission(request.user, permission_code)


@register.filter
def has_permission(user, permission_code):
    """Template filter to check if user has permission.
    Usage: {% if user|has_permission:'view_dashboard' %}...{% endif %}
    """
    return _user_has_permission(user, permission_code)


@register.simple_tag(takes_context=True)
def check_admin(context):
    """Template tag to check if current user is an admin"""
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return False
    user = request.user
    if not user.is_authenticated:
        return False
    return user.role == 1 or user.is_superadmin or user.is_admin
