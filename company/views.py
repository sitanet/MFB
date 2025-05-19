from django.shortcuts import render, get_object_or_404, redirect

from accounts.views import check_role_admin
from .models import Company, Branch
from .forms import CompanyForm, BranchForm, EndSession
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test


def company_list(request):
    companies = Company.objects.all()
    return render(request, 'company/company_list.html', {'companies': companies})


def branch_list(request):
    branches = Branch.objects.all()
    return render(request, 'branch/branch_list.html', {'branches': branches})



def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk)
    return render(request, 'company/company_detail.html', {'company': company})



def branch_detail(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    return render(request, 'branch/branch_detail.html', {'branch': branch})


def create_company(request):
    if request.method == "POST":
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('company_list')  # Redirect to the company list page
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

def _send_otp_sms(phone_number, message, branch=None):
    """Send OTP via Termii API with basic logging"""
    try:
        if not phone_number or not phone_number.startswith('+'):
            logger.error(f"Invalid phone number: {phone_number}")
            return False

        response = requests.post(
            settings.TERMII_SMS_URL,
            json={
                "api_key": settings.TERMII_API_KEY,
                "to": phone_number,
                "from": settings.TERMII_SENDER_ID,
                "sms": message,
                "type": "plain",
                "channel": "generic"
            },
            timeout=15
        )
        response_data = response.json()

        # Create delivery record
        SmsDelivery.objects.create(
            branch=branch,
            phone_number=phone_number,
            message=message,
            status='sent' if response_data.get('code') == 'ok' else 'failed'
        )

        return response_data.get('code') == 'ok'
        
    except Exception as e:
        logger.error(f"SMS error: {str(e)}")
        SmsDelivery.objects.create(
            branch=branch,
            phone_number=phone_number,
            message=message,
            status='error'
        )
        return False
@login_required
def create_branch(request):
    try:
        # Remove the authentication check
        # if not request.user.is_authenticated:
        #     messages.error(request, 'You must be logged in to create a branch.')
        #     return redirect('login')

        # If user is authenticated and already has a branch, prevent creation
        if request.user.is_authenticated and hasattr(request.user, 'branch') and request.user.branch:
            messages.warning(request, 'Your account already has a branch.')
            return redirect('dashboard')

        if request.method == 'POST':
            form = BranchForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        branch = form.save(commit=False)
                        
                        # Only link to user if authenticated
                        if request.user.is_authenticated:
                            branch.user = request.user
                            branch.company_name = branch.branch_name
                            branch.phone_verified = False
                            branch.otp_code = str(random.randint(100000, 999999))
                            branch.save()

                            # Link user to branch
                            request.user.branch = branch
                            request.user.save()

                            # Send OTP only if user has a phone number
                            if hasattr(request.user, 'phone_number') and request.user.phone_number:
                                phone_number = request.user.phone_number
                                sms_sent = _send_otp_sms(
                                    phone_number,
                                    f"Your verification code: {branch.otp_code}",
                                    branch
                                )
                                if sms_sent:
                                    messages.success(request, 'Verification code sent to your phone.')
                                    return redirect('verify_phone')
                                else:
                                    messages.warning(request, 'OTP could not be sent. You can request it again later.')
                            else:
                                messages.warning(request, 'No phone number found for OTP verification.')
                        else:
                            # Handle unauthenticated branch creation
                            branch.save()
                            messages.success(request, 'Branch created successfully!')
                            return redirect('some_public_page')  # Redirect to a public page

                except ValueError as e:
                    messages.error(request, str(e))
                except Exception as e:
                    print(f"Error creating branch: {e}")  # Debugging
                    messages.error(request, "System error. Please try again.")
            else:
                # Show form errors
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        else:
            # Pre-fill form only if user is authenticated
            initial_data = {}
            if request.user.is_authenticated:
                initial_data = {
                    'branch_name': f"{request.user.first_name or request.user.username}'s Branch",
                    'phone_number': getattr(request.user, 'phone_number', '')
                }
            form = BranchForm(initial=initial_data)

        return render(request, 'branch/create_branch.html', {
            'form': form,
            'phone_valid': request.user.is_authenticated and 
                         hasattr(request.user, 'phone_number') and 
                         request.user.phone_number and 
                         request.user.phone_number.startswith('+')
        })

    except Exception as e:
        print(f"Unexpected error: {e}")  # Debugging
        messages.error(request, "A system error occurred. Please contact support.")
        return redirect('home')  # Redirect to a safe public page


        
# views.py
from django.contrib.auth.decorators import login_required

@login_required
def verify_phone(request):
    user = request.user
    if not user.branch:
        return redirect('create_branch')
    
    branch = user.branch
    
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '')
        if entered_otp == branch.otp_code:
            branch.phone_verified = True
            branch.save()
            messages.success(request, 'Phone verification successful!')
            return redirect('dashboard')
        messages.error(request, 'Invalid OTP. Please try again.')
    
    return render(request, 'branch/verify_phone.html')





