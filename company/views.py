from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from functools import wraps

from accounts.views import check_role_admin
from .models import Company, Branch, VendorUser
from .forms import CompanyForm, BranchForm, EndSession


# ==================== VENDOR AUTHENTICATION DECORATOR ====================

def vendor_login_required(view_func):
    """
    Decorator to require vendor user authentication.
    Redirects to vendor login if not authenticated as vendor.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        vendor_user_id = request.session.get('vendor_user_id')
        if not vendor_user_id:
            messages.error(request, 'Please login to access vendor management.')
            return redirect('vendor_login')
        
        try:
            vendor_user = VendorUser.objects.get(id=vendor_user_id, is_active=True)
            request.vendor_user = vendor_user
        except VendorUser.DoesNotExist:
            request.session.pop('vendor_user_id', None)
            messages.error(request, 'Session expired. Please login again.')
            return redirect('vendor_login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


# ==================== VENDOR AUTHENTICATION VIEWS ====================

def vendor_login(request):
    """Vendor login view - separate from client login"""
    # If already logged in as vendor, redirect to dashboard
    if request.session.get('vendor_user_id'):
        return redirect('vendor_dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'company/vendor_login.html')
        
        try:
            vendor_user = VendorUser.objects.get(email=email)
            if vendor_user.check_password(password):
                if vendor_user.is_active:
                    # Store vendor user in session
                    request.session['vendor_user_id'] = vendor_user.id
                    request.session['vendor_user_name'] = vendor_user.get_full_name()
                    messages.success(request, f'Welcome back, {vendor_user.first_name}!')
                    return redirect('vendor_dashboard')
                else:
                    messages.error(request, 'Your account is inactive. Contact administrator.')
            else:
                messages.error(request, 'Invalid email or password.')
        except VendorUser.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'company/vendor_login.html')


def vendor_logout(request):
    """Vendor logout view"""
    request.session.pop('vendor_user_id', None)
    request.session.pop('vendor_user_name', None)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('vendor_login')


@vendor_login_required
def vendor_dashboard(request):
    """Vendor dashboard - overview of all companies and branches"""
    companies = Company.objects.all()
    branches = Branch.objects.all()
    
    # Statistics
    total_companies = companies.count()
    total_branches = branches.count()
    active_branches = branches.filter(is_active=True).count()
    inactive_branches = branches.filter(is_active=False).count()
    
    context = {
        'vendor_user': request.vendor_user,
        'total_companies': total_companies,
        'total_branches': total_branches,
        'active_branches': active_branches,
        'inactive_branches': inactive_branches,
        'recent_companies': companies.order_by('-id')[:5],
        'recent_branches': branches.order_by('-created_at')[:5],
    }
    return render(request, 'company/vendor_dashboard.html', context)


# ==================== VENDOR USER MANAGEMENT VIEWS ====================

@vendor_login_required
def vendor_user_list(request):
    """List all vendor users"""
    vendor_users = VendorUser.objects.all().order_by('-date_joined')
    context = {
        'vendor_user': request.vendor_user,
        'vendor_users': vendor_users,
    }
    return render(request, 'company/vendor_user_list.html', context)


@vendor_login_required
def vendor_user_create(request):
    """Create a new vendor user"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        is_supervendor = request.POST.get('is_supervendor') == 'on'
        
        # Validation
        if not all([email, username, first_name, last_name, password]):
            messages.error(request, 'All required fields must be filled.')
            return render(request, 'company/vendor_user_create.html', {'vendor_user': request.vendor_user})
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'company/vendor_user_create.html', {'vendor_user': request.vendor_user})
        
        if VendorUser.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists.')
            return render(request, 'company/vendor_user_create.html', {'vendor_user': request.vendor_user})
        
        if VendorUser.objects.filter(username=username).exists():
            messages.error(request, 'A user with this username already exists.')
            return render(request, 'company/vendor_user_create.html', {'vendor_user': request.vendor_user})
        
        try:
            new_user = VendorUser.objects.create_user(
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                is_supervendor=is_supervendor,
            )
            messages.success(request, f'Vendor user "{email}" created successfully!')
            return redirect('vendor_user_list')
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
    
    return render(request, 'company/vendor_user_create.html', {'vendor_user': request.vendor_user})


