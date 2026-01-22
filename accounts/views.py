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

# Import models from correct locations for multi-database architecture
from company.models import Company, Branch  # Vendor database
from .forms import UserForm, UserProfileForm, UserProfilePictureForm, EdituserForm
from .models import Role, User, UserProfile  # Client database
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
    """Check if user has admin role"""
    if user.role == 1:
        return True
    else:
        raise PermissionDenied


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
@user_passes_test(check_role_admin)
def registerUser(request):
    """Register a new user with multi-database support"""
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

            user.save()
            
            # Get branch name for success message
            user_branch = get_branch_from_vendor_db(user.branch_id)
            branch_name = user_branch.branch_name if user_branch else "Unknown Branch"
            
            messages.success(request, f'User {user.username} registered successfully in {branch_name}!')
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
@user_passes_test(check_role_admin)
def users(request):
    """Display all users for admin with branch information"""
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
@user_passes_test(check_role_admin)
def editUser(request, uuid=None):
    """Edit user with multi-database branch support"""
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
@user_passes_test(check_role_admin)
def deleteUser(request, uuid=None):
    """Delete a user"""
    user = get_object_or_404(User, uuid=uuid)
    user.delete()
    messages.success(request, 'User deleted successfully!')
    return redirect('display_all_user')


# Alias for compatibility
def delete_user(request, uuid):
    """Delete user by UUID (compatibility function)"""
    user = User.objects.get(uuid=uuid)
    user.delete()
    messages.success(request, 'User deleted successfully!')
    return redirect('display_all_user')


# ==================== DASHBOARD VIEW ====================

@login_required(login_url='login')
def dashboard(request):
    """Dashboard with statistics and branch information"""
    # Date setup
    today = timezone.now()
    current_month = today.month
    current_year = today.year

    # Get user's branch and company information
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    user_company = user_branch.company if user_branch else None

    # Get company branches for filtering
    if user_company:
        company_branches = Branch.objects.filter(company=user_company)
        company_branch_ids = [b.id for b in company_branches]  # Keep as integers for ForeignKey
    else:
        company_branch_ids = [int(request.user.branch_id)] if request.user.branch_id else []

    # Filter base querysets by company branches (use all_objects to bypass TenantManager)
    company_customers = Customer.all_objects.filter(branch_id__in=company_branch_ids)
    company_loans = Loans.all_objects.filter(branch_id__in=company_branch_ids)
    company_memtrans = Memtrans.all_objects.filter(branch_id__in=company_branch_ids)

    # Current Month Deposits
    current_month_deposits = (
        company_memtrans.filter(
            ses_date__month=current_month,
            ses_date__year=current_year,
            amount__gt=0,
            account_type='C'
        ).aggregate(total=Sum('amount'))['total'] or 0
    )

    # Current Month Loans (disbursed only)
    current_month_loans = (
        company_loans.filter(
            appli_date__month=current_month,
            appli_date__year=current_year,
            disb_status='T'
        ).aggregate(total=Sum('loan_amount'))['total'] or 0
    )

    # Accumulated Deposits (YTD)
    total_deposits = (
        company_memtrans.filter(
            ses_date__year=current_year,
            amount__gt=0,
            account_type='C'
        ).aggregate(total=Sum('amount'))['total'] or 0
    )

    # Accumulated Loans (YTD)
    total_loans = (
        company_loans.filter(
            disb_status='T',
            disbursement_date__year=current_year
        ).aggregate(total=Sum('loan_amount'))['total'] or 0
    )

    total_customers = company_customers.count()

    # NPL Ratio
    npl_ratio = 0
    if company_loans.exists():
        total_loans_count = company_loans.count()
        defaulted_count = company_loans.filter(approval_status='Defaulted').count()
        npl_ratio = (
            round((defaulted_count / total_loans_count) * 100, 2)
            if total_loans_count > 0 else 0
        )

    # Monthly trends
    months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    deposits_trend = []
    loans_trend = []

    for m in range(1, 13):
        deposits = (
            company_memtrans.filter(
                ses_date__month=m,
                ses_date__year=current_year,
                amount__gt=0,
                account_type='C'
            ).aggregate(total=Sum('amount'))['total'] or 0
        )

        loans = (
            company_loans.filter(
                appli_date__month=m,
                appli_date__year=current_year,
                disb_status='T'
            ).aggregate(total=Sum('loan_amount'))['total'] or 0
        )

        deposits_trend.append(float(deposits) / 1_000_000_000)
        loans_trend.append(float(loans) / 1_000_000_000)

    # Customer Segmentation (filtered by company)
    segmentation = {}
    for cat in Category.objects.all():
        segmentation[cat.category_name] = company_customers.filter(cust_cat=cat).count()

    # Branch Performance (only show company branches)
    branch_data = []
    # Get branches belonging to user's company only
    if user_company:
        branches_to_show = Branch.objects.filter(company=user_company)
    else:
        branches_to_show = Branch.objects.filter(id=request.user.branch_id) if request.user.branch_id else []
    
    for branch in branches_to_show:
        # Count customers and loans for this branch (use all_objects to bypass TenantManager)
        cust_count = Customer.all_objects.filter(branch_id=branch.id).count()
        
        branch_deposits = (
            Memtrans.all_objects.filter(
                branch_id=branch.id,
                amount__gt=0,
                account_type='C'
            ).aggregate(total=Sum('amount'))['total'] or 0
        )

        branch_loans = (
            Loans.all_objects.filter(
                branch_id=branch.id,
                disb_status='T'
            ).aggregate(total=Sum('loan_amount'))['total'] or 0
        )

        profit = Decimal(branch_loans) * Decimal('0.05')
        
        npl = Loans.all_objects.filter(
            branch_id=branch.id,
            approval_status='Defaulted'
        ).count()
        total_loans_branch = Loans.all_objects.filter(branch_id=branch.id).count()
        npl_ratio_branch = (
            round((npl / total_loans_branch) * 100, 2)
            if total_loans_branch > 0 else 0
        )

        # Branch Status
        if npl_ratio_branch < 5 and branch_deposits > 0:
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
            "deposits": branch_deposits,
            "loans": branch_loans,
            "profit": profit,
            "npl_ratio": npl_ratio_branch,
            "status": status,
        })

    context = {
        # User information
        'user_branch': user_branch,
        'user_company': user_company,
        
        # Current Month
        "current_month_deposits": current_month_deposits,
        "current_month_loans": current_month_loans,

        # Accumulated (YTD)
        "total_deposits": total_deposits,
        "total_loans": total_loans,
        "total_customers": total_customers,
        "npl_ratio": npl_ratio,

        # Charts & Lists
        "months": months,
        "deposits_trend": deposits_trend,
        "loans_trend": loans_trend,
        "segmentation": segmentation,
        "branch_data": branch_data,
    }

    return render(request, 'accounts/dashboard.html', context)


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