from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
import random

@login_required
def resend_otp(request):
    user = request.user
    if not user.branch:
        return redirect('create_branch')

    branch = user.branch
    # Generate a new 6-digit OTP
    new_otp = str(random.randint(100000, 999999))
    branch.otp_code = new_otp
    branch.save()

    # TODO: Replace with actual SMS sending logic
    print(f"Resending OTP {new_otp} to {branch.phone_number}")

    # Show a success message and redirect to the verify phone page
    messages.success(request, 'A new OTP has been sent to your phone number.')
    return redirect('verify_phone')



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



def update_company(request, company_id):
    company = get_object_or_404(Company, pk=company_id)
    if request.method == "POST":
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            return redirect('company_list')
    else:
        form = CompanyForm(instance=company)
    return render(request, 'company/update_company.html', {'form': form, 'company': company})





# Function to update branch details along with company model
from django.shortcuts import get_object_or_404, redirect, render
from .models import Branch, Company
from .forms import BranchForm

def update_branch(request, id):
    # Get the branch object to update
    branch = get_object_or_404(Branch, pk=id)
    
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





def company_delete(request, id):
    company = get_object_or_404(Company, id=id)
    if request.method == 'POST':
        company.delete()
        return redirect('company_list')
    return render(request, 'company/company_confirm_delete.html', {'company': company})



def branch_delete(request, id):
    branch = get_object_or_404(Branch, id=id)
    if request.method == 'POST':
        branch.delete()
        return redirect('branch_list')
    return render(request, 'branch/branch_confirm_delete.html', {'branch': branch})

from .forms import EndSession


from django.utils import timezone
@login_required(login_url='login')
@user_passes_test(check_role_admin)
@login_required

def session_mgt(request):
    # Access the branch associated with the logged-in user
    branch = request.user.branch  # Assuming the 'branch' field is part of the User model

    if request.method == 'POST':
        form = EndSession(request.POST, instance=branch)
        if form.is_valid():
            # Check if session_status is "Open" and update system_date
            session_status = form.cleaned_data.get('session_status')
            if session_status == 'Open':
                branch.system_date_date = timezone.now()
            
            form.save()  # Save the branch instance
            messages.success(request, 'Session Change Successfully')
            return redirect('session_mgt')  # Redirect to the same page after successful update
    else:
        form = EndSession(instance=branch)
    
    return render(request, 'company/session_mgt.html', {'form': form})






from django.contrib.auth import get_user_model
from django.shortcuts import render

def display_users_and_branches(request):
    # Get the custom User model
    User = get_user_model()  
    
    # Fetch users and prefetch related branch and company data
    users = User.objects.select_related('branch', 'branch__company').all()

    # Pass the user data to the template
    return render(request, 'users/display_users_and_branches.html', {'users': users})
