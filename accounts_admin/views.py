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
@user_passes_test(check_role_admin)
def chart_of_accounts(request):
    from accounts.utils import get_company_branch_ids_all, get_branch_from_vendor_db
    
    # Get user's branch and company
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    
    if not user_branch:
        messages.error(request, 'No branch assigned to your account. Please contact administrator to assign you to a branch.')
        return redirect('dashboard')
    
    # Get company for this user (chart of accounts is company-wide)
    branch_ids = get_company_branch_ids_all(request.user)
    user_company = user_branch.company if user_branch else None
    
    # Retrieve accounts for the entire company (visible to all branches)
    # Query by branch_ids and get distinct by gl_no to avoid duplicates
    accounts = Account.all_objects.filter(
        header=None,
        branch_id__in=branch_ids
    ).order_by('gl_no').distinct('gl_no')
    
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            # Assign company and branch to the new account
            account.company = user_company
            account.branch = user_branch

            # Check for duplicate gl_no within the same COMPANY
            if Account.all_objects.filter(gl_no=account.gl_no, company=user_company).exists():
                form.add_error('gl_no', 'An account with this GL number already exists in your company.')
            else:
                account.save()
                messages.success(request, 'Account added successfully! It is now visible to all branches in your company.')
                return redirect('chart_of_accounts')
    else:
        form = AccountForm()

    # Retrieve all accounts within the company (distinct by gl_no to avoid duplicates)
    account = Account.all_objects.filter(
        branch_id__in=branch_ids
    ).order_by('gl_no').distinct('gl_no')

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
def update_chart_of_account(request, uuid):
    from accounts.utils import get_company_branch_ids_all
    
    chart_of_account = Account.all_objects.get(uuid=uuid)
    
    # Get all branch IDs for this company (chart of accounts is always company-wide)
    branch_ids = get_company_branch_ids_all(request.user)
    
    # Filter the accounts based on the company (visible to all branches)
    accounts = Account.all_objects.filter(header=None, branch_id__in=branch_ids)
    
    form = AccountForm(instance=chart_of_account)

    if request.method == 'POST':
        form = AccountForm(request.POST, instance=chart_of_account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account updated successfully!')
            return redirect('chart_of_accounts')

    return render(request, 'accounts_admin/update_chart_of_account.html', {
        'form': form,
        'chart_of_account': chart_of_account,
        'accounts': accounts
    })

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def delete_chart_of_account(request, uuid):
    instance = get_object_or_404(Account, uuid=uuid)

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
def create_account_officer(request):
    from accounts.utils import get_branch_from_vendor_db
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    user_company = user_branch.company if user_branch else None

    # Filter Region based on company
    region_queryset = Region.objects.filter(branch__company=user_company) if user_company else Region.objects.none()

    # Filter Users who are associated with branches having the same company
    from accounts.utils import get_company_branch_ids_all
    branch_ids = get_company_branch_ids_all(request.user)
    user_officer = User.objects.filter(branch_id__in=branch_ids)

    if request.method == "POST":
        form = CreditOfficerForm(request.POST)
        form.fields['region'].queryset = region_queryset
        if form.is_valid():
            user_value = form.cleaned_data.get('user')
            if Account_Officer.objects.filter(user=user_value).exists():
                form.add_error('user', 'An account officer with this user already exists in this branch.')
            else:
                account_officer = form.save(commit=False)
                account_officer.branch = user_branch
                account_officer.save()
                return redirect('account_officer_list')
    else:
        form = CreditOfficerForm()
        form.fields['region'].queryset = region_queryset

    return render(request, 'accounts_admin/account_officer/create_account_officer.html', {
        'form': form,
        'officer': region_queryset,
        'user_officer': user_officer,
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def account_officer_list(request):
    from accounts.utils import get_branch_from_vendor_db
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    user_company = user_branch.company if user_branch else None

    # Filter Account_Officer based on the user's company
    officers = Account_Officer.objects.filter(region__branch__company=user_company) if user_company else []

    # Filter regions based on the same company
    branches = Region.objects.filter(branch__company=user_company) if user_company else []

    return render(
        request, 
        'accounts_admin/account_officer/account_officer_list.html', 
        {'officers': officers, 'branches': branches}
    )



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def update_account_officer(request, uuid):
    officer = get_object_or_404(Account_Officer, uuid=uuid)
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
def account_officer_delete(request, uuid):
    officer = get_object_or_404(Account_Officer, uuid=uuid)
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
def update_region(request, uuid):
    region = get_object_or_404(Region, uuid=uuid)
    
   
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
def region_delete(request, uuid):
    officer = get_object_or_404(Region, uuid=uuid)
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
def update_category(request, uuid):
    category = get_object_or_404(Category, uuid=uuid)
    
   
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
def category_delete(request, uuid):
    category = get_object_or_404(Category, uuid=uuid)
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
def update_id_type(request, uuid):
    id_type = get_object_or_404(Id_card_type, uuid=uuid)
    
   
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
def id_type_delete(request, uuid):
    id_type = get_object_or_404(Id_card_type, uuid=uuid)
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
def update_bus_sector(request, uuid):
    bus_sec = get_object_or_404(Business_Sector, uuid=uuid)
    
   
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
def bus_sec_delete(request, uuid):
    bus_sec = get_object_or_404(Business_Sector, uuid=uuid)
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
    from accounts.utils import get_company_branch_ids_all
    
    # Get all branch IDs for this company (accounts list is always company-wide)
    branch_ids = get_company_branch_ids_all(request.user)

    # Filter accounts by company branches, distinct by gl_no to avoid duplicates
    accounts = Account.all_objects.filter(branch_id__in=branch_ids).order_by('gl_no').distinct('gl_no')

    return render(request, 'account_list.html', {'accounts': accounts})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def update_account(request, uuid):
    # Ensure the user is assigned to a branch
    user_branch = getattr(request.user, 'branch', None)
    if not user_branch:
        messages.error(request, "You are not assigned to any branch. Contact the administrator.")
        return redirect('account_list')

    user_company = user_branch.company  # Get the user's company

    # Get the account, ensuring it belongs to the same company
    account = get_object_or_404(Account, uuid=uuid, branch__company=user_company)

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
def delete_account(request, uuid):
    account = get_object_or_404(Account, uuid=uuid)
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

def edit_loan_provision(request, uuid):
    loan_provision = get_object_or_404(LoanProvision, uuid=uuid)
    if request.method == 'POST':
        form = LoanProvisionForm(request.POST, instance=loan_provision)
        if form.is_valid():
            form.save()
            return redirect('loan_provision_list')
    else:
        form = LoanProvisionForm(instance=loan_provision)
    
    return render(request, 'accounts_admin/loan_provision/edit_loan_provision.html', {'form': form})


# loans/views.py

def delete_loan_provision(request, uuid):
    loan_provision = get_object_or_404(LoanProvision, uuid=uuid)
    if request.method == 'POST':
        loan_provision.delete()
        return redirect('loan_provision_list')
    
    return render(request, 'accounts_admin/loan_provision/delete_loan_provision.html', {'loan_provision': loan_provision})


# ==================== CUSTOMER ACCOUNT TYPE MANAGEMENT ====================
from .models import CustomerAccountType
from .forms import CustomerAccountTypeForm


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def customer_account_type_list(request):
    """List all customer account types for the company"""
    from accounts.utils import get_company_branch_ids_all
    
    branch_ids = get_company_branch_ids_all(request.user)
    account_types = CustomerAccountType.all_objects.filter(
        branch_id__in=branch_ids
    ).select_related('account').order_by('sort_order', 'account__gl_name')
    
    return render(request, 'accounts_admin/customer_account_type/list.html', {
        'account_types': account_types
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def customer_account_type_create(request):
    """Create a new customer account type"""
    from accounts.utils import get_company_branch_ids_all, get_branch_from_vendor_db
    
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    branch_ids = get_company_branch_ids_all(request.user)
    
    # Get accounts that are not already added as customer account types
    existing_account_ids = CustomerAccountType.all_objects.filter(
        branch_id__in=branch_ids
    ).values_list('account_id', flat=True)
    
    available_accounts = Account.all_objects.filter(
        branch_id__in=branch_ids
    ).exclude(id__in=existing_account_ids).order_by('gl_no')
    
    if request.method == 'POST':
        form = CustomerAccountTypeForm(request.POST)
        form.fields['account'].queryset = available_accounts
        
        if form.is_valid():
            account_type = form.save(commit=False)
            account_type.branch = user_branch
            account_type.save()
            messages.success(request, 'Customer Account Type added successfully!')
            return redirect('customer_account_type_list')
    else:
        form = CustomerAccountTypeForm()
        form.fields['account'].queryset = available_accounts
    
    return render(request, 'accounts_admin/customer_account_type/form.html', {
        'form': form,
        'title': 'Add Customer Account Type',
        'available_accounts': available_accounts,
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def customer_account_type_edit(request, uuid):
    """Edit an existing customer account type"""
    from accounts.utils import get_company_branch_ids_all
    
    account_type = get_object_or_404(CustomerAccountType, uuid=uuid)
    branch_ids = get_company_branch_ids_all(request.user)
    
    # Get accounts - include current one plus those not already used
    existing_account_ids = CustomerAccountType.all_objects.filter(
        branch_id__in=branch_ids
    ).exclude(uuid=uuid).values_list('account_id', flat=True)
    
    available_accounts = Account.all_objects.filter(
        branch_id__in=branch_ids
    ).exclude(id__in=existing_account_ids).order_by('gl_no')
    
    if request.method == 'POST':
        form = CustomerAccountTypeForm(request.POST, instance=account_type)
        form.fields['account'].queryset = available_accounts
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer Account Type updated successfully!')
            return redirect('customer_account_type_list')
    else:
        form = CustomerAccountTypeForm(instance=account_type)
        form.fields['account'].queryset = available_accounts
    
    return render(request, 'accounts_admin/customer_account_type/form.html', {
        'form': form,
        'title': 'Edit Customer Account Type',
        'account_type': account_type,
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def customer_account_type_delete(request, uuid):
    """Delete a customer account type"""
    account_type = get_object_or_404(CustomerAccountType, uuid=uuid)
    
    if request.method == 'POST':
        account_type.delete()
        messages.success(request, 'Customer Account Type deleted successfully!')
        return redirect('customer_account_type_list')
    
    return render(request, 'accounts_admin/customer_account_type/delete.html', {
        'account_type': account_type
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def customer_account_type_toggle(request, uuid):
    """Toggle active status of a customer account type"""
    account_type = get_object_or_404(CustomerAccountType, uuid=uuid)
    account_type.is_active = not account_type.is_active
    account_type.save()
    
    status = "activated" if account_type.is_active else "deactivated"
    messages.success(request, f'Account Type {status} successfully!')
    return redirect('customer_account_type_list')


# ==================== LOAN AUTO REPAYMENT SETTINGS ====================
from .models import LoanAutoRepaymentSetting


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def loan_auto_repayment_list(request):
    """List all loan accounts with auto repayment settings"""
    from accounts.utils import get_company_branch_ids_all, get_branch_from_vendor_db
    
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    branch_ids = get_company_branch_ids_all(request.user)
    
    # Get all loan accounts (gl_no starting with 104 for loan portfolio)
    loan_accounts = Account.all_objects.filter(
        branch_id__in=branch_ids,
        gl_no__startswith='104'
    ).exclude(gl_no='10400').order_by('gl_no')
    
    # Get existing settings
    existing_settings = {
        setting.account_id: setting 
        for setting in LoanAutoRepaymentSetting.all_objects.filter(branch_id__in=branch_ids)
    }
    
    # Create settings for accounts that don't have one yet
    for account in loan_accounts:
        if account.id not in existing_settings:
            LoanAutoRepaymentSetting.all_objects.create(
                branch=user_branch,
                account=account,
                is_auto_repayment_enabled=False
            )
    
    # Refresh settings after creation
    settings = LoanAutoRepaymentSetting.all_objects.filter(
        branch_id__in=branch_ids
    ).select_related('account').order_by('account__gl_no')
    
    return render(request, 'accounts_admin/loan_auto_repayment/list.html', {
        'settings': settings
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def loan_auto_repayment_toggle(request, uuid):
    """Toggle auto repayment status for a loan account"""
    setting = get_object_or_404(LoanAutoRepaymentSetting, uuid=uuid)
    setting.is_auto_repayment_enabled = not setting.is_auto_repayment_enabled
    setting.save()
    
    status = "enabled" if setting.is_auto_repayment_enabled else "disabled"
    messages.success(request, f'Auto repayment {status} for {setting.account.gl_name}!')
    return redirect('loan_auto_repayment_list')


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def loan_auto_repayment_update_interest_gl(request, uuid):
    """Update the interest income GL number for a loan auto repayment setting"""
    setting = get_object_or_404(LoanAutoRepaymentSetting, uuid=uuid)
    
    if request.method == 'POST':
        interest_income_gl_no = request.POST.get('interest_income_gl_no', '').strip()
        
        # Validate that the GL number exists if provided
        if interest_income_gl_no:
            from accounts.utils import get_company_branch_ids_all
            branch_ids = get_company_branch_ids_all(request.user)
            
            # Check if the GL number exists in the chart of accounts
            if not Account.all_objects.filter(branch_id__in=branch_ids, gl_no=interest_income_gl_no).exists():
                messages.error(request, f'GL number {interest_income_gl_no} does not exist in the Chart of Accounts!')
                return redirect('loan_auto_repayment_list')
        
        setting.interest_income_gl_no = interest_income_gl_no if interest_income_gl_no else None
        setting.save()
        messages.success(request, f'Interest income GL updated for {setting.account.gl_name}!')
    
    return redirect('loan_auto_repayment_list')


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def loan_auto_repayment_update_balance_sheet_gl(request, uuid):
    """Update the interest receivable and unearned interest income GL numbers"""
    setting = get_object_or_404(LoanAutoRepaymentSetting, uuid=uuid)
    
    if request.method == 'POST':
        int_receivable_gl_no = request.POST.get('int_receivable_gl_no', '').strip()
        unearned_int_income_gl_no = request.POST.get('unearned_int_income_gl_no', '').strip()
        
        from accounts.utils import get_company_branch_ids_all
        branch_ids = get_company_branch_ids_all(request.user)
        
        # Validate interest receivable GL
        if int_receivable_gl_no:
            if not Account.all_objects.filter(branch_id__in=branch_ids, gl_no=int_receivable_gl_no).exists():
                messages.error(request, f'Interest Receivable GL {int_receivable_gl_no} does not exist in the Chart of Accounts!')
                return redirect('loan_auto_repayment_list')
        
        # Validate unearned interest income GL
        if unearned_int_income_gl_no:
            if not Account.all_objects.filter(branch_id__in=branch_ids, gl_no=unearned_int_income_gl_no).exists():
                messages.error(request, f'Unearned Interest Income GL {unearned_int_income_gl_no} does not exist in the Chart of Accounts!')
                return redirect('loan_auto_repayment_list')
        
        setting.int_receivable_gl_no = int_receivable_gl_no if int_receivable_gl_no else None
        setting.unearned_int_income_gl_no = unearned_int_income_gl_no if unearned_int_income_gl_no else None
        setting.save()
        messages.success(request, f'Balance sheet GLs updated for {setting.account.gl_name}!')
    
    return redirect('loan_auto_repayment_list')
