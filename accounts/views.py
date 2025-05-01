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




from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator

User = get_user_model()

def register(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            # Create user but mark as inactive and unverified
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = True  # User can login but not access privileged areas
            user.verified = False  # Will be set to True after branch creation
            user.save()

            # Send activation email
            uid = urlsafe_base64_encode(str(user.pk).encode())
            token = default_token_generator.make_token(user)
            activation_link = request.build_absolute_uri(
                reverse('activate', kwargs={'uidb64': uid, 'token': token})
            )

            subject = 'Complete Your Registration'
            message = f'''
Dear {user.first_name},

Thank you for registering. To complete your setup, please click the link below 
to create your branch and activate your account:

{activation_link}

This link will expire in 24 hours.

Regards,
Admin Team
'''
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False
                )
                messages.success(request, 'Registration successful! Please check your email to complete setup.')
            except Exception as e:
                messages.warning(request, f'User created, but email could not be sent. Please contact support. Error: {str(e)}')
                # Consider logging this error for admin
                return redirect('contact_support')  # You should have some fallback

            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserForm()

    return render(request, 'accounts/public_reg.html', {'form': form})



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
    # users = User.objects.all()
    users = User.objects.filter(branch__company__company_name=request.user.branch.company.company_name)


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



# accounts/views.py
import logging
import random
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.cache import cache
from .models import Branch, User
from django.conf import settings



logger = logging.getLogger(__name__)

from django.contrib.auth import authenticate, login as auth_login
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone


def login(request):
    if request.user.is_authenticated:
        return redirect('myAccount')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = authenticate(request, username=email, password=password)
            if user is None:
                raise ValueError("Invalid credentials")

            # Check if user is verified
            if not user.verified:
                raise ValueError("Account not verified")

            # Check if branch exists — but allow if none, to let them log in and create
            if user.branch and user.branch.expire_date < timezone.now().date():
                raise ValueError("Branch license expired")

            # Log in user
            auth_login(request, user)
            return redirect('dashboard')

        except Exception as e:
            messages.error(request, str(e))
            return redirect('login')

    return render(request, 'accounts/login.html')


def verify_otp(request):
    # Check if user came from login flow
    if 'otp_data' not in request.session:
        messages.error(request, "OTP session expired. Login again.")
        return redirect('login')

    otp_data = request.session['otp_data']
    user_id = otp_data['user_id']

    if request.method == 'POST':
        user_entered_otp = request.POST.get('otp')

        # Check both cache and session storage
        cache_otp = cache.get(f'otp_{user_id}')
        session_otp = otp_data['otp']

        logger.debug(f"Verifying OTP for {user_id}. Cache: {cache_otp}, Session: {session_otp}, Entered: {user_entered_otp}")

        # CORRECTED LINE (removed extra parenthesis)
        if user_entered_otp and str(user_entered_otp) == str(session_otp):
            try:
                user = User.objects.get(pk=user_id)
                from django.contrib.auth import login as auth_login
                auth_login(request, user)
                
                # Cleanup
                cache.delete(f'otp_{user_id}')
                del request.session['otp_data']
                
                messages.success(request, "Logged in successfully!")
                return redirect('myAccount')

            except User.DoesNotExist:
                messages.error(request, "User not found!")
        else:
            messages.error(request, "Invalid OTP!")

    return render(request, 'accounts/verify_otp.html')

from django.shortcuts import redirect
from django.contrib import messages

def resend_otp(request):
    if request.method == "POST":
        phone_number = request.session.get('phone_number')  # Assuming phone_number is stored in session
        otp = request.session.get('otp')  # Assuming OTP is stored in session

        if phone_number and otp:
            # Resend the OTP using your Termii send_sms function
            send_sms(phone_number, f"Your OTP code is {otp}")
            messages.success(request, "OTP has been resent to your phone.")
        else:
            messages.error(request, "Unable to resend OTP. Please try again.")

    return redirect('verify_otp')  # Redirect back to the OTP verification page


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