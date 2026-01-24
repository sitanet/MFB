"""
User Views for Multi-Database Architecture

This module contains views for user management.
Branch models are imported from company.models (vendor database).
Users are stored in client database but reference branches by ID.
"""

import datetime
import threading
import random
import logging
from random import randint

from django.contrib.auth.tokens import default_token_generator
from django.core.mail import message, EmailMultiAlternatives, send_mail
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
from django.contrib import messages, auth
from django.contrib.auth import authenticate, login as auth_login, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum, Count
from decimal import Decimal
from functools import wraps

# Import models from correct locations for multi-database architecture
from company.models import Company, Branch  # Vendor database
from .forms import UserForm, UserProfileForm, UserProfilePictureForm, EdituserForm
from .models import Role, User, UserProfile, RolePermission  # Client database
from accounts_admin.models import Account, Category  # Client database
from customers.models import Customer  # Client database
from transactions.models import Memtrans  # Client database
from loans.models import Loans  # Client database

# Import utilities
from accounts.utils import detectUser, send_verification_email
from .utils import send_sms

logger = logging.getLogger(__name__)
User = get_user_model()


# ==================== HELPER FUNCTIONS ====================

def get_branch_from_vendor_db(branch_id):
    """Helper function to get branch from database"""
    if not branch_id:
        return None
    try:
        return Branch.objects.get(id=branch_id)
    except Branch.DoesNotExist:
        return None


def get_all_branches_from_vendor_db():
    """Helper function to get all branches from database"""
    return Branch.objects.all()


def get_company_from_vendor_db(company_id):
    """Helper function to get company from database"""
    if not company_id:
        return None
    try:
        return Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        return None


def get_user_branches_from_vendor_db(user):
    """Get branches accessible to user based on their company"""
    if not user.branch_id:
        return get_all_branches_from_vendor_db()
    
    user_branch = get_branch_from_vendor_db(user.branch_id)
    if user_branch and user_branch.company:
        return Branch.objects.filter(company=user_branch.company)
    
    return get_all_branches_from_vendor_db()


# ==================== ROLE CHECKING FUNCTIONS ====================

def check_role_admin(user):
    """Check if user has admin role (System Administrator - role 1) or any authenticated staff"""
    if not user.is_authenticated:
        return False
    # Allow System Administrator (role 1) or any user with a valid staff role (1-12)
    if user.role is not None and user.role >= 1 and user.role <= 12:
        return True
    return False


def check_role_system_admin(user):
    """Check if user is System Administrator (role 1) - only they can manage users"""
    if not user.is_authenticated:
        return False
    return user.role == 1


def check_role_coordinator(user):
    """Check if user has coordinator role"""
    if user.role == 2:
        return True
    else:
        raise PermissionDenied


def check_role_team_member(user):
    """Check if user has team member role"""
    if user.role == 3:
        return True
    else:
        raise PermissionDenied


def check_role_customer(user):
    """Check if user has customer role"""
    if user.role == 13:
        return True
    else:
        return False


def check_role_vendor(user):
    """Check if user has vendor role"""
    if user.role == 2:
        return True
    else:
        return False


# ==================== USER REGISTRATION VIEWS ====================

@login_required(login_url='login')
@user_passes_test(check_role_system_admin)
def registerUser(request):
    """Register a new user with multi-database support - Only System Administrator can access"""
    # Get allowed branches based on user's company
    allowed_branches = get_user_branches_from_vendor_db(request.user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES)
        # Set queryset to use vendor database
        form.fields['branch'].queryset = allowed_branches

        if form.is_valid():
            user = form.save(commit=False)
            
            # Get selected branch from form
            branch = form.cleaned_data.get('branch')
            if branch:
                user.branch_id = str(branch.id)
            elif allowed_branches.count() == 1:
                # Auto-assign if only one branch available
                user.branch_id = str(allowed_branches.first().id)

            # Set optional cashier fields
            user.cashier_gl = form.cleaned_data.get('cashier_gl') or None
            user.cashier_ac = form.cleaned_data.get('cashier_ac') or None

            # Set user as inactive until email is verified
            user.is_active = False
            user.save()
            
            # Send verification email
            mail_subject = 'Please activate your account'
            email_template = 'accounts/email/accounts_verification_email.html'
            try:
                send_verification_email(request, user, mail_subject, email_template)
                messages.success(request, f'User {user.username} registered successfully! A verification email has been sent to {user.email}.')
            except Exception as e:
                messages.warning(request, f'User {user.username} registered but failed to send verification email: {str(e)}')
            
            return redirect('display_all_user')
        else:
            messages.error(request, 'There were errors in the form.')
            print(form.errors)
    else:
        form = UserForm()
        form.fields['branch'].queryset = allowed_branches

        # Auto-select branch if user has only one available
        if allowed_branches.count() == 1:
            form.initial['branch'] = allowed_branches.first().id

    context = {
        'form': form,
        'branches': allowed_branches,
    }
    return render(request, 'accounts/registeruser.html', context)


# Alias for compatibility
registeruser = registerUser


def register(request):
    """Public user registration with OTP verification"""
    print("🔍 Entered register view")

    if User.objects.exists():
        print("⚠️ User already exists. Showing message on registration page.")
        messages.error(request, "A user already exists. Multiple users are not allowed.")
        return render(request, "accounts/public_reg.html", {"form": None})

    if request.method == "POST":
        print("📩 Received POST request with data:", request.POST.dict())
        form = UserForm(request.POST)

        if form.is_valid():
            print("✅ Form is valid")
            user = form.save(commit=False)
            
            # Handle branch assignment
            branch = form.cleaned_data.get('branch')
            if branch:
                user.branch_id = str(branch.id)
            
            user.set_password(form.cleaned_data["password"])

            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
            user.otp_code = otp_code
            user.last_otp_sent = timezone.now()
            user.save()
            
            print(f"👤 User created: {user.username}, email: {user.email}, OTP: {otp_code}")

            # Send Email OTP
            try:
                subject = "Your OTP Code"
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [user.email]

                # Get company name for email
                user_branch = get_branch_from_vendor_db(user.branch_id)
                company_name = user_branch.company.company_name if user_branch and user_branch.company else "FinanceFlex"

                text_content = f"""
Hi {user.first_name},

Your account has been created successfully.
Here is your OTP code: {otp_code}

Verify your account:
http://127.0.0.1:8000/accounts/user_verify_otp/

Thank you!
"""

                html_content = f"""
                <html>
                <body>
                    <p>Hi {user.first_name},</p>
                    <p>Your account has been created successfully.</p>
                    <p><strong>Your OTP Code:</strong> {otp_code}</p>
                    <a href="http://127.0.0.1:8000/accounts/user_verify_otp/"
                       style="display:inline-block; padding:10px 20px; background:#28a745; color:#fff; text-decoration:none;">
                       Verify Account
                    </a>
                    <p>Thank you,<br>{company_name}</p>
                </body>
                </html>
                """

                msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                print(f"📧 OTP email sent to {user.email}")
            except Exception as e:
                print(f"❌ Email sending failed: {e}")
                messages.warning(request, "User created, but failed to send OTP email.")

            # Send SMS OTP
            try:
                if user.phone_number:
                    sms_message = f"Hi {user.first_name}, your OTP is {otp_code}. Verify at: http://127.0.0.1:8000/accounts/user_verify_otp/"
                    print(f"[DEBUG-SMS] Sending OTP SMS to {user.phone_number}: {sms_message}")
                    if send_sms(user.phone_number, sms_message):
                        print(f"📲 SMS sent successfully to {user.phone_number}")
                    else:
                        print(f"⚠️ SMS sending failed for {user.phone_number}")
                        messages.warning(request, "OTP email sent, but SMS failed.")
                else:
                    print("⚠️ User has no phone number, skipping SMS.")
            except Exception as sms_err:
                print(f"❌ SMS error: {sms_err}")
                messages.warning(request, "User created, but failed to send OTP SMS.")

            messages.success(request, "User registered successfully. OTP sent via Email & SMS.")
            return redirect("register")
        else:
            print("❌ Form is invalid:", form.errors)
    else:
        print("📄 Received GET request")
        form = UserForm()

    return render(request, "accounts/public_reg.html", {"form": form})