@vendor_login_required
def vendor_user_edit(request, uuid):
    """Edit an existing vendor user"""
    user_to_edit = get_object_or_404(VendorUser, uuid=uuid)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        is_supervendor = request.POST.get('is_supervendor') == 'on'
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if not all([first_name, last_name]):
            messages.error(request, 'First name and last name are required.')
            return render(request, 'company/vendor_user_edit.html', {
                'vendor_user': request.vendor_user,
                'user_to_edit': user_to_edit,
            })
        
        # Update password if provided
        if new_password:
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'company/vendor_user_edit.html', {
                    'vendor_user': request.vendor_user,
                    'user_to_edit': user_to_edit,
                })
            user_to_edit.set_password(new_password)
        
        user_to_edit.first_name = first_name
        user_to_edit.last_name = last_name
        user_to_edit.phone_number = phone_number
        user_to_edit.is_supervendor = is_supervendor
        user_to_edit.save()
        
        messages.success(request, f'Vendor user "{user_to_edit.email}" updated successfully!')
        return redirect('vendor_user_list')
    
    context = {
        'vendor_user': request.vendor_user,
        'user_to_edit': user_to_edit,
    }
    return render(request, 'company/vendor_user_edit.html', context)


@vendor_login_required
def vendor_user_toggle_active(request, uuid):
    """Toggle vendor user active/inactive status"""
    user_to_toggle = get_object_or_404(VendorUser, uuid=uuid)
    
    # Prevent deactivating yourself
    if user_to_toggle.id == request.vendor_user.id:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('vendor_user_list')
    
    if request.method == 'POST':
        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save()
        status = "activated" if user_to_toggle.is_active else "deactivated"
        messages.success(request, f'Vendor user "{user_to_toggle.email}" has been {status}.')
    
    return redirect('vendor_user_list')


@vendor_login_required
def vendor_user_delete(request, uuid):
    """Delete a vendor user"""
    user_to_delete = get_object_or_404(VendorUser, uuid=uuid)
    
    # Prevent deleting yourself
    if user_to_delete.id == request.vendor_user.id:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('vendor_user_list')
    
    if request.method == 'POST':
        email = user_to_delete.email
        user_to_delete.delete()
        messages.success(request, f'Vendor user "{email}" has been deleted.')
    
    return redirect('vendor_user_list')


# ==================== COMPANY MANAGEMENT VIEWS ====================

@vendor_login_required
def company_list(request):
    companies = Company.objects.all()
    return render(request, 'company/company_list.html', {'companies': companies})


@vendor_login_required
def branch_list(request):
    # Vendor management - show ALL branches across all companies
    branches = Branch.objects.select_related('company').all().order_by('company__company_name', 'branch_name')
    return render(request, 'branch/branch_list.html', {'branches': branches})


@vendor_login_required
def company_detail(request, uuid):
    company = get_object_or_404(Company, uuid=uuid)
    return render(request, 'company/company_detail.html', {'company': company})


@vendor_login_required
def branch_detail(request, uuid):
    branch = get_object_or_404(Branch, uuid=uuid)
    return render(request, 'branch/branch_detail.html', {'branch': branch})


@vendor_login_required
def create_company(request):
    if request.method == "POST":
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('company_list')
    else:
        form = CompanyForm()
    return render(request, 'company/create_company.html', {'form': form})


from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Branch
from .forms import BranchForm
from django.contrib.auth import get_user_model
import random
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
User = get_user_model()




from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def sms_delivery_webhook(request):
    """Handle delivery reports from Termii"""
    try:
        data = json.loads(request.body)
        logger.info(f"Delivery webhook: {data}")
        
        # Update delivery status
        SmsDelivery.objects.filter(
            message_id=data.get('message_id')
        ).update(
            status=data.get('status', 'failed'),
            updated_at=timezone.now()
        )
        
        return JsonResponse({'status': 'received'})
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return JsonResponse({'status': 'error'}, status=400)



@login_required
def sms_troubleshoot(request):
    """View to help diagnose SMS issues"""
    deliveries = SmsDelivery.objects.filter(
        phone_number=request.user.phone_number
    ).order_by('-created_at')[:5]
    
    return render(request, 'sms_troubleshoot.html', {
        'deliveries': deliveries,
        'user_phone': request.user.phone_number
    })


from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Branch, SmsDelivery
from .forms import BranchForm
from django.contrib.auth import get_user_model
import random
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

