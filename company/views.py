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




def create_branch(request):
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