def registerusermasterintelligent(request):
    """Master intelligent user registration"""
    companies = Company.objects.all()
    
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            phone_number = form.cleaned_data['phone_number']
            role = form.cleaned_data['role']
            branch = form.cleaned_data['branch']
            cashier_gl = form.cleaned_data['cashier_gl']
            cashier_ac = form.cleaned_data['cashier_ac']

            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                role=role,
                phone_number=phone_number,
                branch_id=str(branch.id),
                cashier_gl=cashier_gl,
                cashier_ac=cashier_ac,
                password=password
            )
            
            user.save()
            messages.success(request, 'You have successfully registered User')
            return redirect('display_all_user')
        else:
            print('invalid form')
            print(form.errors)
    else:
        form = UserForm()
        
    context = {
        'form': form,
        'companies': companies,
    }
    return render(request, 'accounts/registerusermasterintelligent.html', context)


# ==================== OTP VERIFICATION VIEWS ====================

def user_verify_otp(request):
    """Verify OTP for user registration"""
    print("🔍 Entered user_verify_otp view")

    user = User.objects.first()
    if not user:
        print("❌ No user found")
        messages.error(request, "No registered user found. Please register first.")
        return redirect("register")

    # Calculate resend availability
    can_resend = False
    countdown_seconds = 30
    if user.last_otp_sent:
        elapsed = (timezone.now() - user.last_otp_sent).total_seconds()
        if elapsed >= 30:
            can_resend = True
        else:
            countdown_seconds = int(30 - elapsed)
    else:
        can_resend = True

    if request.method == "POST":
        otp = request.POST.get("otp")
        print(f"📝 OTP entered: {otp}")

        if user.is_otp_valid(otp):
            print("✅ OTP is valid")
            user.verified = True
            user.save()
            messages.success(request, "OTP verified successfully. You can now log in.")
            return redirect("login")
        else:
            print("❌ Invalid OTP")
            messages.error(request, "OTP is invalid or expired.")

    return render(request, "accounts/user_verify_otp.html", {
        "can_resend": can_resend,
        "countdown_seconds": countdown_seconds,
    })


def user_resend_otp(request):
    """Resend OTP for user verification"""
    print("🔍 Entered user_resend_otp view")

    try:
        user = User.objects.first()
        if not user:
            print("❌ No registered user found")
            messages.error(request, "No registered user found. Please register first.")
            return redirect("register")

        otp_code = str(random.randint(100000, 999999))
        user.otp_code = otp_code
        user.last_otp_sent = timezone.now()
        user.save()
        print(f"🆕 New OTP for {user.email}: {otp_code}")

        # Get branch and company info for email
        user_branch = get_branch_from_vendor_db(user.branch_id)
        company_name = user_branch.company.company_name if user_branch and user_branch.company else "FinanceFlex"

        # Send Email
        try:
            subject = "Your New OTP Code"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]

            text_content = f"Hi {user.first_name},\nYour new OTP is: {otp_code}\n\nVerify at: http://127.0.0.1:8000/accounts/user_verify_otp/"
            html_content = f"""
            <html><body>
                <p>Hi {user.first_name},</p>
                <p>Your new OTP is <strong>{otp_code}</strong></p>
                <a href="http://127.0.0.1:8000/accounts/user_verify_otp/"
                   style="padding:10px 20px; background:#28a745; color:#fff; text-decoration:none;">Verify Account</a>
                <p>Thank you,<br>{company_name}</p>
            </body></html>
            """

            msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            print(f"📧 Resent OTP email to {user.email}")
        except Exception as e:
            print(f"❌ Failed to resend OTP email: {e}")
            messages.warning(request, "OTP email could not be sent.")

        # Send SMS
        try:
            if user.phone_number:
                sms_message = f"Hi {user.first_name}, your new OTP is {otp_code}. Verify at: http://127.0.0.1:8000/accounts/user_verify_otp/"
                print(f"[DEBUG-SMS] Sending new OTP SMS to {user.phone_number}: {sms_message}")
                if send_sms(user.phone_number, sms_message):
                    print(f"📲 SMS resent successfully to {user.phone_number}")
                else:
                    print(f"⚠️ SMS resend failed for {user.phone_number}")
                    messages.warning(request, "OTP email sent, but SMS failed.")
            else:
                print("⚠️ User has no phone number, skipping SMS.")
        except Exception as sms_err:
            print(f"❌ SMS resend error: {sms_err}")
            messages.warning(request, "OTP resend failed via SMS.")

        messages.success(request, f"A new OTP has been sent to {user.email} and phone.")
    except Exception as e:
        print(f"❌ Resend OTP error: {e}")
        messages.error(request, "An error occurred while resending OTP.")

    return redirect("user_verify_otp")


# Alias for URL compatibility
resend_otp = user_resend_otp


# ==================== AUTHENTICATION VIEWS ====================

def _send_otp_background(user_id, otp, phone_number, email, branch):
    """Send OTP via SMS and Email in background thread"""
    print(f"[DEBUG-BG] 🚀 Background OTP delivery started for user {user_id}")
    print(f"[DEBUG-BG] Phone: {phone_number}, Email: {email}, OTP: {otp}")
    
    try:
        # Send SMS
        if phone_number:
            try:
                sms_message = f"Your OTP code is: {otp}"
                if send_sms(phone_number, sms_message, branch=branch):
                    print(f"[SMS] ✅ OTP sent to {phone_number}")
                else:
                    print(f"[SMS] ⚠️ Failed to send OTP to {phone_number}")
            except Exception as sms_exc:
                print(f"[DEBUG-BG][SMS] Exception: {sms_exc}")

        # Send Email
        if email:
            try:
                company_name = getattr(branch, "company_name", "Support Team") if branch else "Support Team"
                subject = "Your OTP Code"
                text_content = f"Hi,\n\nYour OTP code is: {otp}\n\nPlease verify your account."
                html_content = f"""
                <html>
                <body>
                    <p>Hi,</p>
                    <p>Your OTP code is: <strong>{otp}</strong></p>
                    <p>Verify your account <a href='http://127.0.0.1:8000/accounts/verify_otp/'>here</a>.</p>
                    <p>Thank you,<br>{company_name}</p>
                </body>
                </html>
                """

                msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                print(f"[EMAIL] ✅ OTP sent to {email}")
            except Exception as email_exc:
                print(f"[DEBUG-BG][EMAIL] Exception: {email_exc}")

        print("[DEBUG-BG] ✅ Background OTP delivery completed")
    except Exception as e:
        print(f"[DEBUG-BG] ⚠️ Background error: {e}")


