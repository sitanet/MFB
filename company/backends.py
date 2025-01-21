# accounts/backends.py

from django.contrib.auth.backends import ModelBackend
from django.utils import timezone
from .models import Company
from accounts.models import User

class LicenseExpiredError(Exception):
    pass

class LicenseExpirationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(username=username)
            company = Company.objects.get(branch_code=user.profile.branch_code)
            if company.expiration_date <= timezone.now().date():  # Check if expiration date is today or in the past
                raise LicenseExpiredError("Your company's license has expired. Please contact your vendor.")
        except User.DoesNotExist:
            return None  # User does not exist
        except Company.DoesNotExist:
            return None  # Company does not exist for the user
        except LicenseExpiredError as e:
            e.message = "Your company's license has expired. Please contact your vendor."
            raise
        return user if user.check_password(password) else None
