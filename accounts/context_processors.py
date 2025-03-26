from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from company.models import Branch
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

from django.utils import timezone
from accounts.utils import send_sms


def soon_to_expire(request):
    soon_expire_message = None

    if request.user.is_authenticated:
        try:
            branch = Branch.objects.select_related("company").get(branch_code=request.user.branch.branch_code)
            company = branch.company
            
            expiration_date = company.expiration_date
            company_email = company.email
            company_phone = company.contact_phone_no
            today = timezone.now().date()

            if today <= expiration_date <= today + timezone.timedelta(days=30):

                if company.last_notification_date == today:
                    logger.info(f"🔹 Notification already sent today for {company.company_name}")
                    return {'soon_expire_message': "A notification has already been sent today."}

                soon_expire_message = "Your company's license will expire soon. Please contact your vendor."

                # Render the email template
                html_content = render_to_string("emails/license_expiration.html", {
                    "company_name": company.company_name,
                    "expiration_date": expiration_date
                })
                text_content = strip_tags(html_content)  # Fallback for non-HTML email clients

                # Send Email Notification
                try:
                    email = EmailMultiAlternatives(
                        subject="License Expiration Warning",
                        body=text_content,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[company_email],
                    )
                    email.attach_alternative(html_content, "text/html")  # Attach HTML version
                    email.send()

                    logger.info(f"✅ HTML Email sent to {company_email}")
                except Exception as e:
                    logger.error(f"❌ Email sending failed: {str(e)}")

                # Send SMS Notification
                sms_message = f"Dear {company.company_name}, your company's license will expire on {expiration_date}. Please renew soon."
                sms_status = send_sms(company_phone, sms_message)

                if sms_status:
                    logger.info(f"✅ SMS sent to {company_phone}")
                else:
                    logger.error(f"❌ SMS sending failed for {company_phone}")

                company.last_notification_date = today
                company.save(update_fields=["last_notification_date"])

        except Branch.DoesNotExist:
            soon_expire_message = "Company details not found. Please contact your vendor."
        except Exception as e:
            logger.error(f"License expiry check error: {str(e)}")
            soon_expire_message = "An unexpected error occurred. Please contact support."

    return {'soon_expire_message': soon_expire_message}
