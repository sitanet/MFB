# views.py
from django.shortcuts import get_object_or_404, render, redirect
from accounts.models import User

from accounts.views import check_role_admin
from company.models import Company, Branch
from .models import Account, Account_Officer, Business_Sector, Category, Id_card_type, LoanProvision, Product_type, Region
from .forms import AccountForm, BusinessSectorForm, CategoryForm, CreditOfficerForm, IdcardTypeForm, RegionForm, loanProductSettingsForm
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, JsonResponse
from django.shortcuts import render



@login_required(login_url='login')
@user_passes_test(check_role_admin)


@login_required

# def chart_of_accounts(request):
#     # Retrieve accounts specific to the user's branch company
#     accounts = Account.objects.filter(
#         header=None,
#         branch__company__company_name=request.user.branch.company.company_name
#     ).order_by('gl_no')
    
#     if request.method == 'POST':
#         form = AccountForm(request.POST)
#         if form.is_valid():
#             account = form.save(commit=False)
#             # Assign the logged-in user's branch to the new account
#             account.branch = request.user.branch

#             # Check for duplicate gl_no within the same branch
#             if Account.objects.filter(gl_no=account.gl_no, branch=account.branch).exists():
#                 form.add_error('gl_no', 'An account with this GL number already exists in your branch.')
#             else:
#                 account.save()
#                 messages.success(request, 'Account added successfully!')
#                 return redirect('chart_of_accounts')
#     else:
#         form = AccountForm()

#     # Retrieve accounts for the logged-in user's branch
#     account = Account.objects.filter(branch__company=request.user.branch.company).order_by('gl_no')
#     return render(request, 'accounts_admin/chart_of_accounts.html', {
#         'account': account,
#         'accounts': accounts,
#         'form': form,
#     })



@login_required
def chart_of_accounts(request):
    # Retrieve accounts specific to the user's company_name
    accounts = Account.objects.filter(
        header=None,
        branch__company_name=request.user.branch.company_name
    ).order_by('gl_no')
    
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            # Assign the logged-in user's branch to the new account
            account.branch = request.user.branch

            # Check for duplicate gl_no within the same branch
            if Account.objects.filter(gl_no=account.gl_no, branch=account.branch).exists():
                form.add_error('gl_no', 'An account with this GL number already exists in your branch.')
            else:
                account.save()
                messages.success(request, 'Account added successfully!')
                return redirect('chart_of_accounts')
    else:
        form = AccountForm()

    # Retrieve all accounts within the user's company_name
    account = Account.objects.filter(
        branch__company_name=request.user.branch.company_name
    ).order_by('gl_no')

    return render(request, 'accounts_admin/chart_of_accounts.html', {
        'account': account,
        'accounts': accounts,
        'form': form,
    })