def login(request):
    """Login view with OTP verification"""
    print("\n[DEBUG] ───────────────────────────────")
    print("[DEBUG] Login request received")

    if request.user.is_authenticated:
        print("[DEBUG] User already authenticated → redirecting to myAccount")
        return redirect('myAccount')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')

        print(f"[DEBUG] POST data received → email='{email}', password_provided={bool(password)}")

        if not email or not password:
            print("[DEBUG] Missing email or password")
            messages.error(request, "Email and password are required.")
            return render(request, 'accounts/login.html')

        try:
            # Check if email exists
            try:
                db_user = User.objects.get(email=email)
                print(f"[DEBUG] Email found → user_id={db_user.id}")
            except User.DoesNotExist:
                print(f"[DEBUG] Email '{email}' does NOT exist")
                messages.error(request, "No account was found with this email.")
                return redirect('login')

            # Try authentication
            user = authenticate(request, email=email, password=password)
            if user is None:
                print("[DEBUG] Authentication FAILED")
                messages.error(request, "Incorrect password. Please try again.")
                return redirect('login')

            user.backend = 'accounts.backends.EmailBackend'
            # DON'T login here - wait until OTP is verified
            # auth.login(request, user)  # REMOVED - security fix
            print(f"[DEBUG] Authentication SUCCESS → user_id={user.id}")

            # Account verification check
            if not getattr(user, "verified", False):
                print(f"[DEBUG] User {user.id} NOT verified")
                messages.error(request, "Your account has not been verified. Please contact support.")
                return redirect('login')

            # Branch license check
            user_branch = get_branch_from_vendor_db(user.branch_id)
            if user_branch and user_branch.expire_date < timezone.now().date():
                print(f"[DEBUG] Branch license EXPIRED for branch {user_branch.id}")
                messages.error(request, "Your branch license has expired. Contact your administrator.")
                return redirect('login')

            # Generate OTP
            otp = randint(100000, 999999)
            print(f"[DEBUG] Generated OTP → {otp}")

            # Store OTP in session (user NOT logged in yet - will login after OTP verified)
            request.session['otp_data'] = {
                'user_id': user.id,
                'otp': otp,
                'timestamp': timezone.now().isoformat(),
                'backend': user.backend  # Store backend for login after OTP
            }

            # Send OTP in background
            kwargs = {
                'user_id': user.id,
                'otp': otp,
                'phone_number': getattr(user, 'phone_number', None),
                'email': getattr(user, 'email', None),
                'branch': user_branch
            }

            print("[DEBUG] Starting background OTP thread")
            thread = threading.Thread(target=_send_otp_background, kwargs=kwargs)
            thread.daemon = True
            thread.start()

            messages.success(request, "OTP sent! Please check your phone and email.")
            return redirect('verify_otp')

        except Exception as e:
            print(f"[DEBUG] EXCEPTION: {str(e)}")
            logger.exception(f"Login failed for {email}: {str(e)}")
            messages.error(request, "A system error occurred. Please try again.")
            return redirect('login')

    return render(request, 'accounts/login.html')


# Alias for compatibility
login_view = login


def verify_otp(request):
    """Verify OTP after login"""
    # Ensure session data is present
    if 'otp_data' not in request.session:
        messages.error(request, "OTP session expired. Please log in again.")
        return redirect('login')

    otp_data = request.session['otp_data']
    user_id = otp_data.get('user_id')
    session_otp = otp_data.get('otp')

    # Fetch user
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('login')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        action = request.POST.get('action')

        # Handle OTP resend
        if action == "resend":
            new_otp = randint(100000, 999999)
            request.session['otp_data']['otp'] = new_otp
            cache.set(f'otp_{user_id}', new_otp, timeout=300)

            # Send SMS
            if getattr(user, "phone_number", None):
                message_text = f"Your OTP code is {new_otp}. It will expire in 5 minutes."
                send_sms(user.phone_number, message_text)

            messages.success(request, "A new OTP has been sent to your phone.")
            return redirect('verify_otp')

        # Check cache and session OTP
        cache_otp = cache.get(f'otp_{user_id}')
        
        # Validate OTP
        if entered_otp and (str(entered_otp) == str(session_otp) or str(entered_otp) == str(cache_otp)):
            # Set the backend before login (required by Django)
            user.backend = otp_data.get('backend', 'accounts.backends.EmailBackend')
            auth.login(request, user)
            
            # Cleanup
            cache.delete(f'otp_{user_id}')
            request.session.pop('otp_data', None)
            
            messages.success(request, "Logged in successfully!")
            return redirect('myAccount')
        else:
            messages.error(request, "Invalid OTP.")

    return render(request, 'accounts/verify_otp.html', {"user": user})


def logout(request):
    """User logout"""
    auth.logout(request)
    return redirect('login')


# ==================== ACCOUNT MANAGEMENT VIEWS ====================

@login_required(login_url='login')
def myAccount(request):
    """User account redirect based on role"""
    user = request.user
    redirectUrl = detectUser(user)
    return redirect(redirectUrl)


@login_required(login_url='login')
def profile(request):
    """User profile management"""
    if request.method == 'POST':
        form = UserProfilePictureForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile picture updated successfully.')
            return redirect('profile')
    else:
        form = UserProfilePictureForm(instance=request.user)
    
    # Get user's branch information
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    
    context = {
        'form': form,
        'user_branch': user_branch,
    }
    return render(request, 'accounts/profile.html', context)


# ==================== USER MANAGEMENT VIEWS ====================

@login_required(login_url='login')
@user_passes_test(check_role_system_admin)
def users(request):
    """Display all users for admin with branch information - Only System Administrator can access"""
    # Get user's branch and company information
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    
    if user_branch and user_branch.company:
        # Filter users by same company
        company_branches = Branch.objects.filter(company=user_branch.company)
        branch_ids = [str(branch.id) for branch in company_branches]
        users_list = User.objects.filter(branch_id__in=branch_ids)
    else:
        # Admin can see all users
        users_list = User.objects.all()

    # Add branch information to each user
    users_with_branch_info = []
    for user in users_list:
        branch = get_branch_from_vendor_db(user.branch_id)
        user.branch_display = branch.branch_name if branch else "No Branch"
        user.company_display = branch.company.company_name if branch and branch.company else "No Company"
        users_with_branch_info.append(user)

    context = {
        'users': users_with_branch_info,
    }
    return render(request, 'accounts/display_all_user.html', context)


# Alias for compatibility
display_all_user = users


@login_required(login_url='login')
@user_passes_test(check_role_system_admin)
def editUser(request, uuid=None):
    """Edit user with multi-database branch support - Only System Administrator can access"""
    user = get_object_or_404(User, uuid=uuid)
    
    # Get allowed branches based on current user's company
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    if user_branch and user_branch.company:
        allowed_branches = Branch.objects.filter(company=user_branch.company)
    else:
        allowed_branches = get_all_branches_from_vendor_db()
    
    # Get customers for the form
    customers = Customer.objects.filter(gl_no__startswith='1')
    
    # Get chart of accounts for cashier GL dropdown
    accounts = Account.objects.filter(branch=request.user.branch)
 
    if request.method == 'POST':
        form = EdituserForm(request.POST, request.FILES, instance=user)
        form.fields['branch'].queryset = allowed_branches
        
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('display_all_user')
    else:
        form = EdituserForm(instance=user)
        form.fields['branch'].queryset = allowed_branches

    context = {
        'form': form,
        'user': user,
        'branch': allowed_branches,
        'customers': customers,
        'accounts': accounts,
    }
    return render(request, 'accounts/update_user.html', context)


# Alias for compatibility
edit_user = editUser


@login_required(login_url='login')
@user_passes_test(check_role_system_admin)
def deleteUser(request, uuid=None):
    """Delete a user - Only System Administrator can access"""
    user = get_object_or_404(User, uuid=uuid)
    user.delete()
    messages.success(request, 'User deleted successfully!')
    return redirect('display_all_user')


@login_required(login_url='login')
@user_passes_test(check_role_system_admin)
def verify_user(request, uuid=None):
    """Admin verifies a user account - Only System Administrator can access"""
    user = get_object_or_404(User, uuid=uuid)
    user.verified = True
    user.is_active = True
    user.save()
    messages.success(request, f'User {user.username} has been verified successfully!')
    return redirect('display_all_user')


# Alias for compatibility - also protected
@login_required(login_url='login')
@user_passes_test(check_role_system_admin)
def delete_user(request, uuid):
    """Delete user by UUID (compatibility function) - Only System Administrator can access"""
    user = User.objects.get(uuid=uuid)
    user.delete()
    messages.success(request, 'User deleted successfully!')
    return redirect('display_all_user')


# ==================== DASHBOARD VIEW ====================

