from django.shortcuts import get_object_or_404, render

# Create your views here.
from django.shortcuts import render, redirect

from accounts.views import check_role_admin
from accounts_admin.models import Account, Account_Officer, Category, Id_card_type, Region
from company.models import Company
from customers.utils import generate_unique_6_digit_number
# from transactions.models import Memtrans
from .models import Customer
from .forms import CustomerForm, InternalAccountForm  # You'll need to create a form for creating/updating customers
from django.contrib import messages
import random
from django.db.models import Sum
from django.db.models import Q
from django.contrib.auth.decorators import login_required, user_passes_test


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def customer_list(request):
    customers = Customer.objects.exclude(ac_no='1')
    # customers = Customer.objects.filter(label='C')
    return render(request, 'customer_list.html', {'customers': customers})

# def customer_detail(request, ac_no):
#     customer = Customer.objects.get(ac_no=ac_no)
#     return render(request, 'customer_detail.html', {'customer': customer})


from .sms_service import send_sms
@login_required(login_url='login')
@user_passes_test(check_role_admin)

def customers(request):
    user_branch = request.user.branch  # Get the user's branch

    # Filter accounts using the user's branch
    cust_data = Account.objects.filter(gl_no__startswith='20') \
        .exclude(gl_no='20100') \
        .exclude(gl_no='20200') \
        .exclude(gl_no='20000')

    gl_no = Account.objects.filter(branch=user_branch) \
        .values_list('gl_no', flat=True).filter(gl_no__startswith='20')

    # officer = Account_Officer.objects.filter(branch=user_branch)
    # region = Region.objects.filter(branch=user_branch)  # Make sure Region has a ForeignKey to Branch
    # category = Category.objects.filter(branch=user_branch)  # Make sure Category has a ForeignKey to Branch
    # id_card = Id_card_type.objects.filter(branch=user_branch)  # Ensure Id_card_type has a ForeignKey to Branch


    officer = Account_Officer.objects.all()
    region = Region.objects.all()  # Make sure Region has a ForeignKey to Branch
    category = Category.objects.all()  # Make sure Category has a ForeignKey to Branch
    id_card = Id_card_type.objects.all()
    # Since you're not using a Company model, fetch the current branch only
    cust_branch = [user_branch]

    # Get the most recent customer
    customer = Customer.objects.filter(branch=user_branch).order_by('-gl_no', '-ac_no').first()

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)

        if form.is_valid():
            ac_no = generate_unique_6_digit_number()
            form.instance.ac_no = ac_no
            form.instance.branch = user_branch

            try:
                new_record = form.save()
                ac_no = new_record.ac_no
                gl_no = new_record.gl_no

                if new_record.sms:
                    phone_number = new_record.phone_no
                    message = f"Hello {new_record.first_name}, Enjoy {gl_no}{ac_no}."
                    
                    print(f"Sending SMS to: {phone_number}")
                    print(f"Message: {message}")

                    sms_response = send_sms(phone_number, message)

                    if 'error' in sms_response:
                        messages.error(request, f"SMS failed: {sms_response['error']}")
                    else:
                        messages.success(request, "SMS sent successfully!")

                return render(request, 'file/customer/account_no.html', {
                    'ac_no': ac_no,
                    'gl_no': gl_no,
                })

            except Exception as e:
                messages.error(request, f"Error saving customer or sending SMS: {e}")
                form.add_error(None, f"Error saving customer or sending SMS: {e}")

        else:
            messages.error(request, "There were errors in the form submission. Please correct them.")
            print(f"Form errors: {form.errors}")

    else:
        form = CustomerForm()

    return render(request, 'file/customer/customer.html', {
        'form': form,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'region': region,
        'category': category,
        'customer': customer,
        'id_card': id_card
    })




