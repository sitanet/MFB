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
    # Get the user's branch from the logged-in user's branch (assuming the user has a `branch` field)
    user_branch = request.user.branch  # Assuming that the user model has a `branch` field

    # Query for required data, filtering by the logged-in user's branch
    cust_data = Account.objects.filter(gl_no__startswith='20', branch=user_branch) \
        .exclude(gl_no='20100') \
        .exclude(gl_no='20200') \
        .exclude(gl_no='20000')
    
    gl_no = Account.objects.filter(branch=user_branch) \
        .values_list('gl_no', flat=True).filter(gl_no__startswith='20')
    
    # Filter Account_Officer based on the logged-in user's branch
    officer = Account_Officer.objects.filter(branch=user_branch)

    # Fix: Filter Region based on the branch (assuming Region model has a `branch` relation)
    region = Region.objects.filter(branch=user_branch)  # Assuming Region has a reference to branch
    
    # Fix: Filter Category based on the branch (if Category has a reference to Branch)
    category = Category.objects.filter(branch=user_branch)  # Assuming Category has a reference to branch

    # Fix: Filter Id_card_type based on the branch (if Id_card_type has a reference to Branch)
    id_card = Id_card_type.objects.filter(branch=user_branch)  # Assuming Id_card_type has a reference to branch

    # Fix: Filter Company based on the branch using the 'branches' related name
    cust_branch = Company.objects.filter(branches=user_branch)  # Using 'branches' related name
    
    # Customer query - No filter based on branch
    customer = Customer.objects.all().order_by('-gl_no', '-ac_no').first()

    # Handle form submission
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)  # Handle file uploads
        if form.is_valid():
            ac_no = generate_unique_6_digit_number()  # Generate unique account number
            form.instance.ac_no = ac_no  # Assign generated account number

            # Automatically assign the logged-in user's branch
            form.instance.branch = request.user.branch

            try:
                new_record = form.save()  # Save form data
                
                # Extract ac_no and gl_no for use after save
                ac_no = new_record.ac_no
                gl_no = new_record.gl_no

                # Check if SMS field is True and send SMS if needed
                if new_record.sms:
                    phone_number = new_record.phone_no
                    message = f"Hello {new_record.first_name}, Enjoy {gl_no}{ac_no}."

                    print(f"Sending SMS to: {phone_number}")
                    print(f"Message: {message}")

                    # Send SMS
                    sms_response = send_sms(phone_number, message)
                    print(f"SMS response: {sms_response}")

                    if 'error' in sms_response:
                        print(f"SMS failed: {sms_response['error']}")
                    else:
                        print(f"SMS sent successfully!")
                
                # Render template to display account number and gl_no
                return render(request, 'file/customer/account_no.html', {
                    'ac_no': ac_no,
                    'gl_no': gl_no,
                })
            except Exception as e:
                print(f"Error saving customer or sending SMS: {e}")
                form.add_error(None, "There was an error saving the customer or sending SMS.")
        else:
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
            # Automatically assign the logged-in user's branch to the internal account
            form.instance.branch = request.user.branch
            form.save()
            return redirect('internal_list')

    else:
        form = InternalAccountForm()

    return render(request, 'file/internal/internal_accounts.html', {'cust_branch': cust_branch, 'gl_no': gl_no, 'form': form})


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
def choose_create_another_account(request):
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
    return render(request, 'file/customer/choose_create_another_account.html',{'data': data, 'total_amounts': total_amounts})




@login_required(login_url='login')
@user_passes_test(check_role_admin)

def create_another_account(request, id):
    customer = get_object_or_404(Customer, id=id)
    loan_account = Account.objects.filter(Q(gl_no__startswith='104') | Q(gl_no__startswith='20')).exclude(gl_no='20000')
    initial_values = {'gl_no_cust': customer.gl_no, 'ac_no_cust': customer.ac_no}
    id_card = Id_card_type.objects.all()
    category = Category.objects.all()
    region = Region.objects.all()
    credit_officer = Account_Officer.objects.all()

    # Initialize gl_no with a default value
    gl_no = None

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)
        if form.is_valid():
            if 'ac_no' in form.cleaned_data:
                new_customer = form.save(commit=False)
                
                # Automatically assign the logged-in user's branch to the new customer account
                new_customer.branch = request.user.branch

                new_customer.ac_no = form.cleaned_data.get('ac_no')
                new_customer.photo = form.cleaned_data.get('photo')
                new_customer.save()
                messages.success(request, 'Account saved successfully!')
                ac_no = new_customer.ac_no
                gl_no = new_customer.gl_no

                return render(request, 'file/customer/account_no.html', {
                    'ac_no': ac_no,
                    'gl_no': gl_no,
                })
            else:
                messages.error(request, 'Invalid form data. Please provide a valid account number.')
        else:
            messages.error(request, 'Form is not valid. Please check the entered data.')

    else:
        form = CustomerForm(initial=initial_values)

    return render(request, 'file/customer/create_another_account.html', {
        'form': form,
        'category': category,
        'loan_account': loan_account,
        'gl_no': gl_no,
        'customer': customer,
        'id_card': id_card,
        'region': region,
        'credit_officer': credit_officer
    })





@login_required(login_url='login')
@user_passes_test(check_role_admin)
def create_loan(request, id):
    customer = get_object_or_404(Customer, id=id)
    loan_account = Account.objects.filter(gl_no__startswith='104').exclude(gl_no='104000').exclude(gl_no='104100').exclude(gl_no='104200')
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