import requests
import logging
from django.conf import settings
from .models import SmsDelivery  # Make sure SmsDelivery is correctly imported

logger = logging.getLogger(__name__)

def _send_otp_sms(phone_number, message, branch=None):
    """Send OTP via Termii API with debug print statements"""
    try:
        print(f"🔍 Starting OTP send to: {phone_number}")  # Debug

        if not phone_number or not phone_number.startswith('+'):
            print(f"❌ Invalid phone number format: {phone_number}")  # Debug
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

        print(f"📦 Payload being sent to Termii: {payload}")  # Debug

        response = requests.post(
            settings.TERMII_SMS_URL,
            json=payload,
            timeout=15
        )

        print(f"📬 HTTP response status: {response.status_code}")  # Debug

        try:
            response_data = response.json()
        except ValueError:
            response_data = {}
            print("❌ Failed to parse response JSON.")  # Debug

        print(f"📨 Response from Termii: {response_data}")  # Debug

        status = 'sent' if response_data.get('code') == 'ok' else 'failed'
        SmsDelivery.objects.create(
            branch=branch,
            phone_number=phone_number,
            message=message,
            status=status
        )
        print(f"✅ SMS delivery status saved as: {status}")  # Debug

        return response_data.get('code') == 'ok'

    except Exception as e:
        print(f"💥 Exception during OTP sending: {e}")  # Debug
        logger.error(f"SMS error: {str(e)}")

        SmsDelivery.objects.create(
            branch=branch,
            phone_number=phone_number,
            message=message,
            status='error'
        )
        return False




from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction
import random

from .forms import BranchForm
 # Update this if you use a different import
# @login_required
from django.shortcuts import render, redirect
from django.contrib import messages
import random
import logging
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.conf import settings
from .forms import BranchForm
from .models import Company
from accounts.utils import send_sms  # 👈 Termii SMS util

logger = logging.getLogger(__name__)


@vendor_login_required
def create_branch(request):
    try:
        print("🔍 Entered create_branch view")

        companies = Company.objects.all()
        print(f"✅ Companies fetched: {companies.count()}")

        if request.method == 'POST':
            print("📩 Received POST request")
            form = BranchForm(request.POST, request.FILES)

            if form.is_valid():
                print("✅ Form is valid")

                branch = form.save(commit=False)
                # Company is now selected from the form dropdown
                branch.company_name = branch.company.company_name
                branch.phone_verified = False
                branch.otp_code = str(random.randint(100000, 999999))
                branch.save()
                print(f"💾 Branch saved with ID: {branch.id}")

                # ------------------------------------------------------
                # ✅ Send Email
                # ------------------------------------------------------
                try:
                    subject = "🎉 Branch Registration Successful"
                    from_email = settings.DEFAULT_FROM_EMAIL
                    recipient_email = branch.company.email  

                    register_url = request.build_absolute_uri(reverse("register"))

                    text_content = f"""
Dear {branch.company.contact_person},

Your branch "{branch.branch_name}" has been successfully created under company "{branch.company.company_name}".

Branch Code: {branch.branch_code}
Contact Phone: {branch.company.contact_phone_no}
OTP Code: {branch.otp_code}

To complete setup, please register using the link below:
{register_url}

Thank you,
{branch.company.company_name}
"""

                    html_content = f"""
                    <html>
                    <body>
                        <h2>Branch Registration Successful 🎉</h2>
                        <p>Dear <strong>{branch.company.contact_person}</strong>,</p>
                        <p>Your branch has been successfully created.</p>

                        <p><strong>Branch Name:</strong> {branch.branch_name}</p>
                        <p><strong>Branch Code:</strong> {branch.branch_code}</p>
                        <p><strong>OTP Code:</strong> {branch.otp_code}</p>

                        <p style="margin-top:20px;">👉 Click below to complete registration:</p>
                        <a href="{register_url}"
                           style="display:inline-block; padding:12px 25px; background:#007bff; color:#fff; text-decoration:none;">
                           Complete Registration
                        </a>
                    </body>
                    </html>
                    """

                    msg = EmailMultiAlternatives(subject, text_content, from_email, [recipient_email])
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()

                    print("✅ Professional email sent successfully")
                except Exception as mail_error:
                    logger.exception("Email sending failed")
                    print(f"❌ Email sending failed: {mail_error}")
                    messages.warning(request, "Branch created, but email could not be sent.")

                # ------------------------------------------------------
                # ✅ Send SMS
                # ------------------------------------------------------
                try:
                    phone_number = branch.company.contact_phone_no
                    if phone_number:
                        sms_message = (
                            f"🎉 Branch '{branch.branch_name}' created under {branch.company.company_name}.\n"
                            f"Branch Code: {branch.branch_code}\n"
                            f"OTP: {branch.otp_code}\n"
                            f"Register here: {request.build_absolute_uri(reverse('register'))}"
                        )

                        print(f"[DEBUG-SMS] Sending SMS to {phone_number} with message: {sms_message}")
                        if send_sms(phone_number, sms_message):
                            print(f"📲 SMS sent successfully to {phone_number}")
                        else:
                            print(f"⚠️ SMS failed for {phone_number}")
                            messages.warning(request, "Branch created, but SMS could not be delivered.")
                    else:
                        print("⚠️ No phone number found for company, skipping SMS.")
                except Exception as sms_error:
                    logger.exception("SMS sending failed")
                    print(f"❌ SMS sending failed: {sms_error}")
                    messages.warning(request, "Branch created, but SMS could not be sent.")

                messages.success(request, "Branch created successfully. Notification sent via Email and SMS.")
                return redirect('branch_list')

            else:
                print("❌ Form is invalid")
                print(form.errors)
        else:
            print("📄 Received GET request, rendering form")
            form = BranchForm()

        return render(request, 'branch/create_branch.html', {'form': form, 'companies': companies})

    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        messages.error(request, "A system error occurred. Please contact support.")
        return redirect('create_branch')





        