# views.py
@login_required(login_url='login')
@user_passes_test(check_role_admin)
def account_settings(request):
    return render(request, 'accounts_admin/account_settings.html')


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def success_view(request):
    return render(request, 'accounts_admin/success.html')

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def update_chart_of_account(request, id):
    chart_of_account = Account.objects.get(id=id)
    
    # Filter the accounts based on the logged-in user's branch
    accounts = Account.objects.filter(header=None, branch=request.user.branch)
    
    form = AccountForm(instance=chart_of_account)

    if request.method == 'POST':
        form = AccountForm(request.POST, instance=chart_of_account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Edited successfully!')
            return redirect('chart_of_accounts')

    return render(request, 'accounts_admin/update_chart_of_account.html', {
        'form': form,
        'chart_of_account': chart_of_account,
        'accounts': accounts
    })

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def delete_chart_of_account(request, id):
    chart_of_account = Account.objects.get(id=id)
    chart_of_account.delete()
    messages.success(request, 'Delete successfully!.')
    return render(request, 'accounts_admin/confirm_delete.html')

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import Account


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def delete_chart_of_account(request, id):
    instance = get_object_or_404(Account, id=id)

    if request.method == 'POST':
        if instance.has_related_child_accounts():
            return render(request, 'accounts_admin/cannot_delete.html', {'instance': instance})

        instance.delete()
        return redirect('chart_of_accounts')

    return render(request, 'accounts_admin/confirm_delete.html', {'instance': instance})



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def cannot_delete(request):
    return render(request, 'accounts_admin/cannot_delete.html')


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def software_reg(request):
    return render(request, 'accounts_admin/software_reg.html')


@login_required(login_url='login')
@user_passes_test(check_role_admin)

@login_required
def create_account_officer(request):
    # Get the company_name associated with the current user
    user_company_name = request.user.branch.company_name  # Assuming user has a branch with company_name

    # Filter Region based on company_name instead of branch
    officer = Region.objects.filter(branch__company_name=user_company_name)

    # Filter Users who are associated with branches having the same company_name
    user_officer = User.objects.filter(branch__company_name=user_company_name)

    if request.method == "POST":
        form = CreditOfficerForm(request.POST)
        if form.is_valid():
            # Save the form but don't commit yet
            account_officer = form.save(commit=False)
            # Assign the user's branch to the new account officer
            account_officer.branch = request.user.branch
            account_officer.save()
            return redirect('account_officer_list')
    else:
        form = CreditOfficerForm()

    return render(request, 'accounts_admin/account_officer/create_account_officer.html', {
        'form': form,
        'officer': officer,
        'user_officer': user_officer,
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def account_officer_list(request):
    # Get the branch associated with the current user
    user_branch = request.user.branch  # Assuming user has a 'branch' attribute

    # Filter Account_Officer based on the user's company_name (through region -> branch)
    officers = Account_Officer.objects.filter(region__branch__company_name=user_branch.company_name)

    # Filter regions (branches) based on the same company_name
    branches = Region.objects.filter(branch__company_name=user_branch.company_name)

    return render(
        request, 
        'accounts_admin/account_officer/account_officer_list.html', 
        {'officers': officers, 'branches': branches}
    )



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def update_account_officer(request, id):
    officer = get_object_or_404(Account_Officer, id=id)
    branches = Company.objects.all()  # Retrieve the list of branches or adjust the query as needed

    if request.method == "POST":
        form = CreditOfficerForm(request.POST, instance=officer)
        if form.is_valid():
            form.save()
            return redirect('account_officer_list')
    else:
        form = CreditOfficerForm(instance=officer)
    return render(request, 'accounts_admin/account_officer/update_account_officer.html', {'form': form, 'officer': officer, 'branches': branches})


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def account_officer_delete(request, id):
    officer = get_object_or_404(Account_Officer, id=id)
    if request.method == 'POST':
        officer.delete()
        return redirect('account_officer_list')
    return render(request, 'accounts_admin/account_officer/officer_confirm_delete.html', {'officer': officer})





@login_required(login_url='login')
@user_passes_test(check_role_admin)

def create_region(request):
    # Get the branch associated with the current user
    user_branch = request.user.branch  # Assuming the user has a 'branch' attribute

    # Filter Region based on the user's branch
    # region = Region.objects.filter(branch=user_branch)
    
    if request.method == "POST":
        form = RegionForm(request.POST)
        if form.is_valid():
            # Save the form but don't commit yet
            new_region = form.save(commit=False)
            # Assign the user's branch to the new region
            new_region.branch = request.user.branch
            new_region.save()
            return redirect('region_list')  # Redirect to the region list page
    else:
        form = RegionForm()
    
    return render(request, 'accounts_admin/region/create_region.html', {
        'form': form,
        # 'region': region,
    })

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def region_list(request):
    # Get the company_name associated with the current user's branch
    user_company_name = request.user.branch.company_name

    # Filter Region based on branches with the same company_name
    region = Region.objects.filter(branch__company_name=user_company_name)
    
    return render(request, 'accounts_admin/region/region_list.html', {'region': region})


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def update_region(request, id):
    region = get_object_or_404(Region, id=id)
    
   
    if request.method == "POST":
        form = RegionForm(request.POST, instance=region)
        if form.is_valid():
            form.save()
            return redirect('region_list')
    else:
        form = RegionForm(instance=region)
    return render(request, 'accounts_admin/region/update_region.html', {'form': form, 'officer': region,'user': region})



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def region_delete(request, id):
    officer = get_object_or_404(Region, id=id)
    if request.method == 'POST':
        officer.delete()
        return redirect('region_list')
    return render(request, 'accounts_admin/region/region_confirm_delete.html', {'officer': officer})






@login_required(login_url='login')
@user_passes_test(check_role_admin)
def create_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            # Create the instance without saving to the database yet
            category = form.save(commit=False)
            
            # Automatically assign the user's branch
            category.branch = request.user.branch  # Assuming the user has a 'branch' attribute
            
            category.save()  # Save the instance to the database
            return redirect('category_list')  # Redirect to the category list page
    else:
        form = CategoryForm()
    
    return render(request, 'accounts_admin/customer_category/create_category.html', {'form': form})


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def category_list(request):
    # Get the company_name associated with the current user's branch
    user_company_name = request.user.branch.company_name

    # Filter categories based on the user's company_name
    category = Category.objects.filter(branch__company_name=user_company_name)
    
    return render(request, 'accounts_admin/customer_category/category_list.html', {'category': category})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def update_category(request, id):
    category = get_object_or_404(Category, id=id)
    
   
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'accounts_admin/customer_category/update_category.html', {'form': form})



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def category_delete(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == 'POST':
        category.delete()
        return redirect('category_list')
    return render(request, 'accounts_admin/customer_category/category_delete.html', {'category': category})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def create_id_type(request):
    if request.method == "POST":
        form = IdcardTypeForm(request.POST)
        if form.is_valid():
            id_type = form.save(commit=False)  # Create the instance without saving to the database
            id_type.branch = request.user.branch  # Automatically assign the user's branch
            id_type.save()  # Save the instance to the database
            return redirect('id_type_list')  # Redirect to the ID type list page
    else:
        form = IdcardTypeForm()
    return render(request, 'accounts_admin/id_type/create_id_type.html', {'form': form})


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def id_type_list(request):
    # Get the company_name associated with the current user's branch
    user_company_name = request.user.branch.company_name

    # Filter Id_card_type by branches with the same company_name
    id_type = Id_card_type.objects.filter(branch__company_name=user_company_name)
    
    return render(request, 'accounts_admin/id_type/id_type_list.html', {'id_type': id_type})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def update_id_type(request, id):
    id_type = get_object_or_404(Id_card_type, id=id)
    
   
    if request.method == "POST":
        form = IdcardTypeForm(request.POST, instance=id_type)
        if form.is_valid():
            form.save()
            return redirect('id_type_list')
    else:
        form = IdcardTypeForm(instance=id_type)
    return render(request, 'accounts_admin/id_type/update_id_type.html', {'form': form})



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def id_type_delete(request, id):
    id_type = get_object_or_404(Id_card_type, id=id)
    if request.method == 'POST':
        id_type.delete()
        return redirect('id_type_list')
    return render(request, 'accounts_admin/id_type/id_type_delete.html', {'id_type': id_type})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def user_define(request):
    return render(request, 'accounts_admin/user_define.html')


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def create_bus_sector(request):
    # Get the company_name of the logged-in user's branch
    user_company_name = request.user.branch.company_name

    # Retrieve all existing business sectors for the same company
    region = Business_Sector.objects.filter(branch__company_name=user_company_name)

    if request.method == "POST":
        form = BusinessSectorForm(request.POST)
        if form.is_valid():
            # Create the instance without saving to set the branch
            bus_sector = form.save(commit=False)
            # Automatically assign the logged-in user's branch
            bus_sector.branch = request.user.branch
            # Save the instance to the database
            bus_sector.save()
            return redirect('bus_sec_list')
    else:
        form = BusinessSectorForm()

    return render(request, 'accounts_admin/business_sector/create_bus_sector.html', {
        'form': form,
        'region': region,
    })



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def bus_sec_list(request):
    # Get the company name of the logged-in user's branch
    user_company_name = request.user.branch.company_name

    # Filter business sectors by all branches under the same company
    bus_sec = Business_Sector.objects.filter(branch__company_name=user_company_name)

    return render(request, 'accounts_admin/business_sector/bus_sec_list.html', {'bus_sec': bus_sec})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def update_bus_sector(request, id):
    bus_sec = get_object_or_404(Business_Sector, id=id)
    
   
    if request.method == "POST":
        form = BusinessSectorForm(request.POST, instance=bus_sec)
        if form.is_valid():
            form.save()
            return redirect('bus_sec_list')
    else:
        form = BusinessSectorForm(instance=bus_sec)
    return render(request, 'accounts_admin/business_sector/update_bus_sector.html', {'form': form, 'bus_sec': bus_sec,'bus_sec': bus_sec})



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def bus_sec_delete(request, id):
    bus_sec = get_object_or_404(Business_Sector, id=id)
    if request.method == 'POST':
        bus_sec.delete()
        return redirect('bus_sec_list')
    return render(request, 'accounts_admin/business_sector/bus_sec_confirm_delete.html', {'bus_sec': bus_sec})


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def product_settings(request):
   
    return render(request, 'accounts_admin/product_settings/product_setting.html')



# views.py

# views.py
from django.shortcuts import render, redirect
from .forms import ProductTypeForm




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def create_product_type(request):
    if request.method == 'POST':
        form = ProductTypeForm(request.POST)
        if form.is_valid():
            product_type = form.save(commit=False)  # Create the instance without saving
            product_type.branch = request.user.branch  # Automatically assign the user's branch
            product_type.save()  # Save the instance to the database
            messages.success(request, 'Added successfully!')
            return redirect('create_product_type')  # Redirect to the same page after saving
    else:
        form = ProductTypeForm()

    return render(request, 'create_product_type.html', {'form': form})








# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .forms import UpdateProductTypeForm


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def update_product_type(request):
    if request.method == 'POST':
        form = UpdateProductTypeForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            product_type = form.cleaned_data['product_type']

            # Update the product_type
            account.product_type = product_type
            account.save()
            messages.success(request, 'Add successfully!.')
            return redirect('update_product_type')

            
    else:
        form = UpdateProductTypeForm()

    return render(request, 'update_product_type.html', {'form': form})



from django.shortcuts import render, redirect, get_object_or_404
from .forms import loanProductSettingsForm  # Replace with your actual form
from .models import Account


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def update_account_old(request):
    if request.method == 'POST':
        form = loanProductSettingsForm(request.POST)
        if form.is_valid():
            gl_no = form.cleaned_data['gl_no']
            print("Debug: gl_no =", gl_no)
            account = get_object_or_404(Account, gl_no=gl_no)
            # Pass the account instance to the form so it's aware of the selected account
            form = loanProductSettingsForm(request.POST, instance=account)

            if form.is_valid():

                # Update the account fields based on the form data
                account.interest_gl = form.cleaned_data['interest_gl']
                account.interest_ac = form.cleaned_data['interest_ac']
                account.pen_gl_no = form.cleaned_data['pen_gl_no']
                account.pen_ac_no = form.cleaned_data['pen_ac_no']
                account.prov_cr_gl_no = form.cleaned_data['prov_cr_gl_no']
                account.prov_cr_ac_no = form.cleaned_data['prov_cr_ac_no']
                account.prov_dr_gl_no = form.cleaned_data['prov_dr_gl_no']
                account.prov_dr_ac_no = form.cleaned_data['prov_dr_ac_no']
                account.writ_off_dr_gl_no = form.cleaned_data['writ_off_dr_gl_no']
                account.writ_off_dr_ac_no = form.cleaned_data['writ_off_dr_ac_no']
                account.writ_off_cr_gl_no = form.cleaned_data['writ_off_cr_gl_no']
                account.writ_off_cr_ac_no = form.cleaned_data['writ_off_cr_ac_no']
                account.loan_com_gl_no = form.cleaned_data['loan_com_gl_no']
                account.loan_com_ac_no = form.cleaned_data['loan_com_ac_no']
                account.int_to_recev_gl_dr = form.cleaned_data['int_to_recev_gl_dr']
                account.int_to_recev_ac_dr = form.cleaned_data['int_to_recev_ac_dr']
                account.unearned_int_inc_gl = form.cleaned_data['unearned_int_inc_gl']
                account.unearned_int_inc_ac = form.cleaned_data['unearned_int_inc_ac']
                account.loan_com_gl_vat = form.cleaned_data['loan_com_gl_vat']
                account.loan_com_ac_vat = form.cleaned_data['loan_com_ac_vat']
                account.loan_proc_gl_vat = form.cleaned_data['loan_proc_gl_vat']
                account.loan_proc_ac_vat = form.cleaned_data['loan_proc_ac_vat']
                account.loan_appl_gl_vat = form.cleaned_data['loan_appl_gl_vat']
                account.loan_appl_ac_vat = form.cleaned_data['loan_appl_ac_vat']
                account.loan_commit_gl_vat = form.cleaned_data['loan_commit_gl_vat']
                account.loan_commit_ac_vat = form.cleaned_data['loan_commit_ac_vat']

                # Save the changes to the account
                account.save()

                return redirect('success_page')  # Redirect to a success page
    else:
        form = loanProductSettingsForm()
        print(form.errors)

    accounts = Account.objects.all()
    return render(request, 'update_account.html', {'form': form, 'accounts': accounts})

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def account_list(request):
    # Get the company name from the user's branch
    user_company_name = request.user.branch.company_name

    # Filter accounts by company name and order by GL number
    accounts = Account.objects.filter(branch__company_name=user_company_name).order_by('gl_no')

    return render(request, 'account_list.html', {'accounts': accounts})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def update_account(request, id):
    # Ensure the user is assigned to a branch
    user_branch = getattr(request.user, 'branch', None)
    if not user_branch:
        messages.error(request, "You are not assigned to any branch. Contact the administrator.")
        return redirect('account_list')

    user_company = user_branch.company  # Get the user's company

    # Get the account, ensuring it belongs to the same company
    account = get_object_or_404(Account, id=id, branch__company=user_company)

    # Optional: Fetch only branches in the user's company for dropdown or reference
    cust_branch = Branch.objects.filter(company=user_company)

    if request.method == 'POST':
        form = loanProductSettingsForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account updated successfully!')
            return redirect('account_list')
    else:
        initial_data = {'gl_no': account.gl_no}
        form = loanProductSettingsForm(instance=account, initial=initial_data)

    return render(request, 'update_account.html', {
        'form': form,
        'account': account,
        'cust_branch': cust_branch,
    })



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def delete_account(request, id):
    account = get_object_or_404(Account, id=id)
    if request.method == 'POST':
        account.delete()
        messages.success(request, 'Account saved successfully!')
        return redirect('account_list')
    return render(request, 'delete_account.html', {'account': account})

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def utilities(request):
    return render(request, 'accounts_admin/utilities.html')



from django.shortcuts import render, redirect
# from .models import InterestRate
# from .forms import InterestRateForm

from django.db.models import Sum



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def add_interest_rate(request):
    if request.method == 'POST':
        form = InterestRateForm(request.POST)
        if form.is_valid():
            interest_rate = form.save(commit=False)  # Create the instance without saving
            interest_rate.branch = request.user.branch  # Automatically assign the user's branch
            interest_rate.save()  # Save the instance to the database
            return redirect('success')  # Redirect to a success page
    else:
        form = InterestRateForm()

    return render(request, 'accounts_admin/add_interest_rate.html', {'form': form})





from django.shortcuts import render, redirect
from .forms import LoanProvisionFormSet

# loans/views.py

from django.shortcuts import render, redirect
from .forms import LoanProvisionFormSet

# views.py

from django.shortcuts import render, redirect
from .models import LoanProvision
from .forms import LoanProvisionForm



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def add_loan_provision(request):
    if request.method == 'POST':
        names = request.POST.getlist('name[]')
        min_days_list = request.POST.getlist('min_days[]')
        max_days_list = request.POST.getlist('max_days[]')
        rates = request.POST.getlist('rate[]')

        for name, min_days, max_days, rate in zip(names, min_days_list, max_days_list, rates):
            LoanProvision.objects.create(
                name=name,
                min_days=min_days,
                max_days=max_days,
                rate=rate,
                branch=request.user.branch  # Automatically assign the user's branch
            )
        return redirect('loan_provision_list')

    return render(request, 'accounts_admin/loan_provision/add_loan_provision.html')

# loans/views.py

from django.shortcuts import render
from .models import LoanProvision

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def loan_provision_list(request):
    user_branch = getattr(request.user, 'branch', None)
    if not user_branch:
        messages.error(request, "You are not assigned to any branch. Contact the administrator.")
        return redirect('home')  # Or appropriate redirect

    user_company = user_branch.company

    # Filter provisions by branches belonging to the user's company
    provisions = LoanProvision.objects.filter(branch__company=user_company)

    return render(request, 'accounts_admin/loan_provision/loan_provision_list.html', {'provisions': provisions})


# loans/views.py

from django.shortcuts import render, redirect, get_object_or_404
from .models import LoanProvision
from .forms import LoanProvisionForm

def edit_loan_provision(request, pk):
    loan_provision = get_object_or_404(LoanProvision, pk=pk)
    if request.method == 'POST':
        form = LoanProvisionForm(request.POST, instance=loan_provision)
        if form.is_valid():
            form.save()
            return redirect('loan_provision_list')
    else:
        form = LoanProvisionForm(instance=loan_provision)
    
    return render(request, 'accounts_admin/loan_provision/edit_loan_provision.html', {'form': form})


# loans/views.py

def delete_loan_provision(request, pk):
    loan_provision = get_object_or_404(LoanProvision, pk=pk)
    if request.method == 'POST':
        loan_provision.delete()
        return redirect('loan_provision_list')
    
    return render(request, 'accounts_admin/loan_provision/delete_loan_provision.html', {'loan_provision': loan_provision})
