from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Company
import logging

logger = logging.getLogger(__name__)

class ExpirationCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization
        self.last_check = None

    def __call__(self, request):
        # Check expiration daily (not on every request)
        if self.should_run_check():
            self.check_expirations()
            self.last_check = timezone.now()

        response = self.get_response(request)
        return response

    def should_run_check(self):
        """Only run check once per day"""
        if self.last_check is None:
            return True
        return (timezone.now() - self.last_check).days >= 1

    def check_expirations(self):
        """Check and handle expiring/expired companies"""
        today = timezone.now().date()
        warning_date = today + timezone.timedelta(days=15)
        
        # 15-day warning
        companies_to_notify = Company.objects.filter(
            expiration_date=warning_date,
            session_status='active',
            email__isnull=False
        )
        for company in companies_to_notify:
            self.send_expiration_warning(company)
        
        # Expired companies
        expired_companies = Company.objects.filter(
            expiration_date__lte=today,
            session_status='active'
        )
        for company in expired_companies:
            company.session_status = 'expired'
            company.save()
            if company.email:
                self.send_expiration_notice(company)

    def send_expiration_warning(self, company):
        try:
            send_mail(
                f"License Expiring Soon: {company.company_name}",
                self._warning_email_content(company),
                settings.DEFAULT_FROM_EMAIL,
                [company.email],
                fail_silently=False,
            )
            logger.info(f"Sent expiration warning to {company.email}")
        except Exception as e:
            logger.error(f"Failed to send warning to {company.email}: {str(e)}")

    def send_expiration_notice(self, company):
        try:
            send_mail(
                f"License Expired: {company.company_name}",
                self._expired_email_content(company),
                settings.DEFAULT_FROM_EMAIL,
                [company.email],
                fail_silently=False,
            )
            logger.info(f"Sent expiration notice to {company.email}")
        except Exception as e:
            logger.error(f"Failed to send expiration notice to {company.email}: {str(e)}")

    def _warning_email_content(self, company):
        return f"""...email content here..."""

    def _expired_email_content(self, company):
        return f"""...email content here..."""