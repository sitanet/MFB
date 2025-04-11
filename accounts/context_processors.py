from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from company.models import Branch
from django.conf import settings
import logging
from django.utils import timezone
from accounts.utils import send_sms

logger = logging.getLogger(__name__)

def soon_to_expire(request):
    soon_expire_message = None

    if not request.user.is_authenticated:
        return {'soon_expire_message': "User not authenticated"}

    try:
        # Get branch with related company in a single query
        branch = Branch.objects.select_related("company").get(
            branch_code=request.user.branch.branch_code
        )
        company = branch.company
        
        if not company.expiration_date:
            return {'soon_expire_message': "No expiration date set for this company"}

        expiration_date = company.expiration_date
        today = timezone.now().date()

        # Check if expiration is within 30 days
        if today > expiration_date:
            return {'soon_expire_message': "License has already expired"}

        if expiration_date > today + timezone.timedelta(days=30):
            return {'soon_expire_message': None}  # No action needed yet

        # Check if notification was already sent today
        if company.last_notification_date == today:
            logger.info(f"Notification already sent today for {company.company_name}")
            return {'soon_expire_message': "A notification has already been sent today."}

        soon_expire_message = "Your company's license will expire soon. Please contact your vendor."

        # Prepare email content
        context = {
            "company_name": company.company_name,
            "expiration_date": expiration_date
        }

        # Send Email Notification
        try:
            html_content = render_to_string("emails/license_expiration.html", context)
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject="License Expiration Warning",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[company.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            logger.info(f"Email sent successfully to {company.email}")
        except Exception as e:
            logger.error(f"Email sending failed to {company.email}: {str(e)}")
            soon_expire_message = "Email notification failed. Please contact support."

        # Send SMS Notification
        if company.contact_phone_no:
            sms_message = (
                f"Dear {company.company_name}, "
                f"your license expires on {expiration_date}. "
                "Please renew soon."
            )
            try:
                sms_status = send_sms(company.contact_phone_no, sms_message)
                if sms_status:
                    logger.info(f"SMS sent to {company.contact_phone_no}")
                else:
                    logger.error(f"SMS failed for {company.contact_phone_no}")
            except Exception as e:
                logger.error(f"SMS sending error: {str(e)}")

        # Update last notification date
        company.last_notification_date = today
        company.save(update_fields=["last_notification_date"])

    except Branch.DoesNotExist:
        logger.error(f"Branch not found for user {request.user}")
        soon_expire_message = "Company details not found. Please contact your vendor."
    except Exception as e:
        logger.exception("Unexpected error in soon_to_expire:")  # This logs the full traceback
        soon_expire_message = "An unexpected error occurred. Please contact support."

    return {'soon_expire_message': soon_expire_message}