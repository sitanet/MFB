from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage, message
from django.conf import settings


# ==================== BRANCH/COMPANY FILTERING HELPERS ====================

def get_branch_from_vendor_db(branch_id):
    """Helper function to get branch from database"""
    if not branch_id:
        return None
    try:
        from company.models import Branch
        # Convert to int if it's a string
        branch_id_int = int(branch_id) if isinstance(branch_id, str) else branch_id
        return Branch.objects.get(id=branch_id_int)
    except (Branch.DoesNotExist, ValueError, TypeError):
        return None


def get_all_branches_from_vendor_db():
    """Helper function to get all branches from database"""
    from company.models import Branch
    return Branch.objects.all()


def is_admin_user(user):
    """
    Check if user is a System Administrator (role=1) or has admin privileges.
    Admins can view all branch activities in their company.
    """
    if not user:
        return False
    return user.role == 1 or user.is_admin or user.is_superadmin


def is_super_admin(user):
    """
    Check if user is a Super Admin (software vendor level).
    Super admins can view ALL data across ALL companies without restriction.
    """
    if not user:
        return False
    return user.is_superadmin


def get_company_branch_ids(user, admin_sees_all=True):
    """
    Get branch IDs for filtering based on user role.
    
    - Super Admin (is_superadmin): See ALL branches across ALL companies
    - Admin users (role=1): See all branches in their company
    - Non-admin users: See only their own branch (unless admin_sees_all=False)
    
    Args:
        user: The current user
        admin_sees_all: If True, admins see all company branches. If False, filter by user's branch only.
    
    Returns a list of branch IDs (integers for ForeignKey, strings for CharField).
    """
    from company.models import Branch
    
    if not user:
        return []
    
    # Super Admin sees ALL branches across ALL companies
    if is_super_admin(user):
        all_branches = Branch.objects.all()
        return [b.id for b in all_branches]
    
    if not user.branch_id:
        return []
    
    user_branch = get_branch_from_vendor_db(user.branch_id)
    if not user_branch or not user_branch.company:
        try:
            return [int(user.branch_id)] if user.branch_id else []
        except (ValueError, TypeError):
            return [user.branch_id] if user.branch_id else []
    
    # Admin users see all branches in the company
    if admin_sees_all and is_admin_user(user):
        company_branches = Branch.objects.filter(company=user_branch.company)
        return [b.id for b in company_branches]
    
    # Non-admin users see only their own branch
    try:
        return [int(user.branch_id)]
    except (ValueError, TypeError):
        return [user.branch_id]


def get_company_branch_ids_all(user):
    """
    Get ALL branch IDs belonging to the user's company.
    This always returns all company branches regardless of user role.
    Used for company-wide resources like Chart of Accounts.
    
    - Super Admin (is_superadmin): See ALL branches across ALL companies
    - Other users: See all branches in their company
    """
    from company.models import Branch
    
    if not user:
        return []
    
    # Super Admin sees ALL branches across ALL companies
    if is_super_admin(user):
        all_branches = Branch.objects.all()
        return [b.id for b in all_branches]
    
    if not user.branch_id:
        return []
    
    user_branch = get_branch_from_vendor_db(user.branch_id)
    if not user_branch or not user_branch.company:
        try:
            return [int(user.branch_id)] if user.branch_id else []
        except (ValueError, TypeError):
            return [user.branch_id] if user.branch_id else []
    
    # Get all branches belonging to the same company
    company_branches = Branch.objects.filter(company=user_branch.company)
    return [b.id for b in company_branches]


def get_user_company(user):
    """Get the company object for the current user"""
    if not user or not user.branch_id:
        return None
    
    user_branch = get_branch_from_vendor_db(user.branch_id)
    if user_branch:
        return user_branch.company
    return None


def filter_by_company(queryset, user, branch_field='branch_id', admin_sees_all=True):
    """
    Filter a queryset based on user role and branch.
    
    - Admin users: See records from all branches in their company
    - Non-admin users: See only records from their own branch
    
    Args:
        queryset: The Django queryset to filter
        user: The current user
        branch_field: The name of the branch_id field in the model (default: 'branch_id')
        admin_sees_all: If True, admins see all company data. If False, everyone sees only their branch.
    
    Returns:
        Filtered queryset
    """
    branch_ids = get_company_branch_ids(user, admin_sees_all=admin_sees_all)
    if not branch_ids:
        return queryset.none()
    
    filter_kwargs = {f'{branch_field}__in': branch_ids}
    return queryset.filter(**filter_kwargs)

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
# from company.models import SmsDelivery  # Uncomment if you want delivery tracking

logger = logging.getLogger(__name__)


def send_sms(phone_number, message, branch=None):
    """
    Send SMS using Termii API.
    - Reads API config from settings.py
    - Ensures phone number is in correct format
    - Returns True/False
    """
    try:
        if not phone_number:
            logger.error("No phone number provided.")
            return False

        # Normalize: ensure +234 format (or whatever your country code is)
        if phone_number.startswith("0"):
            phone_number = "+234" + phone_number[1:]
        elif not phone_number.startswith("+"):
            logger.warning(f"Phone number not in international format: {phone_number}")

        payload = {
            "api_key": settings.TERMII_API_KEY,
            "to": phone_number,
            "from": settings.TERMII_SENDER_ID,
            "sms": message,
            "type": "plain",
            "channel": "generic",  # or "generic" depending on your use case
        }

        response = requests.post(settings.TERMII_SMS_URL, json=payload, timeout=15)
        response_data = response.json() if response.text else {}

        logger.info(f"[SMS] Response: {response.status_code}, {response.text}")

        if response.status_code == 200 and response_data.get("message") == "Successfully Sent":
            logger.info(f"✅ SMS successfully sent to {phone_number}")

            # Optional: Track in DB
            # SmsDelivery.objects.create(
            #     phone_number=phone_number,
            #     message=message,
            #     status="sent",
            #     branch=branch
            # )

            return True

        logger.warning(f"❌ SMS failed for {phone_number}. Response: {response_data}")
        return False

    except requests.exceptions.RequestException as e:
        logger.error(f"🚨 Network Error while sending SMS: {e}")
        return False
    except Exception as e:
        logger.exception("🚨 Unexpected error while sending SMS")
        return False








from django.contrib import auth, messages
from django.shortcuts import redirect
from django.utils import timezone

def enforce_auto_logout(request):
    if not request.user.is_authenticated:
        return None

    minutes = request.session.get('auto_logout_minutes')
    if not minutes:
        return None

    try:
        minutes = int(minutes)
        if minutes <= 0:
            return None
    except (TypeError, ValueError):
        return None

    now = timezone.now()
    last_activity = request.session.get('last_activity')

    if last_activity:
        last_activity = timezone.datetime.fromisoformat(last_activity)
        if timezone.is_naive(last_activity):
            last_activity = timezone.make_aware(last_activity)
    else:
        last_activity = now

    if (now - last_activity).total_seconds() > minutes * 60:
        auth.logout(request)
        request.session.flush()
        messages.info(request, 'You have been logged out due to inactivity.')
        return redirect('login')

    request.session['last_activity'] = now.isoformat()
    return None
