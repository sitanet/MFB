import logging
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db import models

logger = logging.getLogger(__name__)

# Use lazy loading to avoid circular import issues
def get_user_model_safe():
    try:
        return get_user_model()
    except Exception as e:
        logger.error(f"Failed to get user model: {e}")
        return None

class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using their email address.
    
    This backend fixes the authentication issues where users could not log in via web
    interface while mobile login worked fine.
    """
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        """
        Authenticate user by email and password.
        
        Args:
            request: HTTP request object (can be None)
            email: User's email address
            password: User's password
            **kwargs: Additional keyword arguments (unused but required by interface)
            
        Returns:
            User object if authentication succeeds, None otherwise
        """
        logger.debug(f"[EmailBackend] Authentication attempt for email: {email}")
        
        # Check for required parameters
        if not email or not password:
            logger.debug("[EmailBackend] Missing email or password")
            return None
        
        # Get user model safely
        User = get_user_model_safe()
        if not User:
            logger.error("[EmailBackend] Could not get user model")
            return None
            
        try:
            # Look up user by email (case insensitive)
            user = User.objects.get(email__iexact=email.strip())
            logger.debug(f"[EmailBackend] Found user: {user.username} (id={user.id})")
        except User.DoesNotExist:
            logger.debug(f"[EmailBackend] No user found with email: {email}")
            return None
        except User.MultipleObjectsReturned:
            logger.error(f"[EmailBackend] Multiple users found with email: {email}")
            return None
        except Exception as e:
            logger.error(f"[EmailBackend] Database error during user lookup: {e}")
            return None
        
        # Verify password
        try:
            if user.check_password(password):
                logger.debug(f"[EmailBackend] Password check SUCCESS for user: {user.username}")
                return user
            else:
                logger.debug(f"[EmailBackend] Password check FAILED for user: {user.username}")
                return None
        except Exception as e:
            logger.error(f"[EmailBackend] Error during password check for {user.username}: {e}")
            return None