# views.py
import threading
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Background function to send OTP via SMS and Email
def deliver_verification_otp_async(branch_id, otp, phone_number, email):
    """Send verification OTP to both phone and email in background"""
    print(f"[DEBUG-BG] 🚀 Starting async verification OTP delivery for branch {branch_id}")
    
    try:
        from .models import Branch  # Adjust import path as needed
        branch = Branch.objects.get(pk=branch_id)
        
        # Send SMS
        if phone_number:
            print(f"[DEBUG-BG] 📱 Sending verification SMS to {phone_number}")
            try:
                from .utils import _send_otp_sms  # Adjust import path as needed
                _send_otp_sms(phone_number, f"Your FinanceFlex branch verification code: {otp}", branch=branch)
                print(f"[DEBUG-BG] 📱 Verification SMS sent successfully")
            except Exception as e:
                logger.error(f"[DEBUG-BG] Verification SMS failed: {e}")
        
        # Send Email
        if email:
            print(f"[DEBUG-BG] 📧 Sending verification email to {email}")
            try:
                subject = "FinanceFlex Branch Phone Verification"
                html_content = render_to_string('branch/email/verification_otp_email.html', {
                    'branch': branch,
                    'otp': otp,
                    'user': branch.user  # Assuming branch has a user relationship
                })
                email_message = EmailMessage(
                    subject=subject,
                    body=html_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                )
                email_message.content_subtype = "html"
                email_message.send()
                print(f"[DEBUG-BG] 📧 Verification email sent successfully")
            except Exception as e:
                logger.error(f"[DEBUG-BG] Verification email failed: {e}")
                
        print(f"[DEBUG-BG] ✅ Async verification OTP delivery completed for branch {branch_id}")
        
    except Exception as e:
        logger.error(f"[DEBUG-BG] Verification OTP delivery error: {e}")

import random
import threading
from datetime import timedelta
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