def company_reg(request):
    user_company = request.user.branch.company

    # Get GL accounts that start with '20' but not exactly '20100', '20200', '20000'
    cust_data = Account.objects.filter(gl_no__startswith='20', branch__company=user_company) \
        .exclude(gl_no__in=['20100', '20200', '20000'])

    # Get list of GL numbers (flat values)
    gl_no = cust_data.values_list('gl_no', flat=True)

    officer = Account_Officer.objects.filter(branch__company=user_company)
    region = Region.objects.filter(branch__company=user_company)
    category = Category.objects.filter(branch__company=user_company)
    id_card = Id_card_type.objects.filter(branch__company=user_company)

    # Get branches under this company
    cust_branch = user_company.branches.all()

    # Get most recent customer
    customer = Customer.objects.all().order_by('-gl_no', '-ac_no').first()

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)

        if form.is_valid():
            ac_no = generate_unique_6_digit_number()
            form.instance.ac_no = ac_no
            form.instance.branch = request.user.branch

            # Set is_company to True before saving
            form.instance.is_company = True
            form.instance.label = 'C'

            try:
                new_record = form.save()
                ac_no = new_record.ac_no
                gl_no = new_record.gl_no

                # If SMS is checked
                if new_record.sms:
                    phone_number = new_record.phone_no
                    message = f"Hello {new_record.first_name}, Enjoy {gl_no}{ac_no}."

                    print(f"Sending SMS to: {phone_number}")
                    print(f"Message: {message}")

                    sms_response = send_sms(phone_number, message)

                    if 'error' in sms_response:
                        messages.error(request, f"SMS failed: {sms_response['error']}")
                    else:
                        messages.success(request, "SMS sent successfully!")

                return render(request, 'file/customer/account_no.html', {
                    'ac_no': ac_no,
                    'gl_no': gl_no,
                })

            except Exception as e:
                messages.error(request, f"Error saving customer or sending SMS: {e}")
                form.add_error(None, f"Error saving customer or sending SMS: {e}")
        else:
            messages.error(request, "There were errors in the form submission. Please correct them.")
            print(f"Form errors: {form.errors}")

    else:
        form = CustomerForm()

    return render(request, 'file/customer/company_reg.html', {
        'form': form,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'region': region,
        'category': category,
        'customer': customer,
        'id_card': id_card,
    })

def edit_company_reg(request, customer_id):
    # Fetch the user company and branches as in the original function
    user_company = request.user.branch.company
    cust_data = Account.objects.filter(gl_no__startswith='104') \
        .exclude(gl_no__in=['20100', '20200', '20000'])
    gl_no = cust_data.values_list('gl_no', flat=True)
    
    officer = Account_Officer.objects.filter(branch__company=user_company)
    region = Region.objects.filter(branch__company=user_company)
    category = Category.objects.filter(branch__company=user_company)
    id_card = Id_card_type.objects.filter(branch__company=user_company)
    
    # Get branches under this company
    cust_branch = user_company.branches.all()

    # Fetch the customer to edit
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        messages.error(request, "Customer not found.")
        return redirect('some-fallback-view')  # Redirect to an appropriate page if customer doesn't exist

    # Fetch customer-related account info for display
    ac_no = customer.ac_no
    gl_no = customer.gl_no

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES, instance=customer)

        if form.is_valid():
            form.instance.branch = request.user.branch

            # Set is_company to True before saving if not already set
            if not form.instance.is_company:
                form.instance.is_company = True
                form.instance.label = 'C'

            # If ac_no is not set (for new customers or empty), generate a unique 6-digit number
            if not form.instance.ac_no:
                form.instance.ac_no = generate_unique_6_digit_number()

            try:
                updated_customer = form.save()
                ac_no = updated_customer.ac_no  # Update ac_no after save
                gl_no = updated_customer.gl_no  # Update gl_no after save

                # If SMS is checked
                if updated_customer.sms:
                    phone_number = updated_customer.phone_no
                    message = f"Hello {updated_customer.first_name}, Enjoy {gl_no}{ac_no}."

                    print(f"Sending SMS to: {phone_number}")
                    print(f"Message: {message}")

                    sms_response = send_sms(phone_number, message)

                    if 'error' in sms_response:
                        messages.error(request, f"SMS failed: {sms_response['error']}")
                    else:
                        messages.success(request, "SMS sent successfully!")

                return render(request, 'file/customer/account_no.html', {
                    'ac_no': ac_no,
                    'gl_no': gl_no,
                })

            except Exception as e:
                messages.error(request, f"Error updating customer or sending SMS: {e}")
                form.add_error(None, f"Error updating customer or sending SMS: {e}")
        else:
            messages.error(request, "There were errors in the form submission. Please correct them.")
            print(f"Form errors: {form.errors}")
    
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'file/customer/company_reg.html', {
        'form': form,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'region': region,
        'category': category,
        'customer': customer,
        'id_card': id_card,
        'ac_no': ac_no,  # Add ac_no to context to ensure it's available
        'gl_no': gl_no,  # Add gl_no to context to ensure it's available
    })






