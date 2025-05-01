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

        if not hasattr(request.user, 'branch') or request.user.branch is None:
            logger.warning(f"User {request.user} has no branch assigned")
            soon_expire_message = "No branch assigned to user"
            cache.set(cache_key, soon_expire_message, 3600)
            return {'soon_expire_message': soon_expire_message}

        branch = Branch.objects.get(branch_code=request.user.branch.branch_code)
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

        # Cache the result for 1 hour
        cache.set(cache_key, soon_expire_message, 3600)

    except Branch.DoesNotExist:
        logger.error(f"Branch not found for user {request.user}")
        soon_expire_message = "Branch not found"
    except Exception as e:
        logger.exception("Unexpected error in soon_to_expire:")
        soon_expire_message = "System error occurred"

    return {'soon_expire_message': soon_expire_message}
