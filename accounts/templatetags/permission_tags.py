from django import template
from accounts.views import user_has_permission

register = template.Library()


@register.simple_tag(takes_context=True)
def has_permission(context, permission_code):
    """Template tag to check if the current user has a specific permission"""
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return False
    return user_has_permission(request.user, permission_code)


@register.simple_tag(takes_context=True)
def is_admin_user(context):
    """Template tag to check if current user is an admin"""
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return False
    user = request.user
    if not user.is_authenticated:
        return False
    return user.role == 1 or user.is_superadmin or user.is_admin