def add_company_reg(request):
    # Fetch the user company and branches as in the original function
    user_company = request.user.branch.company
    cust_data = Account.objects.filter(gl_no__startswith='104') \
        .exclude(gl_no__in=['20100', '20200', '20000'])
    gl_no = cust_data.values_list('gl_no', flat=True)
    
    officer = Account_Officer.objects.filter(branch__company=user_company)
    region = Region.objects.filter(branch__company=user_company)
    category = Category.objects.filter(branch__company=user_company)
    id_card = Id_card_type.objects.filter(branch__company=user_company)
    
    # Get branches under this company
    cust_branch = user_company.branches.all()

    # Handle new customer addition
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)

        if form.is_valid():
            form.instance.branch = request.user.branch

            # Set is_company to True before saving if not already set
            if not form.instance.is_company:
                form.instance.is_company = True
                form.instance.label = 'C'

            # If ac_no is not set (for new customers), generate a unique 6-digit number
            if not form.instance.ac_no:
                form.instance.ac_no = generate_unique_6_digit_number()

            try:
                # Save the new customer
                new_customer = form.save()
                ac_no = new_customer.ac_no  # Get the ac_no after save
                gl_no = new_customer.gl_no  # Get the gl_no after save

                # If SMS is checked
                if new_customer.sms:
                    phone_number = new_customer.phone_no
                    message = f"Hello {new_customer.first_name}, Enjoy {gl_no}{ac_no}."

                    print(f"Sending SMS to: {phone_number}")
                    print(f"Message: {message}")

                    sms_response = send_sms(phone_number, message)

                    if 'error' in sms_response:
                        messages.error(request, f"SMS failed: {sms_response['error']}")
                    else:
                        messages.success(request, "SMS sent successfully!")

                return render(request, 'file/customer/account_no.html', {
                    'ac_no': ac_no,
                    'gl_no': gl_no,
                })

            except Exception as e:
                messages.error(request, f"Error creating customer or sending SMS: {e}")
                form.add_error(None, f"Error creating customer or sending SMS: {e}")
        else:
            messages.error(request, "There were errors in the form submission. Please correct them.")
            print(f"Form errors: {form.errors}")
    
    else:
        form = CustomerForm()

    return render(request, 'file/customer/company_reg.html', {
        'form': form,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'region': region,
        'category': category,
        'id_card': id_card,
    })

# views.py

from django.shortcuts import render, redirect
from .models import Group, Customer
from .forms import GroupForm, AssignCustomerForm

def create_group(request):
    form = GroupForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('assign_customers_to_group')
    return render(request, 'groups/create_group.html', {'form': form})


from django.shortcuts import render, redirect
from .forms import AssignCustomerForm
from .models import Customer

# groups/views.py
# groups/views.py

# groups/views.py

from django.shortcuts import render, redirect
from .forms import AssignCustomerForm
from .models import Customer, Group

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import AssignCustomerForm
from .models import Customer, Group

# Assign customer to group view
def assign_customers_to_group(request):
    if request.method == 'POST':
        form = AssignCustomerForm(request.POST)
        if form.is_valid():
            # Get the group and customer from the form
            group = form.cleaned_data['group']
            customer = form.cleaned_data['customer']
            
            # Assign the group to the customer and save
            customer.group = group
            customer.save()

            # Add a success message
            messages.success(request, f"{customer.first_name} {customer.last_name} has been assigned to {group.group_name}.")
            return redirect('assign_customers_to_group')  # Redirect to avoid re-posting on refresh
        else:
            # Print form errors for debugging purposes
            print("Form errors:", form.errors)
            messages.error(request, "There was an error with the form. Please try again.")

    else:
        form = AssignCustomerForm()
    
    return render(request, 'groups/assign_customers.html', {'form': form})


def remove_from_group(request, customer_id):
    try:
        customer = Customer.objects.get(id=customer_id)
        group_id = customer.group.id if customer.group else None
        customer.group = None
        customer.save()

        messages.success(request, f"{customer.first_name} {customer.last_name} has been removed from the group.")
        if group_id:
            return redirect('group_customers', group_id=group_id)
        else:
            return redirect('assign_customers_to_group')
    except Customer.DoesNotExist:
        messages.error(request, "Customer not found.")
        return redirect('assign_customers_to_group')



