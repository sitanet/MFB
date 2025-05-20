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

        branch = getattr(request.user, 'branch', None)
        if branch is None:
            logger.warning(f"User {request.user} has no branch assigned")
            soon_expire_message = "No branch assigned to user"
            return {'soon_expire_message': soon_expire_message}

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
        logger.exception("Unexpected error in soon_to_expire:")
        soon_expire_message = "System error occurred"

    return {'soon_expire_message': soon_expire_message}
