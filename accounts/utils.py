from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage, message
from django.conf import settings

def detectUser(user):
    if user.role == 1:
        redirectUrl = 'dashboard'
        return redirectUrl
    elif user.role == 2:
        redirectUrl = 'dashboard_2'
        return redirectUrl
    elif user.role == 3:
        redirectUrl = 'dashboard_3'
        return redirectUrl
    elif user.role == 3:
        redirectUrl = 'dashboard_4'
        return redirectUrl
    elif user.role == 3:
        redirectUrl = 'dashboard_5'
        return redirectUrl
    elif user.role == 3:
        redirectUrl = 'dashboard_6'
        return redirectUrl
    elif user.role == 3:
        redirectUrl = 'dashboard_7'
        return redirectUrl
    elif user.role == 3:
        redirectUrl = 'dashboard_8'
        return redirectUrl
    elif user.role == 3:
        redirectUrl = 'dashboard_9'
        return redirectUrl
    elif user.role == 3:
        redirectUrl = 'dashboard_10'
        return redirectUrl
    elif user.role == 3:
        redirectUrl = 'dashboard_11'
        return redirectUrl
    elif user.role == 3:
        redirectUrl = 'dashboard_12'
        return redirectUrl
    elif user.role == None and user.is_superadmin:
        redirectUrl = '/admin'
        return redirectUrl

    
def send_verification_email(request, user, mail_subject, email_template):
    from_email = settings.DEFAULT_FROM_EMAIL
    current_site = get_current_site(request)
    message = render_to_string(email_template, {
        'user': user,
        'domain': current_site,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    })
    to_email = user.email
    mail = EmailMessage(mail_subject, message, from_email, to=[to_email])
    mail.content_subtype = "html"
    mail.send()


def send_notification(mail_subject, mail_template, context):
    from_email = settings.DEFAULT_FROM_EMAIL
    message = render_to_string(mail_template, context)
    if(isinstance(context['to_email'], str)):
        to_email = []
        to_email.append(context['to_email'])
    else:
        to_email = context['to_email']
    mail = EmailMessage(mail_subject, message, from_email, to=to_email)
    mail.content_subtype = "html"
    mail.send()

import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_sms(phone_number, message):
    api_key = settings.TERMII_API_KEY
    sender_id = settings.TERMII_SENDER_ID
    url = settings.TERMII_SMS_URL

    payload = {
        "to": phone_number,
        "from": sender_id,
        "sms": message,
        "type": "plain",
        "channel": "generic",
        "api_key": api_key,
    }

    try:
        response = requests.post(url, json=payload)
        response_data = response.json() if response.text else {}

        # Print full response for debugging
        logger.info(f"SMS Response: {response.status_code}, {response.text}")

        if response.status_code == 200 and response_data.get("message") == "Successfully Sent":
            logger.info(f"✅ SMS successfully sent to {phone_number}")
            return True
        else:
            logger.warning(f"❌ SMS failed for {phone_number}. Response: {response_data}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"🚨 Network Error while sending SMS: {e}")
        return False





import requests
import logging
from django.conf import settings
from company.models import SmsDelivery  # Optional: if tracking delivery

logger = logging.getLogger(__name__)

def _send_otp_sms(phone_number, message, branch=None):
    """Send OTP via Termii API"""
    try:
        if not phone_number or not phone_number.startswith('+'):
            logger.error(f"Invalid phone number: {phone_number}")
            return False

        payload = {
            "api_key": settings.TERMII_API_KEY,
            "to": phone_number,
            "from": settings.TERMII_SENDER_ID,
            "sms": message,
            "type": "plain",
            "channel": "dnd"
        }

        response = requests.post(
            settings.TERMII_SMS_URL,
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            logger.info(f"OTP sent to {phone_number}")
            # Optional: save to SmsDelivery
            return True
        else:
            logger.error(f"Failed to send SMS: {response.text}")
            return False

    except Exception as e:
        logger.exception("Error sending OTP SMS")
        return False
