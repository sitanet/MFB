import logging
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db import models

logger = logging.getLogger(__name__)

class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using either:
    - Email address
    - Phone number (for mobile app compatibility)
    
    This backend fixes the authentication issues where mobile sends phone numbers
    but web uses email addresses.
    """
    
    def authenticate(self, request, **credentials):
        """
        Authenticate user by email OR phone number and password.
        """
        print(f"\n[DEBUG-EmailBackend] ===== AUTHENTICATION ATTEMPT =====")
        print(f"[DEBUG-EmailBackend] Request: {request}")
        print(f"[DEBUG-EmailBackend] Credentials received: {credentials}")
        
        # Extract login identifier (email, phone, or username)
        login_identifier = (
            credentials.get('email') or 
            credentials.get('username') or 
            credentials.get('phone_number')
        )
        password = credentials.get('password')
        
        print(f"[DEBUG-EmailBackend] Login identifier: '{login_identifier}'")
        print(f"[DEBUG-EmailBackend] Password provided: {bool(password)}")
        
        if not login_identifier or not password:
            print("[DEBUG-EmailBackend] ❌ Missing login identifier or password")
            return None
        
        # Get user model
        try:
            User = get_user_model()
            print(f"[DEBUG-EmailBackend] ✅ User model: {User}")
        except Exception as e:
            print(f"[DEBUG-EmailBackend] ❌ Failed to get user model: {e}")
            return None
        
        # Determine if identifier is email or phone number
        is_email = '@' in str(login_identifier)
        
        try:
            if is_email:
                print(f"[DEBUG-EmailBackend] Looking up user by EMAIL: {login_identifier}")
                user = User.objects.get(email__iexact=login_identifier.strip())
            else:
                print(f"[DEBUG-EmailBackend] Looking up user by PHONE: {login_identifier}")
                # Try phone_number field first, then mobile field as fallback
                try:
                    user = User.objects.get(phone_number=login_identifier)
                except User.DoesNotExist:
                    # Check if user has a customer profile with mobile number
                    user = User.objects.get(customer__mobile=login_identifier)
            
            print(f"[DEBUG-EmailBackend] ✅ Found user: {user.username} (id={user.id})")
            print(f"[DEBUG-EmailBackend] User email: {user.email}")
            print(f"[DEBUG-EmailBackend] User phone: {getattr(user, 'phone_number', 'N/A')}")
            print(f"[DEBUG-EmailBackend] User verified: {getattr(user, 'verified', 'N/A')}")
            print(f"[DEBUG-EmailBackend] User active: {getattr(user, 'is_active', 'N/A')}")
            
        except User.DoesNotExist:
            print(f"[DEBUG-EmailBackend] ❌ No user found with identifier: {login_identifier}")
            return None
        except User.MultipleObjectsReturned:
            print(f"[DEBUG-EmailBackend] ❌ Multiple users found with identifier: {login_identifier}")
            return None
        except Exception as e:
            print(f"[DEBUG-EmailBackend] ❌ Database error during user lookup: {e}")
            return None
        
        # Verify password
        try:
            print(f"[DEBUG-EmailBackend] Checking password...")
            password_valid = user.check_password(password)
            print(f"[DEBUG-EmailBackend] Password check result: {password_valid}")
            
            if password_valid:
                print(f"[DEBUG-EmailBackend] ✅ Authentication SUCCESS for user: {user.username}")
                return user
            else:
                print(f"[DEBUG-EmailBackend] ❌ Password check FAILED for user: {user.username}")
                return None
        except Exception as e:
            print(f"[DEBUG-EmailBackend] ❌ Error during password check: {e}")
            return None

    def get_user(self, user_id):
        """Required method for Django auth backends."""
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None