@login_required(login_url='login')
def dashboard(request):
    """Role-based dashboard - each role sees only relevant data"""
    today = timezone.now()
    current_month = today.month
    current_year = today.year

    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    user_company = user_branch.company if user_branch else None
    user_role = request.user.role
    try:
        user_branch_id = int(request.user.branch_id) if request.user.branch_id else None
    except (ValueError, TypeError):
        user_branch_id = None

    # Role-based access levels:
    # Level 1: Company-wide (System Admin=1, General Manager=2)
    # Level 2: Branch-wide (Branch Manager=3, Assistant Manager=4, Accountant=5)
    # Level 3: Department/Personal (Credit roles=7,8, Teller=11, CSU=10, etc.)
    
    if user_role in [1, 2] and user_company:
        # System Admin & General Manager see company-wide data
        company_branches = Branch.objects.filter(company=user_company)
        branch_ids = [b.id for b in company_branches]
        access_level = 'company'
    elif user_role in [3, 4, 5, 6, 12]:
        # Branch Manager, Asst Manager, Accountant, Accounts Asst, MIS - see branch data
        branch_ids = [user_branch_id] if user_branch_id else []
        access_level = 'branch'
    else:
        # Credit Officers, Tellers, CSU, Verification - see only their own data
        branch_ids = [user_branch_id] if user_branch_id else []
        access_level = 'personal'

    # Base querysets filtered by accessible branches
    branch_customers = Customer.all_objects.filter(branch_id__in=branch_ids)
    branch_loans = Loans.all_objects.filter(branch_id__in=branch_ids)
    branch_memtrans = Memtrans.all_objects.filter(branch_id__in=branch_ids)

    # For personal level, further filter by user
    if access_level == 'personal':
        if user_role in [7, 8]:  # Credit Supervisor/Officer - their assigned loans
            branch_loans = branch_loans.filter(user=request.user)
            # Get customers linked to their loans
            customer_ids = branch_loans.values_list('customer_id', flat=True)
            branch_customers = branch_customers.filter(id__in=customer_ids)
        elif user_role == 11:  # Teller - their transactions
            branch_memtrans = branch_memtrans.filter(user=request.user)
        elif user_role == 10:  # CSU - customers they serve (if tracked)
            pass  # Show branch customers for CSU

    # Calculate statistics based on filtered data
    current_month_deposits = (
        branch_memtrans.filter(
            ses_date__month=current_month, ses_date__year=current_year,
            amount__gt=0, account_type='C'
        ).aggregate(total=Sum('amount'))['total'] or 0
    )

    current_month_loans = (
        branch_loans.filter(
            appli_date__month=current_month, appli_date__year=current_year,
            disb_status='T'
        ).aggregate(total=Sum('loan_amount'))['total'] or 0
    )

    total_deposits = (
        branch_memtrans.filter(
            ses_date__year=current_year, amount__gt=0, account_type='C'
        ).aggregate(total=Sum('amount'))['total'] or 0
    )

    total_loans = (
        branch_loans.filter(
            disb_status='T', disbursement_date__year=current_year
        ).aggregate(total=Sum('loan_amount'))['total'] or 0
    )

    total_customers = branch_customers.count()

    # NPL Ratio
    npl_ratio = 0
    total_loans_count = branch_loans.count()
    if total_loans_count > 0:
        defaulted_count = branch_loans.filter(approval_status='Defaulted').count()
        npl_ratio = round((defaulted_count / total_loans_count) * 100, 2)

    # Monthly trends
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    deposits_trend = []
    loans_trend = []

    for m in range(1, 13):
        dep = branch_memtrans.filter(
            ses_date__month=m, ses_date__year=current_year,
            amount__gt=0, account_type='C'
        ).aggregate(total=Sum('amount'))['total'] or 0

        loan = branch_loans.filter(
            appli_date__month=m, appli_date__year=current_year,
            disb_status='T'
        ).aggregate(total=Sum('loan_amount'))['total'] or 0

        deposits_trend.append(float(dep) / 1_000_000_000)
        loans_trend.append(float(loan) / 1_000_000_000)

    # Customer Segmentation
    segmentation = {}
    for cat in Category.objects.all():
        segmentation[cat.category_name] = branch_customers.filter(cust_cat=cat).count()

    # Branch Performance - only for company/branch level access
    branch_data = []
    if access_level == 'company':
        branches_to_show = Branch.objects.filter(company=user_company)
    elif access_level == 'branch':
        branches_to_show = Branch.objects.filter(id=user_branch_id) if user_branch_id else []
    else:
        branches_to_show = []  # Personal level doesn't see branch performance

    for branch in branches_to_show:
        cust_count = Customer.all_objects.filter(branch_id=branch.id).count()
        
        b_deposits = Memtrans.all_objects.filter(
            branch_id=branch.id, amount__gt=0, account_type='C'
        ).aggregate(total=Sum('amount'))['total'] or 0

        b_loans = Loans.all_objects.filter(
            branch_id=branch.id, disb_status='T'
        ).aggregate(total=Sum('loan_amount'))['total'] or 0

        profit = Decimal(b_loans) * Decimal('0.05')
        
        npl_count = Loans.all_objects.filter(branch_id=branch.id, approval_status='Defaulted').count()
        total_b_loans = Loans.all_objects.filter(branch_id=branch.id).count()
        npl_ratio_branch = round((npl_count / total_b_loans) * 100, 2) if total_b_loans > 0 else 0

        if npl_ratio_branch < 5 and b_deposits > 0:
            status = "Excellent"
        elif npl_ratio_branch < 10:
            status = "Good"
        elif npl_ratio_branch < 15:
            status = "Fair"
        else:
            status = "Poor"

        branch_data.append({
            "name": branch.branch_name,
            "location": branch.address,
            "customers": cust_count,
            "deposits": b_deposits,
            "loans": b_loans,
            "profit": profit,
            "npl_ratio": npl_ratio_branch,
            "status": status,
        })

    # Role-specific extra data
    pending_loans = None
    today_transactions = None
    my_customers = None

    if user_role in [7, 8]:  # Credit roles - show pending loans
        pending_loans = branch_loans.filter(approval_status='Pending').count()
    
    if user_role == 11:  # Teller - show today's transactions
        today_transactions = branch_memtrans.filter(ses_date=today.date()).count()
    
    if user_role in [8, 10]:  # Credit Officer, CSU - show their customers
        my_customers = branch_customers.count()

    context = {
        'user_branch': user_branch,
        'user_company': user_company,
        'user_role': user_role,
        'access_level': access_level,
        
        "current_month_deposits": current_month_deposits,
        "current_month_loans": current_month_loans,
        "total_deposits": total_deposits,
        "total_loans": total_loans,
        "total_customers": total_customers,
        "npl_ratio": npl_ratio,

        "months": months,
        "deposits_trend": deposits_trend,
        "loans_trend": loans_trend,
        "segmentation": segmentation,
        "branch_data": branch_data,
        
        # Role-specific data
        "pending_loans": pending_loans,
        "today_transactions": today_transactions,
        "my_customers": my_customers,
    }

    return render(request, 'accounts/dashboard.html', context)


# ==================== ROLE-SPECIFIC DASHBOARDS ====================

def get_base_dashboard_context(request):
    """Get base context data for all dashboards"""
    today = timezone.now()
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    user_company = user_branch.company if user_branch else None
    
    try:
        user_branch_id = int(request.user.branch_id) if request.user.branch_id else None
    except (ValueError, TypeError):
        user_branch_id = None
    
    return {
        'today': today,
        'user_branch': user_branch,
        'user_company': user_company,
        'user_branch_id': user_branch_id,
        'user': request.user,
    }


