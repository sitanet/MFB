# company/backends.py

from django.contrib.auth.backends import ModelBackend
from django.utils import timezone
from .models import Branch, VendorUser
from accounts.models import User

class LicenseExpiredError(Exception):
    pass


class LicenseExpirationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(username=username)
            company = Branch.objects.get(branch_code=user.profile.branch_code)
            if company.expiration_date <= timezone.now().date():
                raise LicenseExpiredError("Your company's license has expired. Please contact your vendor.")
        except User.DoesNotExist:
            return None
        except Branch.DoesNotExist:
            return None
        except LicenseExpiredError as e:
            e.message = "Your company's license has expired. Please contact your vendor."
            raise
        return user if user.check_password(password) else None


class VendorAuthBackend(ModelBackend):
    """
    Authentication backend for VendorUser model.
    Used for vendor/company management login - separate from client users.
    """
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        """
        Authenticate vendor user by email and password.
        """
        try:
            user = VendorUser.objects.get(email=email)
            if user.check_password(password) and user.is_active:
                return user
        except VendorUser.DoesNotExist:
            return None
        return None
    
    def get_user(self, user_id):
        """
        Retrieve vendor user by ID.
        """
        try:
            return VendorUser.objects.get(pk=user_id)
        except VendorUser.DoesNotExist:
            return None