@login_required
def verify_phone(request):
    user = request.user
    if not hasattr(user, "branch"):
        return redirect("create_branch")

    branch = user.branch

    # ✅ On GET, only generate OTP if not already set (avoid overwriting on refresh)
    if request.method == "GET" and not branch.otp_code:
        otp = str(random.randint(100000, 999999))
        branch.otp_code = otp
        branch.otp_generated_at = now()  # ✅ track timestamp for expiry
        branch.save()
        print(f"[DEBUG] Generated verification OTP: {otp} for branch {branch.id}")

        # Choose contact info
        phone_number = getattr(branch, "phone_number", None) or getattr(user, "phone_number", None)
        email = getattr(user, "email", None)

        # ✅ Send OTP in background thread
        thread = threading.Thread(
            target=deliver_verification_otp_async,
            args=(branch.id, otp, phone_number, email)
        )
        thread.daemon = True
        thread.start()
        print("[DEBUG] 🚀 Verification OTP delivery initiated")

    # ✅ On POST, verify OTP
    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        print(f"[DEBUG] Entered OTP: {entered_otp}, Stored OTP: {branch.otp_code}")

        # Optional: enforce expiry (5 minutes)
        otp_valid = True
        if hasattr(branch, "otp_generated_at") and branch.otp_generated_at:
            if now() > branch.otp_generated_at + timedelta(minutes=5):
                otp_valid = False

        if otp_valid and entered_otp == branch.otp_code:
            branch.phone_verified = True
            branch.otp_code = None  # ✅ clear OTP
            branch.otp_generated_at = None
            branch.save()
            messages.success(request, "Phone verification successful!")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid or expired OTP. Please try again.")

    return render(request, "branch/verify_phone.html")


from django.core.mail import send_mail

@login_required
def resend_otp_branch(request):
    user = request.user

    if not hasattr(user, "branch"):
        return redirect('create_branch')

    branch = user.branch

    # Generate OTP
    new_otp = str(random.randint(100000, 999999))
    branch.otp_code = new_otp
    branch.save()

    # Send email
    send_mail(
        subject="Your OTP Code",
        message=f"Your OTP is {new_otp}",
        from_email=settings.DEFAULT_FROM_EMAIL, # or settings.DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
        fail_silently=False,
    )

    messages.success(request, "A new OTP has been sent to your email.")
    return redirect("verify_phone")



def create_branch_old(request):
    companies = Company.objects.all()
    if request.method == "POST":
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('branch_list')  # Redirect to the company list page
    else:
        form = BranchForm()
    return render(request, 'branch/create_branch.html', {'form': form, 'companies' : companies})



@vendor_login_required
def update_company(request, uuid):
    company = get_object_or_404(Company, uuid=uuid)
    if request.method == "POST":
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            return redirect('company_list')
    else:
        form = CompanyForm(instance=company)
    return render(request, 'company/update_company.html', {'form': form, 'company': company})


@vendor_login_required
def update_branch(request, uuid):
    # Get the branch object to update
    branch = get_object_or_404(Branch, uuid=uuid)
    
    # Get all companies for the dropdown
    companies = Company.objects.all()

    # If the request is POST, update the branch and company
    if request.method == "POST":
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            updated_branch = form.save(commit=False)
            updated_branch.save()  # Save the updated branch information
            
            return redirect('branch_list')  # Redirect to the list view after saving
    else:
        form = BranchForm(instance=branch)
    
    # Render the form with the existing branch data and companies
    return render(request, 'branch/update_branch.html', {
        'form': form,
        'branch': branch,
        'companies': companies  # Pass companies for the dropdown
    })





@vendor_login_required
def company_delete(request, uuid):
    company = get_object_or_404(Company, uuid=uuid)
    if request.method == 'POST':
        try:
            company.delete()
            messages.success(request, f"Company '{company.company_name}' deleted successfully.")
            return redirect('company_list')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('company_list')
    return render(request, 'company/company_confirm_delete.html', {'company': company})


@vendor_login_required
def branch_delete(request, uuid):
    branch = get_object_or_404(Branch, uuid=uuid)
    if request.method == 'POST':
        try:
            branch.delete()
            messages.success(request, f"Branch '{branch.branch_name}' deleted successfully.")
            return redirect('branch_list')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('branch_list')
    return render(request, 'branch/branch_confirm_delete.html', {'branch': branch})

from .forms import EndSession


from django.utils import timezone
@login_required(login_url='login')
@user_passes_test(check_role_admin)
@login_required

def session_mgt(request, uuid=None):
    # Get the branch — ensure user has access (optional security check)
    branch = get_object_or_404(Branch, uuid=uuid) if uuid else request.user.branch

    # Optional: Restrict access to user's own branch (recommended)
    if hasattr(request.user, 'branch') and request.user.branch_id != str(branch.id):
        messages.error(request, "You do not have permission to manage this branch's session.")
        return redirect('dashboard')  # or another safe page

    if request.method == 'POST':
        form = EndSession(request.POST, instance=branch)
        if form.is_valid():
            session_status = form.cleaned_data.get('session_status')
            if session_status == 'Open':
                # Assuming system_date_date is a DateField
                branch.system_date_date = timezone.now().date()
            form.save()
            messages.success(request, 'Session updated successfully.')
            # ✅ Redirect with uuid to match URL pattern
            return redirect('session_mgt', uuid=branch.uuid)
    else:
        form = EndSession(instance=branch)

    return render(request, 'company/session_mgt.html', {
        'form': form,
        'branch': branch
    })