# Remove customer from group
from django.shortcuts import get_object_or_404

def group_customers(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    customers = Customer.objects.filter(group=group)

    return render(request, 'groups/group_customers.html', {
        'group': group,
        'customers': customers
    })


def group_list(request):
    groups = Group.objects.all()
    return render(request, 'groups/group_list.html', {'groups': groups})


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def edit_customer(request, id):
    customer = get_object_or_404(Customer, id=id)
    cust_data = Account.objects.filter(gl_no__startswith='200').exclude(gl_no='200100').exclude(gl_no='200200').exclude(gl_no='200000')
    gl_no = Account.objects.all().values_list('gl_no', flat=True).filter(gl_no__startswith='200')
    cust_branch = Company.objects.all()
    category = Category.objects.all()
    region = Region.objects.all()
    officer = Account_Officer.objects.all()
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            form.save()
            return redirect('customer_list')
    else:
        initial_data = {'gl_no': customer.gl_no}
        form = CustomerForm(instance=customer, initial=initial_data)
        # form = CustomerForm(instance=customer)
    return render(request, 'file/customer/edit_customer.html', {'form': form, 'customer': customer, 'cust_data': cust_data,
     'cust_branch': cust_branch, 'gl_no': gl_no, 'region': region,'category':category,'officer':officer})



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Customer
# from transactions.models import Memtrans
@login_required(login_url='login')
@user_passes_test(check_role_admin)
def delete_customer(request, id):
    customer = get_object_or_404(Customer, id=id)
    # Check if there are transactions associated with this customer
    transactions_exist = Memtrans.objects.filter(customer=customer).exists()
    
    if transactions_exist:
        messages.error(request, 'You cannot delete this customer because there are transactions attached to it.')
        return redirect('customer_list')

    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Customer deleted successfully!')
        return redirect('customer_list')
    
    return render(request, 'file/customer/delete_customer.html', {'customer': customer})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def new_accounts(request):
   
    return render(request, 'file/new_accounts.html')


# def customers(request):
   
#     return render(request, 'file/customer.html')





# def internal_accounts(request):
#     gl_no = Account.objects.all()
#     cust_branch = Company.objects.all()
#     if request.method == 'POST':
#         form = CustomerForm(request.POST)  # Handle file uploads with request.FILES
#         if form.is_valid():
       
#             form.save()
#             return redirect('customer_list')

#     else:
#         form = CustomerForm()

   
#     return render(request, 'file/internal_accounts.html', {'cust_branch':cust_branch,'gl_no':gl_no})

from django.contrib import messages
@login_required(login_url='login')
@user_passes_test(check_role_admin)


def internal_accounts(request):
    # Get the branch of the logged-in user
    user_branch = request.user.branch

    # Filter the Account objects based on the user's branch code
    gl_no = Account.objects.filter(branch=user_branch).order_by('gl_no')
    
    # Get the branches related to the logged-in user's company
    cust_branch = Company.objects.all()

    if request.method == 'POST':
        form = InternalAccountForm(request.POST)
        if form.is_valid():
            gl_no_value = form.cleaned_data.get('gl_no')
            ac_no_value = form.cleaned_data.get('ac_no')

            # ✅ Check duplicate in Customer model
            if Customer.objects.filter(gl_no=gl_no_value, ac_no=ac_no_value, branch=user_branch).exists():
                messages.error(
                    request,
                    f"⚠️ Customer with GL {gl_no_value} and AC {ac_no_value} already exists under your branch."
                )
            else:
                # Assign branch automatically
                form.instance.branch = user_branch
                form.save()
                messages.success(request, "✅ Internal account created successfully.")
                return redirect('internal_list')
    else:
        form = InternalAccountForm()

    return render(
        request,
        'file/internal/internal_accounts.html',
        {'cust_branch': cust_branch, 'gl_no': gl_no, 'form': form}
    )


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def edit_internal_account(request, id):
    account = get_object_or_404(Customer, id=id)
    cust_branch = Company.objects.all()
    cust_data = Account.objects.filter(gl_no__startswith='').exclude(gl_no='200100').exclude(gl_no='200200').exclude(gl_no='200000')

    if request.method == 'POST':
        form = InternalAccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            return redirect('internal_list')
    else:
        form = InternalAccountForm(instance=account)

    return render(request, 'file/internal/edit_internal.html', {'form': form, 'account': account,'cust_branch':cust_branch,'cust_data':cust_data})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def delete_internal_account(request, id):
    account = get_object_or_404(Customer, id=id)

    if request.method == 'POST':
        # You may add a confirmation step here if needed
        account.delete()
        return redirect('internal_list')

    return render(request, 'file/internal/delete_internal.html', {'account': account})


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def internal_list(request):
    account = Customer.objects.filter(ac_no=1)
    return render(request, 'file/internal/internal_list.html', {'account': account})



# def create_loan(request, id):
#     customer = get_object_or_404(Customer, id=id)
#     cashier_gl_value = request.user.cashier_gl
#     customers = Customer.objects.get(gl_no=cashier_gl_value)
    
#     initial_values = {'gl_no_cashier': customers.gl_no, 'ac_no_cashier': customers.ac_no,  'gl_no_cust': customer.gl_no, 'ac_no_cust': customer.ac_no, 
#     }
   

    
        

#     return render(request, 'loans/choose_to_create_loan.html', {'form': form, 'data': data, 'customer': customer, 'total_amount': total_amount,'formatted_balance':formatted_balance,'customers':customers,'sum_of_amount_cust':sum_of_amount_cust,'sum_of_amount_cash':sum_of_amount_cash})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
# def create_loan(request):
#     cust_data = Account.objects.filter(gl_no__startswith='200').exclude(gl_no='200100').exclude(gl_no='200200').exclude(gl_no='200000')
#     gl_no = Account.objects.all().values_list('gl_no', flat=True).filter(gl_no__startswith='200')
#     officer = Account_Officer.objects.all()
#     region = Region.objects.all()
#     category = Category.objects.all()
#     id_card = Id_card_type.objects.all()

#     cust_branch = Company.objects.all()
#     customer = Customer.objects.all().order_by('-gl_no', '-ac_no').first()
#     if request.method == 'POST':
#         form = CustomerForm(request.POST, request.FILES)  # Handle file uploads with request.FILES
#         if form.is_valid():
#             ac_no = generate_unique_6_digit_number()
            
#             # Assign the generated number to the 'cust_no' field of the form
#             form.instance.ac_no = ac_no
           
            
#             new_record = form.save()

#             # Get the ac_no and gl_no from the newly created record
#             ac_no = new_record.ac_no
#             gl_no = new_record.gl_no

#             # Render a template that displays the ac_no and gl_no
#             return render(request, 'file/customer/account_no.html', {
#                 'ac_no': new_record.ac_no,
#                 'gl_no': new_record.gl_no,
#             })

           
#     else:
#         form = CustomerForm()

#     return render(request, 'loans/create_loan.html', {'form': form, 'cust_data': cust_data, 'cust_branch': cust_branch, 
#         'gl_no': gl_no, 'officer': officer, 'region': region,'category':category,'customer':customer,'id_card':id_card})



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_to_create_loan(request):
    data = Memtrans.objects.all().order_by('-id').first()
    customers = Customer.objects.filter(label='C').order_by('-id')
    
    total_amounts = []

    for customer in customers:
        # Calculate the total amount for each customer
        total_amount = Memtrans.objects.filter(gl_no=customer.gl_no, ac_no=customer.ac_no, error='A').aggregate(total_amount=Sum('amount'))['total_amount']
        total_amounts.append({
            'customer': customer,
            'total_amount': total_amount or 0.0,
        })
    return render(request, 'loans/choose_to_create_loan.html',{'data': data, 'total_amounts': total_amounts})





@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_to_create_company_loan(request):
    data = Memtrans.objects.all().order_by('-id').first()
    customers = Customer.objects.filter(label='C').order_by('-id')
    
    total_amounts = []

    for customer in customers:
        # Calculate the total amount for each customer
        total_amount = Memtrans.objects.filter(gl_no=customer.gl_no, ac_no=customer.ac_no, error='A').aggregate(total_amount=Sum('amount'))['total_amount']
        total_amounts.append({
            'customer': customer,
            'total_amount': total_amount or 0.0,
        })
    return render(request, 'loans/choose_to_create_company_loan.html',{'data': data, 'total_amounts': total_amounts})




@login_required(login_url='login')
@user_passes_test(check_role_admin)

def choose_create_another_account(request):
    user_branch = request.user.branch  # Get the branch of the logged-in user
    data = Memtrans.objects.all().order_by('-id').first()
    
    # Fetch only customers belonging to the logged-in user's branch
    customers = Customer.objects.filter(label='C', branch=user_branch).order_by('-id')
    
    total_amounts = []

    for customer in customers:
        # Calculate the total amount for each customer
        total_amount = Memtrans.objects.filter(gl_no=customer.gl_no, ac_no=customer.ac_no, error='A').aggregate(total_amount=Sum('amount'))['total_amount']
        total_amounts.append({
            'customer': customer,
            'total_amount': total_amount or 0.0,
        })

    return render(request, 'file/customer/choose_create_another_account.html', {
        'data': data,
        'total_amounts': total_amounts,
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def create_another_account(request, id):
    # Get the logged-in user's branch
    user_branch = request.user.branch
    customer = get_object_or_404(Customer, id=id)
    
    # Filter accounts for loan accounts, excluding specific GL numbers
    loan_account = Account.objects.filter(
        (Q(gl_no__startswith='104') | Q(gl_no__startswith='20')),
        branch=user_branch
    ).exclude(gl_no='20000')
    
    # Set initial values for the form
    initial_values = {'gl_no_cust': customer.gl_no, 'ac_no_cust': customer.ac_no}
    
    # Fetch required data for the form
    id_card = Id_card_type.objects.all()
    category = Category.objects.all()
    region = Region.objects.all()
    credit_officer = Account_Officer.objects.all()
    
    # Initialize GL number variable
    gl_no = None

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)
        if form.is_valid():
            if 'ac_no' in form.cleaned_data:
                new_customer = form.save(commit=False)
                
                # Automatically assign the logged-in user's branch to the new customer account
                new_customer.branch = user_branch  # Set the user's branch explicitly

                # Assign form data to the new customer
                new_customer.ac_no = form.cleaned_data.get('ac_no')
                new_customer.photo = form.cleaned_data.get('photo')
                new_customer.save()
                
                # Success message and redirect to account number display
                messages.success(request, 'Account saved successfully!')
                ac_no = new_customer.ac_no
                gl_no = new_customer.gl_no

                return render(request, 'file/customer/account_no.html', {
                    'ac_no': ac_no,
                    'gl_no': gl_no,
                })
            else:
                # Error if account number is missing
                messages.error(request, 'Invalid form data. Please provide a valid account number.')
        else:
            # Error if the form is invalid
            messages.error(request, 'Form is not valid. Please check the entered data.')

    else:
        # Initialize the form with initial values
        form = CustomerForm(initial=initial_values)

    # Render the account creation page
    return render(request, 'file/customer/create_another_account.html', {
        'form': form,
        'category': category,
        'loan_account': loan_account,
        'gl_no': gl_no,
        'customer': customer,
        'id_card': id_card,
        'region': region,
        'credit_officer': credit_officer,
        'user_branch': user_branch,  # Pass user_branch to the template if needed
    })





@login_required(login_url='login')
@user_passes_test(check_role_admin)
def create_loan(request, id):
    customer = get_object_or_404(Customer, id=id)
    loan_account = Account.objects.filter(
    Q(gl_no__startswith='104') | Q(gl_no__startswith='206')
).exclude(gl_no='104000').exclude(gl_no='104100').exclude(gl_no='104200')
    initial_values = {'gl_no_cust': customer.gl_no, 'ac_no_cust': customer.ac_no}

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)
        if form.is_valid():
            # Check if 'ac_no' is present in form.cleaned_data
            if 'ac_no' in form.cleaned_data:
              
                new_customer = form.save(commit=False)

                # Automatically assign the logged-in user's branch to the new loan account
                new_customer.branch = request.user.branch

                new_customer.ac_no = form.cleaned_data.get('ac_no')
                new_customer.photo = form.cleaned_data.get('photo')
                new_customer.save()
                messages.success(request, 'Account saved successfully!')
                ac_no = new_customer.ac_no
                gl_no = new_customer.gl_no

                # Render a template that displays the ac_no and gl_no
                return render(request, 'file/customer/account_no.html', {
                    'ac_no': new_customer.ac_no,
                    'gl_no': new_customer.gl_no,
                })
            else:
                # Handle the case when 'ac_no' key is not present in form.cleaned_data
                messages.error(request, 'Invalid form data. Please provide a valid account number.')
        else:
            messages.error(request, 'Form is not valid. Please check the entered data.')

    else:
        form = CustomerForm(initial=initial_values)

    return render(request, 'loans/create_loan_account.html', {'form': form, 'customer': customer, 'loan_account': loan_account})



def manage_customer(request):
    return render(request, 'manage_customer.html')





from django.shortcuts import render, get_object_or_404
from transactions.models import Memtrans
from .models import Customer

def customer_list_account(request):
    # Retrieve all customers
    customers = Customer.objects.filter(label__in=['C', 'L'])

    
    # Render the list template with customer data
    return render(request, 'file/customer/customer_list.html', {
        'customers': customers,
    })




def customer_detail(request, pk):
    # Retrieve the customer by primary key
    customer = get_object_or_404(Customer, pk=pk)
    
    # Retrieve the account number from the customer
    ac_no_customer = customer.ac_no
    
    # Calculate the balance for transactions with the same ac_no but different gl_no
    transactions = Memtrans.objects.filter(ac_no=ac_no_customer).values('gl_no').annotate(
        total_amount=Sum('amount')
    ).order_by('gl_no')
    
    # Render the detail template with the customer data and transaction information
    return render(request, 'customer_detail.html', {
        'customer': customer,
        'transactions': transactions,
        'ac_no_customer': ac_no_customer,  # Pass the account number to the template
    })







def transaction_list(request, gl_no, ac_no):
    # Fetch the transactions related to the provided account number
    transactions = Memtrans.objects.filter(gl_no=gl_no, ac_no=ac_no)
    
    # If no transactions found, handle accordingly
    if not transactions:
        return render(request, 'transaction_list.html', {
            'transactions': transactions,
            'message': 'No related transactions found.'
        })
    
    # Example of fetching a main transaction (optional, if needed)
    # main_transaction = transactions.first()  # Get the first one, if needed

    context = {
        'ac_no': ac_no,
        'gl_no': gl_no,
        'transactions': transactions
    }
    return render(request, 'transaction_list.html', context)





# views.py
from django.shortcuts import render, redirect
from .forms import FixedDepositAccountForm
from .models import FixedDepositAccount
from customers.models import Customer
from company.models import Branch

def register_fixed_deposit_account(request):
    if request.method == "POST":
        form = FixedDepositAccountForm(request.POST)
        if form.is_valid():
            # Set the branch to the logged-in user's branch before saving
            fixed_deposit_account = form.save(commit=False)
            fixed_deposit_account.branch = request.user.branch  # Assuming the user has a branch field
            fixed_deposit_account.save()

            # Update the customer's label to "F"
            customer = fixed_deposit_account.customer
            customer.label = "F"
            customer.save()

            return redirect("fixed_deposit/fixed_deposit_account_success")  # Redirect to a success page
    else:
        form = FixedDepositAccountForm()

    # Fetch all customers for the dropdown
    customers = Customer.objects.all()

    # Get the logged-in user's branch
    user_branch = request.user.branch  # Assuming the user has a branch field

    return render(request, "fixed_deposit/register_fixed_deposit_account.html", {
        "form": form,
        "customers": customers,
        "user_branch": user_branch,  # Pass the user's branch to the template
    })




from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Customer

def customer_sms_email_alert(request):
    customers = Customer.objects.filter(ac_no__gt=1)

    if request.method == "POST":
        customer_id = request.POST.get("customer_id")
        action_type = request.POST.get("action_type")  # Check which button was clicked
        customer = Customer.objects.get(id=customer_id)

        if action_type == "sms":
            customer.sms = not customer.sms  # Toggle SMS
            messages.success(request, "SMS alert setting updated successfully.")
        elif action_type == "email":
            customer.email_alert = not customer.email_alert  # Toggle Email
            messages.success(request, "Email alert setting updated successfully.")

        customer.save()
        return redirect("customer_sms_email_alert")

    return render(request, "file/customer/customer_sms_email_alert.html", {"customers": customers})