@login_required(login_url='login')
def dashboard_2(request):
    """General Manager Dashboard - Company-wide overview"""
    ctx = get_base_dashboard_context(request)
    today = ctx['today']
    user_company = ctx['user_company']
    
    if user_company:
        company_branches = Branch.objects.filter(company=user_company)
        branch_ids = [b.id for b in company_branches]
    else:
        branch_ids = []
    
    # Company-wide statistics
    total_customers = Customer.all_objects.filter(branch_id__in=branch_ids).count()
    total_loans = Loans.all_objects.filter(branch_id__in=branch_ids, disb_status='T').aggregate(total=Sum('loan_amount'))['total'] or 0
    total_deposits = Memtrans.all_objects.filter(branch_id__in=branch_ids, amount__gt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    pending_loans = Loans.all_objects.filter(branch_id__in=branch_ids, approval_status='Pending').count()
    approved_loans = Loans.all_objects.filter(branch_id__in=branch_ids, approval_status='Approved').count()
    
    # Branch performance
    branch_data = []
    for branch in company_branches if user_company else []:
        cust_count = Customer.all_objects.filter(branch_id=branch.id).count()
        b_deposits = Memtrans.all_objects.filter(branch_id=branch.id, amount__gt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
        b_loans = Loans.all_objects.filter(branch_id=branch.id, disb_status='T').aggregate(total=Sum('loan_amount'))['total'] or 0
        branch_data.append({
            'name': branch.branch_name,
            'customers': cust_count,
            'deposits': b_deposits,
            'loans': b_loans,
        })
    
    context = {
        **ctx,
        'role_name': 'General Manager',
        'total_customers': total_customers,
        'total_loans': total_loans,
        'total_deposits': total_deposits,
        'pending_loans': pending_loans,
        'approved_loans': approved_loans,
        'branch_data': branch_data,
        'total_branches': len(branch_ids),
    }
    return render(request, 'accounts/dashboards/general_manager.html', context)


@login_required(login_url='login')
def dashboard_3(request):
    """Branch Manager Dashboard - Branch operations overview"""
    ctx = get_base_dashboard_context(request)
    branch_id = ctx['user_branch_id']
    today = ctx['today']
    
    # Branch statistics
    total_customers = Customer.all_objects.filter(branch_id=branch_id).count()
    total_loans = Loans.all_objects.filter(branch_id=branch_id, disb_status='T').aggregate(total=Sum('loan_amount'))['total'] or 0
    total_deposits = Memtrans.all_objects.filter(branch_id=branch_id, amount__gt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    pending_loans = Loans.all_objects.filter(branch_id=branch_id, approval_status='Pending').count()
    today_transactions = Memtrans.all_objects.filter(branch_id=branch_id, ses_date=today.date()).count()
    
    # Staff count
    staff_count = User.objects.filter(branch_id=branch_id, role__in=[4,5,6,7,8,9,10,11,12]).count()
    
    # Recent loans
    recent_loans = Loans.all_objects.filter(branch_id=branch_id).order_by('-appli_date')[:10]
    
    context = {
        **ctx,
        'role_name': 'Branch Manager',
        'total_customers': total_customers,
        'total_loans': total_loans,
        'total_deposits': total_deposits,
        'pending_loans': pending_loans,
        'today_transactions': today_transactions,
        'staff_count': staff_count,
        'recent_loans': recent_loans,
    }
    return render(request, 'accounts/dashboards/branch_manager.html', context)


@login_required(login_url='login')
def dashboard_4(request):
    """Assistant Manager Dashboard"""
    ctx = get_base_dashboard_context(request)
    branch_id = ctx['user_branch_id']
    today = ctx['today']
    
    total_customers = Customer.all_objects.filter(branch_id=branch_id).count()
    pending_loans = Loans.all_objects.filter(branch_id=branch_id, approval_status='Pending').count()
    today_transactions = Memtrans.all_objects.filter(branch_id=branch_id, ses_date=today.date()).count()
    total_deposits = Memtrans.all_objects.filter(branch_id=branch_id, amount__gt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        **ctx,
        'role_name': 'Assistant Manager',
        'total_customers': total_customers,
        'pending_loans': pending_loans,
        'today_transactions': today_transactions,
        'total_deposits': total_deposits,
    }
    return render(request, 'accounts/dashboards/assistant_manager.html', context)


@login_required(login_url='login')
def dashboard_5(request):
    """Accountant Dashboard - Financial overview"""
    ctx = get_base_dashboard_context(request)
    branch_id = ctx['user_branch_id']
    today = ctx['today']
    current_month = today.month
    current_year = today.year
    
    # Financial metrics
    total_deposits = Memtrans.all_objects.filter(branch_id=branch_id, amount__gt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    total_withdrawals = Memtrans.all_objects.filter(branch_id=branch_id, amount__lt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    month_deposits = Memtrans.all_objects.filter(branch_id=branch_id, ses_date__month=current_month, ses_date__year=current_year, amount__gt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    month_withdrawals = Memtrans.all_objects.filter(branch_id=branch_id, ses_date__month=current_month, ses_date__year=current_year, amount__lt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    
    total_loan_disbursed = Loans.all_objects.filter(branch_id=branch_id, disb_status='T').aggregate(total=Sum('loan_amount'))['total'] or 0
    total_loan_repaid = Loans.all_objects.filter(branch_id=branch_id, disb_status='T').aggregate(total=Sum('amount_paid'))['total'] or 0
    
    context = {
        **ctx,
        'role_name': 'Accountant',
        'total_deposits': total_deposits,
        'total_withdrawals': abs(total_withdrawals) if total_withdrawals else 0,
        'month_deposits': month_deposits,
        'month_withdrawals': abs(month_withdrawals) if month_withdrawals else 0,
        'total_loan_disbursed': total_loan_disbursed,
        'total_loan_repaid': total_loan_repaid,
    }
    return render(request, 'accounts/dashboards/accountant.html', context)


@login_required(login_url='login')
def dashboard_6(request):
    """Accounts Assistant Dashboard"""
    ctx = get_base_dashboard_context(request)
    branch_id = ctx['user_branch_id']
    today = ctx['today']
    
    today_deposits = Memtrans.all_objects.filter(branch_id=branch_id, ses_date=today.date(), amount__gt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    today_withdrawals = Memtrans.all_objects.filter(branch_id=branch_id, ses_date=today.date(), amount__lt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    today_transactions = Memtrans.all_objects.filter(branch_id=branch_id, ses_date=today.date()).count()
    
    recent_transactions = Memtrans.all_objects.filter(branch_id=branch_id).order_by('-ses_date', '-id')[:20]
    
    context = {
        **ctx,
        'role_name': 'Accounts Assistant',
        'today_deposits': today_deposits,
        'today_withdrawals': abs(today_withdrawals) if today_withdrawals else 0,
        'today_transactions': today_transactions,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'accounts/dashboards/accounts_assistant.html', context)


@login_required(login_url='login')
def dashboard_7(request):
    """Credit Supervisor Dashboard - Loan portfolio overview"""
    ctx = get_base_dashboard_context(request)
    branch_id = ctx['user_branch_id']
    
    # Loan statistics
    total_loans = Loans.all_objects.filter(branch_id=branch_id).count()
    pending_loans = Loans.all_objects.filter(branch_id=branch_id, approval_status='Pending').count()
    approved_loans = Loans.all_objects.filter(branch_id=branch_id, approval_status='Approved').count()
    disbursed_loans = Loans.all_objects.filter(branch_id=branch_id, disb_status='T').count()
    defaulted_loans = Loans.all_objects.filter(branch_id=branch_id, approval_status='Defaulted').count()
    
    total_portfolio = Loans.all_objects.filter(branch_id=branch_id, disb_status='T').aggregate(total=Sum('loan_amount'))['total'] or 0
    total_outstanding = Loans.all_objects.filter(branch_id=branch_id, disb_status='T').aggregate(total=Sum('loan_balance'))['total'] or 0
    
    # Loans pending approval
    loans_to_approve = Loans.all_objects.filter(branch_id=branch_id, approval_status='Pending').order_by('-appli_date')[:10]
    
    # Credit officers performance
    credit_officers = User.objects.filter(branch_id=branch_id, role__in=[7, 8])
    officer_performance = []
    for officer in credit_officers:
        officer_loans = Loans.all_objects.filter(branch_id=branch_id, user=officer)
        officer_performance.append({
            'name': f"{officer.first_name} {officer.last_name}",
            'total_loans': officer_loans.count(),
            'disbursed': officer_loans.filter(disb_status='T').count(),
            'defaulted': officer_loans.filter(approval_status='Defaulted').count(),
        })
    
    context = {
        **ctx,
        'role_name': 'Credit Supervisor',
        'total_loans': total_loans,
        'pending_loans': pending_loans,
        'approved_loans': approved_loans,
        'disbursed_loans': disbursed_loans,
        'defaulted_loans': defaulted_loans,
        'total_portfolio': total_portfolio,
        'total_outstanding': total_outstanding,
        'loans_to_approve': loans_to_approve,
        'officer_performance': officer_performance,
    }
    return render(request, 'accounts/dashboards/credit_supervisor.html', context)


@login_required(login_url='login')
def dashboard_8(request):
    """Credit Officer Dashboard - Personal loan management"""
    ctx = get_base_dashboard_context(request)
    branch_id = ctx['user_branch_id']
    user = request.user
    
    # My loans
    my_loans = Loans.all_objects.filter(branch_id=branch_id, user=user)
    my_pending = my_loans.filter(approval_status='Pending').count()
    my_approved = my_loans.filter(approval_status='Approved').count()
    my_disbursed = my_loans.filter(disb_status='T').count()
    my_defaulted = my_loans.filter(approval_status='Defaulted').count()
    
    my_portfolio = my_loans.filter(disb_status='T').aggregate(total=Sum('loan_amount'))['total'] or 0
    my_outstanding = my_loans.filter(disb_status='T').aggregate(total=Sum('loan_balance'))['total'] or 0
    
    # Recent loans
    recent_loans = my_loans.order_by('-appli_date')[:10]
    
    # My customers
    my_customer_ids = my_loans.values_list('customer_id', flat=True).distinct()
    my_customers = Customer.all_objects.filter(id__in=my_customer_ids).count()
    
    context = {
        **ctx,
        'role_name': 'Credit Officer',
        'my_pending': my_pending,
        'my_approved': my_approved,
        'my_disbursed': my_disbursed,
        'my_defaulted': my_defaulted,
        'my_portfolio': my_portfolio,
        'my_outstanding': my_outstanding,
        'recent_loans': recent_loans,
        'my_customers': my_customers,
        'total_loans': my_loans.count(),
    }
    return render(request, 'accounts/dashboards/credit_officer.html', context)


@login_required(login_url='login')
def dashboard_9(request):
    """Verification Officer Dashboard - Customer verification tasks"""
    ctx = get_base_dashboard_context(request)
    branch_id = ctx['user_branch_id']
    today = ctx['today']
    
    # Total customers
    total_customers = Customer.all_objects.filter(branch_id=branch_id).count()
    
    # New customers this month (need verification)
    new_customers_month = Customer.all_objects.filter(
        branch_id=branch_id, 
        date_registered__month=today.month, 
        date_registered__year=today.year
    ).count()
    
    # Recent customers to review
    recent_customers = Customer.all_objects.filter(branch_id=branch_id).order_by('-date_registered')[:20]
    
    # Loans pending verification/approval
    pending_loans = Loans.all_objects.filter(branch_id=branch_id, approval_status='Pending').count()
    approved_loans = Loans.all_objects.filter(branch_id=branch_id, approval_status='Approved').count()
    
    context = {
        **ctx,
        'role_name': 'Verification Officer',
        'total_customers': total_customers,
        'new_customers_month': new_customers_month,
        'recent_customers': recent_customers,
        'pending_loans': pending_loans,
        'approved_loans': approved_loans,
    }
    return render(request, 'accounts/dashboards/verification_officer.html', context)


@login_required(login_url='login')
def dashboard_10(request):
    """Customer Service Unit Dashboard"""
    ctx = get_base_dashboard_context(request)
    branch_id = ctx['user_branch_id']
    today = ctx['today']
    
    total_customers = Customer.all_objects.filter(branch_id=branch_id).count()
    new_customers_today = Customer.all_objects.filter(branch_id=branch_id, created_at__date=today.date()).count()
    new_customers_month = Customer.all_objects.filter(branch_id=branch_id, created_at__month=today.month, created_at__year=today.year).count()
    
    # Recent customers
    recent_customers = Customer.all_objects.filter(branch_id=branch_id).order_by('-created_at')[:20]
    
    context = {
        **ctx,
        'role_name': 'Customer Service',
        'total_customers': total_customers,
        'new_customers_today': new_customers_today,
        'new_customers_month': new_customers_month,
        'recent_customers': recent_customers,
    }
    return render(request, 'accounts/dashboards/customer_service.html', context)


@login_required(login_url='login')
def dashboard_11(request):
    """Teller Dashboard - Daily transactions"""
    ctx = get_base_dashboard_context(request)
    branch_id = ctx['user_branch_id']
    today = ctx['today']
    user = request.user
    
    # Today's transactions by this teller
    my_today_transactions = Memtrans.all_objects.filter(branch_id=branch_id, ses_date=today.date(), user=user)
    my_deposits = my_today_transactions.filter(amount__gt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    my_withdrawals = my_today_transactions.filter(amount__lt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    my_transaction_count = my_today_transactions.count()
    
    # Branch totals for today
    branch_today = Memtrans.all_objects.filter(branch_id=branch_id, ses_date=today.date())
    branch_deposits = branch_today.filter(amount__gt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    branch_withdrawals = branch_today.filter(amount__lt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
    
    # Recent transactions
    recent_transactions = my_today_transactions.order_by('-id')[:20]
    
    context = {
        **ctx,
        'role_name': 'Teller',
        'my_deposits': my_deposits,
        'my_withdrawals': abs(my_withdrawals) if my_withdrawals else 0,
        'my_transaction_count': my_transaction_count,
        'branch_deposits': branch_deposits,
        'branch_withdrawals': abs(branch_withdrawals) if branch_withdrawals else 0,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'accounts/dashboards/teller.html', context)


@login_required(login_url='login')
def dashboard_12(request):
    """M.I.S Officer Dashboard - Reports and analytics"""
    ctx = get_base_dashboard_context(request)
    branch_id = ctx['user_branch_id']
    today = ctx['today']
    current_month = today.month
    current_year = today.year
    
    # Overall statistics
    total_customers = Customer.all_objects.filter(branch_id=branch_id).count()
    total_loans = Loans.all_objects.filter(branch_id=branch_id).count()
    total_transactions = Memtrans.all_objects.filter(branch_id=branch_id).count()
    
    # Monthly trends
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    deposits_trend = []
    loans_trend = []
    customers_trend = []
    
    for m in range(1, 13):
        dep = Memtrans.all_objects.filter(branch_id=branch_id, ses_date__month=m, ses_date__year=current_year, amount__gt=0, account_type='C').aggregate(total=Sum('amount'))['total'] or 0
        loan = Loans.all_objects.filter(branch_id=branch_id, appli_date__month=m, appli_date__year=current_year, disb_status='T').aggregate(total=Sum('loan_amount'))['total'] or 0
        cust = Customer.all_objects.filter(branch_id=branch_id, created_at__month=m, created_at__year=current_year).count()
        
        deposits_trend.append(float(dep))
        loans_trend.append(float(loan))
        customers_trend.append(cust)
    
    # NPL ratio
    total_loan_count = Loans.all_objects.filter(branch_id=branch_id).count()
    defaulted_count = Loans.all_objects.filter(branch_id=branch_id, approval_status='Defaulted').count()
    npl_ratio = round((defaulted_count / total_loan_count) * 100, 2) if total_loan_count > 0 else 0
    
    context = {
        **ctx,
        'role_name': 'M.I.S Officer',
        'total_customers': total_customers,
        'total_loans': total_loans,
        'total_transactions': total_transactions,
        'months': months,
        'deposits_trend': deposits_trend,
        'loans_trend': loans_trend,
        'customers_trend': customers_trend,
        'npl_ratio': npl_ratio,
    }
    return render(request, 'accounts/dashboards/mis_officer.html', context)


@login_required(login_url='login')
def customer_dashboard(request):
    """Customer Dashboard - Personal account overview"""
    ctx = get_base_dashboard_context(request)
    user = request.user
    
    # Get customer record
    try:
        customer = Customer.all_objects.get(email=user.email)
    except Customer.DoesNotExist:
        customer = None
    
    if customer:
        # Account balance
        account_balance = customer.available_balance or 0
        
        # My loans
        my_loans = Loans.all_objects.filter(customer=customer)
        active_loans = my_loans.filter(disb_status='T', loan_balance__gt=0).count()
        total_loan_balance = my_loans.filter(disb_status='T').aggregate(total=Sum('loan_balance'))['total'] or 0
        
        # Recent transactions
        recent_transactions = Memtrans.all_objects.filter(cust_ac_no=customer.cust_ac_no).order_by('-ses_date', '-id')[:10]
    else:
        account_balance = 0
        active_loans = 0
        total_loan_balance = 0
        recent_transactions = []
    
    context = {
        **ctx,
        'role_name': 'Customer',
        'customer': customer,
        'account_balance': account_balance,
        'active_loans': active_loans,
        'total_loan_balance': total_loan_balance,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'accounts/dashboards/customer.html', context)


# ==================== PASSWORD MANAGEMENT ====================

@login_required(login_url='login')
def change_password(request):
    """Change password view"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = request.user
        
        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('change_password')
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('change_password')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('change_password')
        
        user.set_password(new_password)
        user.save()
        
        # Re-authenticate the user
        user = auth.authenticate(username=user.username, password=new_password)
        if user:
            auth.login(request, user)
        
        messages.success(request, 'Password changed successfully.')
        return redirect('myAccount')
    
    return render(request, 'accounts/change_password.html')


def forgot_password(request):
    """Forgot password view"""
    if request.method == 'POST':
        email = request.POST['email']

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email__exact=email)
            
            # Send reset password email
            mail_subject = 'Reset Your Password'
            email_template = 'accounts/email/reset_password_email.html'
            send_verification_email(request, user, mail_subject, email_template)

            messages.success(request, 'Password reset link has been sent to your email address.')
            return redirect('forgot_password')
        else:
            messages.error(request, 'Account does not exist')
            return redirect('forgot_password')
    
    return render(request, 'accounts/forgot_password.html')


def reset_password_validate(request, uidb64, token):
    """Validate password reset token"""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.info(request, 'Please reset your password')
        return redirect('reset_password')
    else:
        messages.error(request, 'This link has been expired!')
        return redirect('myAccount')


def reset_password(request):
    """Reset password view"""
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            pk = request.session.get('uid')
            user = User.objects.get(pk=pk)
            user.set_password(password)
            user.is_active = True
            user.save()
            messages.success(request, 'Password reset successful')
            return redirect('login')
        else:
            messages.error(request, 'Password do not match!')
            return redirect('reset_password')
    
    return render(request, 'accounts/reset_password.html')


# ==================== ACCOUNT ACTIVATION ====================

def activate(request, uidb64, token):
    """Activate user account"""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.verified = True
        user.save()
        auth.login(request, user)
        
        messages.success(request, 'Account activated successfully!')
        return redirect('dashboard')
    else:
        messages.error(request, 'The activation link is invalid or has expired.')
        return redirect('login')


# ==================== UTILITY VIEWS ====================

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def user_admin(request):
    """User admin view"""
    return render(request, 'accounts/user_admin.html')


def contact_support(request):
    """Contact support view"""
    return render(request, 'contact_support.html')


def forbidden(request):
    """403 Forbidden page"""
    return render(request, 'accounts/403.html')


# ==================== BRANCH MANAGEMENT VIEWS ====================

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def branches_view(request):
    """View all branches from vendor database"""
    branches = get_all_branches_from_vendor_db()
    
    # Add user count for each branch
    branches_with_stats = []
    for branch in branches:
        user_count = User.objects.filter(branch_id=str(branch.id)).count()
        customer_count = Customer.objects.filter(branch_id=str(branch.id)).count()
        
        branch.user_count = user_count
        branch.customer_count = customer_count
        branches_with_stats.append(branch)
    
    context = {
        'branches': branches_with_stats,
    }
    return render(request, 'accounts/branches.html', context)


# ==================== TRANSACTION PIN MANAGEMENT ====================

@login_required(login_url='login')
def set_transaction_pin(request):
    """Set or update user transaction PIN"""
    if request.method == 'POST':
        current_pin = request.POST.get('current_pin')
        new_pin = request.POST.get('new_pin')
        confirm_pin = request.POST.get('confirm_pin')
        
        user = request.user
        
        # Validate current PIN if user has one
        if user.transaction_pin:
            if not current_pin:
                messages.error(request, 'Current PIN is required.')
                return redirect('myAccount')
            if not user.check_transaction_pin(current_pin):
                messages.error(request, 'Current PIN is incorrect.')
                return redirect('myAccount')
        
        # Validate new PIN
        if not new_pin or not new_pin.isdigit():
            messages.error(request, 'PIN must contain only numbers.')
            return redirect('myAccount')
        
        if len(new_pin) < 4 or len(new_pin) > 6:
            messages.error(request, 'PIN must be between 4 and 6 digits.')
            return redirect('myAccount')
        
        if new_pin != confirm_pin:
            messages.error(request, 'PIN confirmation does not match.')
            return redirect('myAccount')
        
        # Set new PIN
        user.set_transaction_pin(new_pin)
        user.save()
        
        messages.success(request, 'Transaction PIN updated successfully.')
        return redirect('myAccount')
    
    return redirect('myAccount')


# ==================== USER SEARCH FUNCTIONALITY ====================

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def search_users(request):
    """Search users with branch information"""
    query = request.GET.get('q', '')
    users_list = []
    
    if query:
        users = User.objects.filter(
            username__icontains=query
        ) | User.objects.filter(
            first_name__icontains=query
        ) | User.objects.filter(
            last_name__icontains=query
        ) | User.objects.filter(
            email__icontains=query
        )
        
        # Add branch information
        for user in users:
            branch = get_branch_from_vendor_db(user.branch_id)
            user.branch_display = branch.branch_name if branch else "No Branch"
            user.company_display = branch.company.company_name if branch and branch.company else "No Company"
            users_list.append(user)
    
    context = {
        'users': users_list,
        'query': query,
    }
    return render(request, 'accounts/search_users.html', context)


# ==================== API ENDPOINTS ====================

@login_required(login_url='login')
def user_profile_ajax(request, user_id):
    """AJAX endpoint for user profile information"""
    try:
        user = User.objects.get(id=user_id)
        branch = get_branch_from_vendor_db(user.branch_id)
        company = branch.company if branch else None
        
        data = {
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone_number': user.phone_number,
                'role': user.get_role(),
                'branch_name': branch.branch_name if branch else None,
                'company_name': company.company_name if company else None,
                'is_active': user.is_active,
                'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            }
        }
        return JsonResponse(data)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def branch_users_ajax(request, branch_id):
    """AJAX endpoint for getting users by branch"""
    try:
        branch = get_branch_from_vendor_db(branch_id)
        if not branch:
            return JsonResponse({'success': False, 'error': 'Branch not found'})
        
        users = User.objects.filter(branch_id=str(branch_id))
        users_data = []
        
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': user.get_role(),
                'is_active': user.is_active,
            })
        
        data = {
            'success': True,
            'branch_name': branch.branch_name,
            'users': users_data,
            'count': len(users_data)
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ==================== AUTO LOGOUT SETTINGS ====================

@login_required(login_url='login')
def auto_logout_settings(request):
    """Auto logout settings view"""
    if request.method == 'POST':
        # Handle auto logout settings update
        timeout_minutes = request.POST.get('timeout_minutes', 30)
        # Store in session or user preferences
        request.session['auto_logout_timeout'] = int(timeout_minutes)
        messages.success(request, 'Auto logout settings updated.')
        return redirect('myAccount')
    
    context = {
        'current_timeout': request.session.get('auto_logout_timeout', 30),
    }
    return render(request, 'accounts/auto_logout_settings.html', context)


# ==================== ROLE PERMISSION MANAGEMENT ====================

# Feature categories and permissions
FEATURE_CATEGORIES = {
    'Dashboard': {
        'view_dashboard': 'View Dashboard',
    },
    'User Management': {
        'view_users': 'View Users',
        'create_user': 'Create User',
        'edit_user': 'Edit User',
        'delete_user': 'Delete User',
        'verify_user': 'Verify User',
        'manage_permissions': 'Manage Role Permissions',
    },
    'Customer Management': {
        'view_customers': 'View Customers',
        'create_customer': 'Create Customer',
        'edit_customer': 'Edit Customer',
        'delete_customer': 'Delete Customer',
        'view_customer_detail': 'View Customer Detail',
        'manage_customer_groups': 'Manage Customer Groups',
        'register_company': 'Register Company/Business Customer',
    },
    'Transactions': {
        'make_deposit': 'Make Deposit',
        'make_withdrawal': 'Make Withdrawal',
        'record_income': 'Record Income',
        'record_expense': 'Record Expense',
        'general_journal': 'General Journal Entry',
        'view_transactions': 'View Transactions',
        'delete_transaction': 'Delete Transaction',
        'seek_and_update': 'Seek and Update Transactions',
        'upload_transactions': 'Upload Transactions (Bulk)',
    },
    'Loan Management': {
        'view_loans': 'View Loans',
        'apply_loan': 'Apply for Loan',
        'modify_loan': 'Modify Loan Application',
        'approve_loan': 'Approve Loan',
        'reject_loan': 'Reject Loan',
        'reverse_loan_approval': 'Reverse Loan Approval',
        'disburse_loan': 'Disburse Loan',
        'reverse_disbursement': 'Reverse Loan Disbursement',
        'loan_repayment': 'Record Loan Repayment',
        'write_off_loan': 'Write Off Loan',
        'view_loan_schedule': 'View Loan Schedule',
        'view_loan_history': 'View Loan History',
        'delete_loan': 'Delete Loan',
        'simple_loan': 'Simple Loan (Application & Approval)',
    },
    'Fixed Deposit': {
        'view_fixed_deposits': 'View Fixed Deposits',
        'register_fixed_deposit': 'Register Fixed Deposit',
        'withdraw_fixed_deposit': 'Withdraw Fixed Deposit',
        'reverse_fixed_deposit': 'Reverse Fixed Deposit',
        'renew_fixed_deposit': 'Renew Fixed Deposit',
        'premature_withdrawal': 'Premature Withdrawal',
        'generate_fd_certificate': 'Generate FD Certificate',
        'mark_lien': 'Mark Lien on Fixed Deposit',
        'manage_fd_products': 'Manage FD Products',
        'fd_interest_accrual': 'Run FD Interest Accrual',
    },
    'Fixed Assets': {
        'view_fixed_assets': 'View Fixed Assets',
        'create_fixed_asset': 'Create Fixed Asset',
        'edit_fixed_asset': 'Edit Fixed Asset',
        'delete_fixed_asset': 'Delete Fixed Asset',
        'post_depreciation': 'Post Depreciation',
        'dispose_asset': 'Dispose Asset',
        'revalue_asset': 'Revalue Asset',
        'transfer_asset': 'Transfer Asset',
        'impair_asset': 'Record Asset Impairment',
        'manage_asset_insurance': 'Manage Asset Insurance',
        'manage_asset_maintenance': 'Manage Asset Maintenance',
        'manage_asset_warranty': 'Manage Asset Warranty',
        'asset_verification': 'Asset Verification',
        'manage_asset_settings': 'Manage Asset Settings (Types/Groups/Locations)',
    },
    'Reports': {
        'view_reports': 'View Reports',
        'generate_statement': 'Generate Account Statement',
        'front_office_report': 'Front Office Reports',
        'back_office_report': 'Back Office Reports',
        'trial_balance': 'Trial Balance Report',
        'financial_report': 'Financial Reports',
        'balance_sheet': 'Balance Sheet',
        'profit_and_loss': 'Profit & Loss Statement',
        'loan_reports': 'Loan Reports',
        'savings_reports': 'Savings Reports',
        'transaction_reports': 'Transaction Reports',
        'cbn_returns': 'CBN Returns',
        'fd_reports': 'Fixed Deposit Reports',
        'asset_reports': 'Fixed Asset Reports',
        'export_reports': 'Export Reports (PDF/Excel/CSV)',
    },
    'Chart of Accounts': {
        'view_chart_of_accounts': 'View Chart of Accounts',
        'create_account': 'Create Account',
        'edit_account': 'Edit Account',
        'delete_account': 'Delete Account',
    },
    'Settings & Configuration': {
        'account_settings': 'Account Settings',
        'product_settings': 'Product Settings',
        'manage_account_officers': 'Manage Account Officers',
        'manage_regions': 'Manage Regions',
        'manage_categories': 'Manage Categories',
        'manage_id_types': 'Manage ID Types',
        'manage_business_sectors': 'Manage Business Sectors',
        'manage_interest_rates': 'Manage Interest Rates',
        'manage_loan_provisions': 'Manage Loan Provisions',
        'manage_customer_account_types': 'Manage Customer Account Types',
        'loan_auto_repayment_settings': 'Loan Auto Repayment Settings',
        'utilities': 'System Utilities',
    },
    'End of Period': {
        'end_of_period': 'Run End of Period',
        'calculate_interest': 'Calculate Interest',
    },
    'Company & Branch': {
        'session_management': 'Session Management',
        'view_branch_info': 'View Branch Information',
    },
    'Audit Trail': {
        'view_audit_trail': 'View Audit Trail',
        'audit_statistics': 'Audit Statistics',
        'audit_configuration': 'Audit Configuration',
        'export_audit': 'Export Audit Trail',
        'manage_alerts': 'Manage Audit Alerts',
    },
}

# Flatten all features
ALL_FEATURES = {}
for category, features in FEATURE_CATEGORIES.items():
    ALL_FEATURES.update(features)


def user_has_permission(user, permission_code):
    """Check if a user has a specific permission"""
    if not user or not user.is_authenticated:
        return False
    
    # System Administrator (role=1) has all permissions
    if user.role == 1 or user.is_superadmin or user.is_admin:
        return True
    
    # Check role-based permissions
    try:
        role_perm = RolePermission.objects.get(role=user.role)
        return permission_code in role_perm.permissions
    except RolePermission.DoesNotExist:
        return False


def permission_required_view(permission_code):
    """Decorator to check if user has the required permission"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Please login to access this feature.')
                return redirect('login')
            
            if not user_has_permission(request.user, permission_code):
                feature_name = ALL_FEATURES.get(permission_code, permission_code)
                messages.error(
                    request, 
                    f'Access Denied: You do not have permission to access "{feature_name}". '
                    f'Please contact your administrator to request access to this feature.'
                )
                return render(request, 'accounts/permission_denied.html', {
                    'feature_name': feature_name,
                    'permission_code': permission_code,
                })
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def manage_role_permissions(request):
    """View to manage role permissions"""
    roles = User.ROLE_CHOICE
    selected_role = request.GET.get('role')
    current_permissions = []
    
    if selected_role:
        selected_role = int(selected_role)
        try:
            role_perm = RolePermission.objects.get(role=selected_role)
            current_permissions = role_perm.permissions
        except RolePermission.DoesNotExist:
            current_permissions = []
    
    if request.method == 'POST':
        role_id = int(request.POST.get('role_id'))
        selected_permissions = request.POST.getlist('permissions')
        
        role_perm, created = RolePermission.objects.get_or_create(role=role_id)
        role_perm.permissions = selected_permissions
        role_perm.save()
        
        role_name = dict(User.ROLE_CHOICE).get(role_id, 'Unknown')
        messages.success(request, f'Permissions for "{role_name}" have been updated successfully!')
        return redirect(f'/accounts/manage_permissions/?role={role_id}')
    
    context = {
        'roles': roles,
        'selected_role': selected_role,
        'current_permissions': current_permissions,
        'feature_categories': FEATURE_CATEGORIES,
        'all_features': ALL_FEATURES,
    }
    return render(request, 'accounts/manage_permissions.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def view_role_permissions(request):
    """View all role permissions summary"""
    roles = User.ROLE_CHOICE
    role_permissions_list = []
    
    for role_id, role_name in roles:
        try:
            role_perm = RolePermission.objects.get(role=role_id)
            perm_count = len(role_perm.permissions)
        except RolePermission.DoesNotExist:
            perm_count = 0
        
        role_permissions_list.append({
            'role_id': role_id,
            'role_name': role_name,
            'permission_count': perm_count,
            'total_features': len(ALL_FEATURES),
        })
    
    context = {
        'role_permissions_list': role_permissions_list,
    }
    return render(request, 'accounts/view_role_permissions.html', context)