from django.contrib.auth import get_user_model
from django.shortcuts import render

def display_users_and_branches(request):
    # Get the custom User model
    User = get_user_model()  
    
    # Fetch all users
    users = User.objects.all()

    # Pass the user data to the template
    return render(request, 'users/display_users_and_branches.html', {'users': users})


@vendor_login_required
def create_branch_admin(request, uuid):
    """
    Create an administrator user for a specific branch.
    This allows new branches to have their own admin who can then create other users.
    """
    User = get_user_model()
    branch = get_object_or_404(Branch, uuid=uuid)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        cashier_gl = request.POST.get('cashier_gl', '').strip() or None
        cashier_ac = request.POST.get('cashier_ac', '').strip() or None
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('create_branch_admin', uuid=uuid)
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('create_branch_admin', uuid=uuid)
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('create_branch_admin', uuid=uuid)
        
        try:
            # Create admin user for this branch
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                phone_number=phone_number,
                cashier_gl=cashier_gl,
                cashier_ac=cashier_ac,
                password=password,
                role=1,  # System Administrator
                branch_id=str(branch.id),
            )
            user.is_active = True
            user.is_staff = True
            user.verified = True
            user.save()
            
            messages.success(request, f'Administrator "{username}" created successfully for branch "{branch.branch_name}"!')
            return redirect('branch_list')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('create_branch_admin', uuid=uuid)
    
    context = {
        'branch': branch,
    }
    return render(request, 'branch/create_branch_admin.html', context)


@vendor_login_required
def edit_branch_admin(request, uuid):
    """
    Edit the super user (administrator) for a specific branch.
    Allows vendor to update the branch admin including cashier_gl and cashier_ac fields.
    """
    User = get_user_model()
    branch = get_object_or_404(Branch, uuid=uuid)
    
    # Find the branch admin (System Administrator with role=1 for this branch)
    branch_admin = User.objects.filter(branch_id=str(branch.id), role=1).first()
    
    if not branch_admin:
        messages.error(request, f'No administrator found for branch "{branch.branch_name}". Please create one first.')
        return redirect('create_branch_admin', uuid=uuid)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        cashier_gl = request.POST.get('cashier_gl', '').strip() or None
        cashier_ac = request.POST.get('cashier_ac', '').strip() or None
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        # Validate email uniqueness (excluding current user)
        if User.objects.filter(email=email).exclude(id=branch_admin.id).exists():
            messages.error(request, 'Email already exists for another user.')
            return redirect('edit_branch_admin', uuid=uuid)
        
        # Validate password if provided
        if new_password:
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return redirect('edit_branch_admin', uuid=uuid)
            branch_admin.set_password(new_password)
        
        try:
            branch_admin.first_name = first_name
            branch_admin.last_name = last_name
            branch_admin.email = email
            branch_admin.phone_number = phone_number
            branch_admin.cashier_gl = cashier_gl
            branch_admin.cashier_ac = cashier_ac
            branch_admin.save()
            
            messages.success(request, f'Administrator "{branch_admin.username}" updated successfully!')
            return redirect('branch_list')
            
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
            return redirect('edit_branch_admin', uuid=uuid)
    
    context = {
        'branch': branch,
        'branch_admin': branch_admin,
    }
    return render(request, 'branch/edit_branch_admin.html', context)


@vendor_login_required
def toggle_branch_active(request, uuid):
    """Toggle branch active/inactive status for subscription management"""
    branch = get_object_or_404(Branch, uuid=uuid)
    if request.method == 'POST':
        branch.is_active = not branch.is_active
        branch.save()
        status = "activated" if branch.is_active else "deactivated"
        messages.success(request, f'Branch "{branch.branch_name}" has been {status}.')
    return redirect('branch_list')


# ==================== BRANCH SUPERUSER MANAGEMENT (VENDOR) ====================

