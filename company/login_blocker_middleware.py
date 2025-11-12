from django.http import HttpResponseForbidden
from django.urls import reverse
from .models import Company

class ExpiredLicenseBlockerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                company = Branch.objects.get(associated_user=request.user)  # You'll need this relation
                if company.session_status == 'expired':
                    if not request.path == reverse('license_expired_page'):
                        return HttpResponseForbidden("Your license has expired")
            except Company.DoesNotExist:
                pass

        return self.get_response(request)