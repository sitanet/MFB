from datetime import datetime
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import message
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlsafe_base64_decode

from accounts.utils import detectUser, send_verification_email
from accounts_admin.models import Account
from customers.models import Customer

from django.urls import reverse


from .forms import UserForm, UserProfileForm, UserProfilePictureForm, EdituserForm
from .models import Role, User, UserProfile
from django.contrib import messages, auth
# from .utils import detectUser, send_verification_email
from django.contrib.auth.decorators import login_required, user_passes_test

from django.core.exceptions import PermissionDenied
# from vendor.models import Vendor
# from django.template.defaultfilters import slugify
# from orders.models import Order
import datetime

from company.models import Company, Branch



from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator

# Create your views here.

# Restrict the vendor from accessing the customer page
def check_role_admin(user):
    if user.role == 1:
        return True
    else:
        raise PermissionDenied


# Restrict the customer from accessing the vendor page
def check_role_coordinator(user):
    if user.role == 2:
        return True
    else:
        raise PermissionDenied
    
def check_role_team_member(user):
    if user.role == 3:
        return True
    else:
        raise PermissionDenied
        
@login_required(login_url='login')
@user_passes_test(check_role_admin)
def registeruser(request):
    # Get the branches available to the user based on their role or branch
    if request.user.is_authenticated:
        # If the logged-in user has a branch (e.g., a branch manager or general manager)
        if request.user.branch:
            branches = Branch.objects.filter(id=request.user.branch.id)  # Only show the user's assigned branch
        else:
            branches = Branch.objects.all()  # If no branch assigned to the user, show all branches
    else:
        branches = Branch.objects.all()  # If not logged in, show all branches (or restrict as needed)
    
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            # Extract data from the form
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            phone_number = form.cleaned_data['phone_number']
            role = form.cleaned_data['role']
            branch = form.cleaned_data['branch']  # Get the branch from form submission
            cashier_gl = form.cleaned_data['cashier_gl']
            cashier_ac = form.cleaned_data['cashier_ac']

            # Create the new user
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                role=role,
                phone_number=phone_number,
                branch=branch,  # Set branch to the one selected in the form
                cashier_gl=cashier_gl,
                cashier_ac=cashier_ac,
                password=password
            )
            user.save()

            messages.success(request, 'You have successfully registered the user!')

            return redirect('display_all_user')  # Redirect to your user display page
        else:
            messages.error(request, 'There were errors in the form.')
            print(form.errors)
    else:
        form = UserForm()

    # Pass the branches to the context, so the form can render the dropdown list
    context = {
        'form': form,
        'branches': branches,  # Provide the branches to the template
    }

    return render(request, 'accounts/registeruser.html', context)




from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.conf import settings
from accounts.forms import UserForm
import logging

logger = logging.getLogger(__name__)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Branch
from .forms import UserForm  # adjust to your form name
import random
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .forms import UserForm
from company.models import Branch
from django.contrib.auth import get_user_model
from .utils import send_sms   # ✅ Import Termii SMS util

User = get_user_model()


def register(request):
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
            user.branch = form.cleaned_data['branch']
            user.set_password(form.cleaned_data["password"])

            otp_code = str(random.randint(100000, 999999))
            user.otp_code = otp_code
            user.last_otp_sent = timezone.now()
            user.save()
            print(f"👤 User created: {user.username}, email: {user.email}, OTP: {otp_code}")

            # ✅ Send Email
            try:
                subject = "Your OTP Code"
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [user.email]

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
                    <p>Thank you,<br>{user.branch.company_name}</p>
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

            # ✅ Send SMS
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