@vendor_login_required
def branch_superuser_list(request):
    """
    List all branches with their superusers (System Administrators).
    Allows vendor to see and manage all branch admins.
    """
    User = get_user_model()
    branches = Branch.objects.select_related('company').all().order_by('company__company_name', 'branch_name')
    
    branches_data = []
    for branch in branches:
        superusers = User.objects.filter(
            branch_id=str(branch.id),
            role=1  # System Administrator
        )
        user_count = User.objects.filter(branch_id=str(branch.id)).count()
        
        branches_data.append({
            'branch': branch,
            'superusers': superusers,
            'superuser_count': superusers.count(),
            'total_users': user_count,
        })
    
    context = {
        'vendor_user': request.vendor_user,
        'branches_data': branches_data,
    }
    return render(request, 'company/branch_superuser_list.html', context)


@vendor_login_required
def branch_superuser_detail(request, uuid):
    """
    View and manage all superusers for a specific branch.
    """
    User = get_user_model()
    branch = get_object_or_404(Branch, uuid=uuid)
    
    superusers = User.objects.filter(
        branch_id=str(branch.id),
        role=1  # System Administrator
    )
    
    context = {
        'vendor_user': request.vendor_user,
        'branch': branch,
        'superusers': superusers,
    }
    return render(request, 'company/branch_superuser_detail.html', context)


@vendor_login_required
def branch_superuser_edit(request, branch_uuid, user_uuid):
    """
    Edit a specific superuser for a branch.
    """
    User = get_user_model()
    branch = get_object_or_404(Branch, uuid=branch_uuid)
    user_to_edit = get_object_or_404(User, uuid=user_uuid, branch_id=str(branch.id))
    
    if request.method == 'POST':
        user_to_edit.first_name = request.POST.get('first_name', user_to_edit.first_name)
        user_to_edit.last_name = request.POST.get('last_name', user_to_edit.last_name)
        user_to_edit.email = request.POST.get('email', user_to_edit.email)
        user_to_edit.phone_number = request.POST.get('phone_number', user_to_edit.phone_number)
        user_to_edit.cashier_gl = request.POST.get('cashier_gl', '').strip() or None
        user_to_edit.cashier_ac = request.POST.get('cashier_ac', '').strip() or None
        user_to_edit.is_active = request.POST.get('is_active') == 'on'
        
        new_role = request.POST.get('role')
        if new_role:
            user_to_edit.role = int(new_role)
        
        new_password = request.POST.get('new_password', '').strip()
        if new_password:
            confirm_password = request.POST.get('confirm_password', '').strip()
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return redirect('branch_superuser_edit', branch_uuid=branch_uuid, user_uuid=user_uuid)
            user_to_edit.set_password(new_password)
        
        user_to_edit.save()
        messages.success(request, f'User {user_to_edit.username} updated successfully.')
        return redirect('branch_superuser_detail', uuid=branch_uuid)
    
    # Get role choices from User model
    ROLE_CHOICES = [
        (1, 'System Administration'),
        (2, 'General Manager'),
        (3, 'Branch Manager'),
        (4, 'Assistant Manager'),
        (5, 'Accountant'),
        (6, 'Accounts Assistant'),
        (7, 'Credit Supervisor'),
        (8, 'Credit Officer'),
        (9, 'Verification Officer'),
        (10, 'Customer Service Unit'),
        (11, 'Teller'),
        (12, 'Management Information System'),
    ]
    
    context = {
        'vendor_user': request.vendor_user,
        'branch': branch,
        'edit_user': user_to_edit,
        'role_choices': ROLE_CHOICES,
    }
    return render(request, 'company/branch_superuser_edit.html', context)


@vendor_login_required
def branch_superuser_toggle(request, branch_uuid, user_uuid):
    """
    Toggle the active status of a superuser.
    """
    User = get_user_model()
    branch = get_object_or_404(Branch, uuid=branch_uuid)
    user_to_toggle = get_object_or_404(User, uuid=user_uuid, branch_id=str(branch.id))
    
    if request.method == 'POST':
        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save()
        
        status = 'activated' if user_to_toggle.is_active else 'deactivated'
        messages.success(request, f'User {user_to_toggle.username} has been {status}.')
    
    return redirect('branch_superuser_detail', uuid=branch_uuid)
