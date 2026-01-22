from django.utils import timezone
from django.core.cache import cache
from company.models import Branch
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

def soon_to_expire(request):
    soon_expire_message = None

    if not request.user.is_authenticated:
        return {'soon_expire_message': None}

    try:
        cache_key = f"soon_expire_message_{request.user.id}"
        cached_message = cache.get(cache_key)
        if cached_message is not None:
            return {'soon_expire_message': cached_message}

        # ✅ FIXED: Use branch_id instead of branch
        branch_id = getattr(request.user, 'branch_id', None)
        
        if not branch_id:
            logger.warning(f"User {request.user.username} has no branch_id assigned")
            soon_expire_message = "No branch assigned to user"
            return {'soon_expire_message': soon_expire_message}

        # ✅ Get branch object using branch_id
        try:
            if isinstance(branch_id, str):
                branch_id_int = int(branch_id)
            else:
                branch_id_int = branch_id
                
            branch = Branch.objects.get(id=branch_id_int)
            
        except ValueError:
            logger.error(f"User {request.user.username} has invalid branch_id format: '{branch_id}'")
            soon_expire_message = "Invalid branch ID format - contact administrator"
            return {'soon_expire_message': soon_expire_message}
            
        except Branch.DoesNotExist:
            logger.error(f"User {request.user.username} branch_id '{branch_id}' does not exist")
            soon_expire_message = f"Branch ID '{branch_id}' does not exist - contact administrator"
            return {'soon_expire_message': soon_expire_message}

        # Continue with expiration check
        expiration_date = branch.expire_date
        today = timezone.now().date()

        if not expiration_date:
            soon_expire_message = "No expiration date set for this branch"
        elif today > expiration_date:
            soon_expire_message = "License has expired"
        elif expiration_date <= today + timedelta(days=30):
            soon_expire_message = f"License expires on {expiration_date}. Please renew."
        else:
            soon_expire_message = None

        cache.set(cache_key, soon_expire_message, 3600)

    except Exception as e:
        logger.exception(f"Unexpected error in soon_to_expire for user {request.user.username}:")
        soon_expire_message = "System error occurred"

    return {'soon_expire_message': soon_expire_message}


def user_permissions(request):
    """Context processor to make permission checking available in templates"""
    from accounts.models import RolePermission
    
    def has_permission(permission_code):
        if not request.user.is_authenticated:
            return False
        
        # System Administrator has all permissions
        if request.user.role == 1 or request.user.is_superadmin or request.user.is_admin:
            return True
        
        try:
            role_perm = RolePermission.objects.get(role=request.user.role)
            return permission_code in role_perm.permissions
        except RolePermission.DoesNotExist:
            return False
    
    return {
        'has_permission': has_permission,
        'is_admin_user': request.user.is_authenticated and (
            request.user.role == 1 or 
            request.user.is_superadmin or 
            request.user.is_admin
        ) if hasattr(request, 'user') else False,
    }