def user_verify_otp(request):
    print("🔍 Entered user_verify_otp view")

    user = User.objects.first()
    if not user:
        print("❌ No user found")
        messages.error(request, "No registered user found. Please register first.")
        return redirect("register")

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

        # ✅ Send Email
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
                <p>Thank you,<br>{user.branch.company_name}</p>
            </body></html>
            """

            msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            print(f"📧 Resent OTP email to {user.email}")
        except Exception as e:
            print(f"❌ Failed to resend OTP email: {e}")
            messages.warning(request, "OTP email could not be sent.")

        # ✅ Send SMS
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





def registerusermasterintelligent(request):
     branch = Company.objects.all()
     
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

            user = User.objects.create_user(first_name=first_name, last_name=last_name, username=username, email=email, role=role, phone_number=phone_number, branch=branch, cashier_gl=cashier_gl,cashier_ac=cashier_ac, password=password)
            
            user.save()
            messages.success(request, 'You have successfull register User')

            # Send verification email
            # mail_subject = 'Please activate your account'
            # email_template = 'accounts/email/accounts_verification_email.html'
            # send_verification_email(request, user, mail_subject, email_template)
            # messages.success(request, 'Your account has been registered sucessfully!')
            return redirect('display_all_user')
        else:
            print('invalid form')
            print(form.errors)
     else:
        form = UserForm()
     context = {
        'form': form,
        'branch': branch,
    }
     return render(request, 'accounts/registerusermasterintelligent.html', context)



@login_required(login_url='login')
def myAccount(request):
    user = request.user
    redirectUrl = detectUser(user)
    return redirect(redirectUrl)

@login_required(login_url='login')
def dashboard(request):
    # member = Member.objects.filter(status=1).count()
    # member_inctive = Member.objects.filter(status=2).count()
    # member_male = Member.objects.filter(gender=1).count()
    # member_female = Member.objects.filter(gender=2).count()
    # member_single = Member.objects.filter(marital_status=1).count()
    # member_married = Member.objects.filter(marital_status=2).count()
    

    # context = {
    #     'member': member,
    #     'member_inctive': member_inctive,
    #     'member_male': member_male,
    #     'member_female': member_female,
    #     'member_single': member_single,
    #     'member_married': member_married,
    # }
    return render(request, 'accounts/dashboard.html')








@login_required(login_url='login')
@user_passes_test(check_role_admin)
def change_password(request):
    return render(request, 'accounts/change_password.html')

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def user_admin(request):
    return render(request, 'accounts/user_admin.html')
@login_required(login_url='login')
@user_passes_test(check_role_admin)
def display_all_user(request):
    # Assuming request.user is linked to a Branch instance via a ForeignKey
    branch = request.user.branch  # Get the branch associated with the logged-in user
    company_name = branch.company_name  # Extract the company name

    # Filter users whose branch's company_name matches the current user's company_name
    users = User.objects.filter(branch__company_name=company_name)

    return render(request, 'accounts/display_all_user.html', {'users': users})



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def edit_user(request, id):
    userrole = User.objects.get(id=id)
    branch = Branch.objects.filter(company__company_name=request.user.branch.company.company_name)

    customer = Customer.objects.filter(gl_no__startswith='1')
 
    if request.method == 'POST':
        form = EdituserForm(request.POST, request.FILES, instance=userrole)
        if form.is_valid():
            form.save()
            return redirect('display_all_user')  # Redirect to a user list view
    else:
        form = EdituserForm(instance=userrole)

    return render(request, 'accounts/update_user.html', {'form': form,'branch':branch,'customer':customer})

# def login(request):
#     if request.user.is_authenticated:
#         messages.warning(request, 'You are already logged in!')
#         return redirect('myAccount')
#     elif request.method == 'POST':
#         email = request.POST['email']
#         password = request.POST['password']

#         user = auth.authenticate(email=email, password=password)

#         if user is not None:
#             auth.login(request, user)
#             # messages.success(request, 'You are now logged in.')
#             return redirect('myAccount')
#         else:
#             # messages.error(request, 'Invalid login credentials')
#             return redirect('login')
#     return render(request, 'accounts/login.html')


import threading
from random import randint
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging

# adjust this import path to where your utils.py actually lives
from .utils import send_sms

logger = logging.getLogger(__name__)


def _send_otp_background(user_id, otp, phone_number, email, branch):
    """
    Send OTP via SMS (Termii) and Email in a background thread.
    Accepts exactly: user_id, otp, phone_number, email, branch.
    Debug prints are included to follow background execution in console.
    """
    print(f"[DEBUG-BG] called _send_otp_background(user_id={user_id!r}, otp={otp!r}, "
          f"phone_number={phone_number!r}, email={email!r}, branch={getattr(branch, 'id', None)!r})")
    logger.debug(f"[BG] start sending otp for user {user_id}")

    # --- Input validation & sanitization ---
    if not isinstance(otp, int) or not (100000 <= otp <= 999999):
        logger.error(f"[OTP] Invalid OTP for user {user_id}: {otp}")
        print(f"[DEBUG-BG] ❌ Invalid OTP: {otp!r}")
        return

    if phone_number is not None and not isinstance(phone_number, str):
        phone_number = str(phone_number)

    if email:
        if not isinstance(email, str) or '@' not in email:
            logger.error(f"[EMAIL] Invalid email for user {user_id}: {email!r}")
            print(f"[DEBUG-BG] ❌ Invalid email: {email!r}")
            email = None

    print(f"[DEBUG-BG] 🚀 Sending OTP {otp} | Phone: {phone_number!r} | Email: {email!r}")

    try:
        # --- SMS via send_sms helper ---
        if phone_number:
            try:
                print(f"[DEBUG-BG][SMS] Attempting to send SMS to {phone_number}")
                sms_message = f"Your OTP code is: {otp}"
                sms_ok = False
                if send_sms:
                    sms_ok = send_sms(phone_number, sms_message, branch=branch)
                else:
                    print("[DEBUG-BG][SMS] send_sms helper not available (import issue)")

                if sms_ok:
                    print(f"[SMS] ✅ OTP sent to {phone_number}")
                    logger.info(f"[SMS] OTP sent to {phone_number} for user {user_id}")
                else:
                    print(f"[SMS] ⚠️ Failed to send OTP to {phone_number}")
                    logger.warning(f"[SMS] Failed to send OTP to {phone_number} for user {user_id}")

            except Exception as sms_exc:
                logger.exception(f"[SMS-ERROR] Error sending SMS for user {user_id}: {sms_exc}")
                print(f"[DEBUG-BG][SMS] Exception while sending SMS: {sms_exc}")

        # --- Email ---
        if email:
            try:
                print(f"[DEBUG-BG][EMAIL] Preparing email to {email}")
                subject = "Your OTP Code"
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [email]

                company_name = getattr(branch, "company_name", "Support Team")
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

                msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                print(f"[EMAIL] ✅ OTP sent to {email}")
                logger.info(f"[EMAIL] OTP sent to {email} for user {user_id}")

            except Exception as email_exc:
                logger.exception(f"[EMAIL-ERROR] Failed sending OTP email to {email} for user {user_id}: {email_exc}")
                print(f"[DEBUG-BG][EMAIL] Exception while sending email: {email_exc}")

        print("[DEBUG-BG] ✅ Background OTP delivery completed")
        logger.debug(f"[BG] completed sending otp for user {user_id}")

    except Exception as e:
        logger.exception(f"[ERROR-BG] OTP delivery failed for user {user_id}: {e}")
        print(f"[DEBUG-BG] ⚠️ Background error: {e}")


def login(request):
    if request.user.is_authenticated:
        print("[DEBUG] User already authenticated → redirect to myAccount")
        logger.debug("User already authenticated; redirecting to myAccount")
        return redirect('myAccount')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')

        print(f"[DEBUG] Login attempt for email: {email!r}")
        logger.debug(f"Login attempt for email: {email!r}")

        if not email or not password:
            messages.error(request, "Email and password are required.")
            print("[DEBUG] Missing email or password")
            return render(request, 'accounts/login.html')

        try:
            user = authenticate(request, username=email, password=password)
            if user is None:
                messages.error(request, "Invalid email or password.")
                print("[DEBUG] Authentication failed")
                return redirect('login')

            print(f"[DEBUG] Authenticated user ID: {user.id}")
            logger.debug(f"Authenticated user id: {user.id}")

            # Account verification checks
            if not getattr(user, "verified", False):
                messages.error(request, "Your account is not verified. Please contact support.")
                print(f"[DEBUG] User {user.id} not verified")
                return redirect('login')

            if user.branch and user.branch.expire_date < timezone.now().date():
                messages.error(request, "Your branch license has expired.")
                print(f"[DEBUG] Branch license expired for branch id: {getattr(user.branch, 'id', None)}")
                return redirect('login')

            # Generate 6-digit OTP
            otp = randint(100000, 999999)
            print(f"[DEBUG] Generated OTP: {otp}")
            logger.debug(f"Generated OTP for user {user.id}")

            # Store in session (for OTP verification step)
            request.session['otp_data'] = {
                'user_id': user.id,
                'otp': otp,
                'timestamp': timezone.now().isoformat()
            }
            print("[DEBUG] OTP stored in session")
            logger.debug("OTP stored in session for user %s", user.id)

            # Start background thread (using kwargs like before)
            kwargs = {
                'user_id': user.id,
                'otp': otp,
                'phone_number': getattr(user, 'phone_number', None),
                'email': getattr(user, 'email', None),
                'branch': getattr(user, 'branch', None)
            }
            print(f"[DEBUG] Starting background thread with kwargs: {kwargs}")
            thread = threading.Thread(target=_send_otp_background, kwargs=kwargs)
            thread.daemon = True
            thread.start()
            print("[DEBUG] 🚀 Background OTP thread started (using kwargs)")
            logger.debug("Background OTP thread started for user %s", user.id)

            messages.success(request, "OTP sent! Check your email and phone.")
            return redirect('verify_otp')

        except Exception as e:
            error_msg = str(e) or "An unexpected error occurred during login."
            logger.exception(f"[ERROR] Login failed for {email}: {error_msg}")
            print(f"[DEBUG] Login exception for {email}: {error_msg}")
            messages.error(request, error_msg)
            return redirect('login')

    return render(request, 'accounts/login.html')


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.core.cache import cache
from django.utils import timezone
import logging
from .models import User  # Adjust to your actual User model
from .utils import send_sms  # 👈 import your SMS util

logger = logging.getLogger(__name__)


def verify_otp(request):
    # ✅ Step 1: Ensure session data is present
    if 'otp_data' not in request.session:
        messages.error(request, "OTP session expired. Please log in again.")
        return redirect('login')

    otp_data = request.session['otp_data']
    user_id = otp_data.get('user_id')
    session_otp = otp_data.get('otp')
    otp_timestamp = otp_data.get('timestamp')  # Optional for expiry check

    # ✅ Fetch user
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('login')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        action = request.POST.get('action')  # e.g. "verify" or "resend"

        # ✅ Handle OTP resend
        if action == "resend":
            from random import randint
            new_otp = randint(100000, 999999)

            # Store in session + cache
            request.session['otp_data']['otp'] = new_otp
            cache.set(f'otp_{user_id}', new_otp, timeout=300)  # 5 min expiry

            # Send SMS
            if getattr(user, "phone_number", None):
                message = f"Your OTP code is {new_otp}. It will expire in 5 minutes."
                logger.debug(f"[OTP-RESEND] Sending new OTP {new_otp} to {user.phone_number}")
                send_sms(user.phone_number, message)

            messages.success(request, "A new OTP has been sent to your phone.")
            return redirect('verify_otp')

        # ✅ Step 2: Check cache
        cache_otp = cache.get(f'otp_{user_id}')
        logger.debug(
            f"Verifying OTP for user {user_id}: "
            f"Cache={cache_otp}, Session={session_otp}, Entered={entered_otp}"
        )

        # ✅ Step 3: Validate OTP
        if entered_otp and (str(entered_otp) == str(session_otp) or str(entered_otp) == str(cache_otp)):
            auth_login(request, user)

            # ✅ Step 4: Cleanup
            cache.delete(f'otp_{user_id}')
            request.session.pop('otp_data', None)

            messages.success(request, "Logged in successfully!")
            return redirect('myAccount')

        else:
            messages.error(request, "Invalid OTP.")

    return render(request, 'accounts/verify_otp.html', {"user": user})



# views.py
import logging
from django.shortcuts import redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from .models import User  # Make sure this is your actual User model

logger = logging.getLogger(__name__)

# views.py


import threading
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from .models import User
import logging

logger = logging.getLogger(__name__)

# Background task function WITH debug prints
import threading
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from .models import User
import logging

logger = logging.getLogger(__name__)

# Background task function WITH debug prints
# def _send_otp_background(phone_number, email, otp, branch, request):
    # """Send OTP in background thread"""
    # print(f"[DEBUG-BG] 🚀 Background OTP delivery started")
    # print(f"[DEBUG-BG] Phone: {phone_number}, Email: {email}, OTP: {otp}")
    
    # sent_any = False
    
    # # Send SMS if phone exists
    # if phone_number:
    #     print(f"[DEBUG-BG] 📱 Processing SMS for: {phone_number}")
    #     try:
    #         # Format phone number
    #         if not phone_number.startswith('+'):
    #             formatted_phone = f"+{phone_number.lstrip('+')}"
    #         else:
    #             formatted_phone = phone_number
                
    #         print(f"[DEBUG-BG] 📱 Formatted phone: {formatted_phone}")
            
    #         sms_success = _send_otp_sms(formatted_phone, f"Your FinanceFlex OTP is {otp}", branch)
    #         print(f"[DEBUG-BG] 📱 SMS result: {'✅ Success' if sms_success else '❌ Failed'}")
            
    #         if sms_success:
    #             # Note: messages in background threads may not work reliably
    #             sent_any = True
    #         else:
    #             logger.warning(f"Background SMS failed for {formatted_phone}")
    #     except Exception as e:
    #         print(f"[DEBUG-BG] 📱 SMS exception: {str(e)}")
    #         logger.error(f"Background SMS error: {e}")
    # else:
    #     print("[DEBUG-BG] 📱 No phone number provided")

    # # Send Email if email exists
    # if email:
    #     print(f"[DEBUG-BG] 📧 Processing email for: {email}")
    #     try:
    #         send_mail(
    #             subject="FinanceFlex: Your OTP Code",
    #             message=f"Your one-time password is: {otp}\n\nValid for 5 minutes.",
    #             from_email=settings.DEFAULT_FROM_EMAIL,
    #             recipient_list=[email],
    #             fail_silently=False,
    #         )
    #         print("[DEBUG-BG] 📧 Email sent successfully")
    #         sent_any = True
    #     except Exception as e:
    #         print(f"[DEBUG-BG] 📧 Email exception: {str(e)}")
    #         logger.error(f"Background email error: {e}")
    # else:
    #     print("[DEBUG-BG] 📧 No email provided")

    # print(f"[DEBUG-BG] ✅ Background delivery completed. Sent: {sent_any}")

def resend_otp(request):
    print("[DEBUG] === RESEND OTP REQUEST STARTED ===")
    
    if request.method != "POST":
        print("[DEBUG] ❌ Non-POST request received")
        return redirect("verify_otp")

    otp_data = request.session.get('otp_data')
    if not otp_data:
        print("[DEBUG] ❌ otp_data not found in session")
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login')

    print(f"[DEBUG] ✅ Found otp_data: {otp_data}")
    
    user_id = otp_data.get('user_id')
    if not user_id:
        print("[DEBUG] ❌ user_id missing in otp_data")
        messages.error(request, "User info missing. Please log in again.")
        return redirect('login')

    try:
        user = User.objects.get(pk=user_id)
        phone_number = getattr(user, 'phone_number', None)
        email = user.email
        print(f"[DEBUG] 👤 User found: {user.email} | Phone: {phone_number}")

        # Generate new OTP
        new_otp = str(randint(100000, 999999))
        otp_data['otp'] = new_otp
        request.session['otp_data'] = otp_data
        print(f"[DEBUG] 🔑 New OTP generated: {new_otp}")

        # ✅ START BACKGROUND TASK
        print("[DEBUG] 🚀 Starting background delivery thread...")
        thread = threading.Thread(
            target=_send_otp_background,
            args=(phone_number, email, new_otp, user.branch, request)
        )
        thread.daemon = True
        thread.start()
        print("[DEBUG] ✅ Background thread started successfully")

        messages.success(request, "OTP delivery initiated! Check your phone and email shortly.")
        
    except User.DoesNotExist:
        print(f"[DEBUG] ❌ User with ID {user_id} does not exist")
        messages.error(request, "Account not found. Please log in again.")
        return redirect('login')
    except Exception as e:
        print(f"[DEBUG] 🚨 Unexpected error: {str(e)}")
        logger.error(f"Resend OTP error: {str(e)}")
        messages.error(request, "Failed to initiate OTP resend.")

    print("[DEBUG] === RESEND OTP REQUEST COMPLETED ===")
    return redirect("verify_otp")



def logout(request):
    auth.logout(request)
    # messages.info(request, 'You are logged in.')
    return redirect('login')






@login_required(login_url='login')
@user_passes_test(check_role_admin)
def profile(request):
    if request.method == 'POST':
        form = UserProfilePictureForm(request.POST, request.FILES, instance=request.user)
    
        if form.is_valid():
            form.save()
            messages.info(request, 'Updated.')
            return redirect('profile')  # Redirect to the user's profile page
    else:
        form = UserProfilePictureForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})




# def profile(request):
#     if request.method == 'POST':
#         form = UserProfilePictureForm(request.POST, request.FILES)
    
#         if form.is_valid():
#             user_profile = UserProfile.objects.get(user=request.user)
#             form = UserProfilePictureForm(request.POST, request.FILES, instance=user_profile)
#             form.save()
#             messages.info(request, 'Updated.')
#             return redirect('profile')  # Redirect to the user's profile page
#     else:
        
#         user_profile = UserProfile.objects.get(user=request.user)
#         form = UserProfilePictureForm(instance=user_profile)

#     return render(request, 'accounts/profile.html', {'form': form})
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import login as auth_login

def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        # Log them in but DON'T verify yet
        user.verified = True
        auth_login(request, user)
        
        # Always redirect to create branch (even if they have one)
        messages.info(request, 'Please create a branch to complete your registration.')
        return redirect('create_branch')
    else:
        messages.error(request, 'The activation link is invalid or has expired.')
        return redirect('login')

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email__exact=email)

            # send reset password email
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
    # validate the user by decoding the token and user pk
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


def change_password(request):
   
    return render(request, 'accounts/change_password.html')

def delete_user(request, id):
    user = User.objects.get(id=id)

    user.delete()
    return redirect('display_all_user')  # Redirect to the user list page after deletion

    # return render(request, 'delete_user.html', {'user': user})





from django.shortcuts import render

def contact_support(request):
    return render(request, 'contact_support.html')  # Create this template