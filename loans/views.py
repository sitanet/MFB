from datetime import timedelta, timezone
from decimal import Decimal
import json
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from accounts.models import User
from accounts.views import check_role_admin
from accounts_admin.models import Account, Account_Officer
from company.models import Company, Branch
import customers
from django.db import transaction
from customers.models import Customer
from loans.forms import LoansForm, LoansApproval
from loans.models import LoanHist, Loans
from transactions.models import Memtrans
from django.db.models import Sum, Max
from django.contrib import messages
from django.utils import timezone



from transactions.utils import generate_loan_disbursement_id, generate_loan_repayment_id, generate_loan_written_off_id
from django.contrib.auth.decorators import login_required, user_passes_test
# Create your views here.

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def loans(request):
    return render(request, 'loans/loans.html')





# list of account that can apply for loan
@login_required(login_url='login')
@user_passes_test(check_role_admin)


def choose_to_apply_loan(request):
    # Get the logged-in user's branch
    user_branch = request.user.branch

    # Get the most recent Memtrans object for the user's branch
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()

    # Filter customers by label 'L' and the user's branch
    customers = Customer.objects.filter(label='L', branch=user_branch).order_by('-id')

    total_amounts = []
    for customer in customers:
        # Calculate the total amount for each customer within the user's branch
        total_amount = Memtrans.objects.filter(
            gl_no=customer.gl_no,
            ac_no=customer.ac_no,
            error='A',
            branch=user_branch
        ).aggregate(total_amount=Sum('amount'))['total_amount']
        total_amounts.append({
            'customer': customer,
            'total_amount': total_amount or 0.0,
        })

    return render(request, 'loans/choose_to_apply_for_loan.html', {
        'customers': customers,
        'total_amounts': total_amounts,
        'data': data,
    })

# loan application
from django.core.exceptions import ValidationError
from django.utils import timezone

@login_required(login_url='login')
@user_passes_test(check_role_admin)


def loan_application(request, id):
    # Get customer by ID
    customer = get_object_or_404(Customer, id=id)
    cust_branch = customer.branch

    # Filter loan accounts based on GL number
    loan_account = Account.objects.filter(gl_no__startswith='104').exclude(
        gl_no='10400').exclude(gl_no='104100').exclude(gl_no='104200')

    # Set initial values for the form
    initial_values = {'gl_no_cust': customer.gl_no, 'ac_no_cust': customer.ac_no}

    # Get the logged-in user's branch
    user = request.user
    branch = get_object_or_404(Branch, id=user.branch_id)  # Use Branch model directly
    branch_date = branch.session_date.strftime('%Y-%m-%d') if branch.session_date else ''

    # Check if the session is closed
    if branch.session_status == 'Closed':
        return HttpResponse("You cannot post any transaction. Session is closed.")

    if request.method == 'POST':
        form = LoansForm(request.POST, request.FILES)
        if form.is_valid():
            # Validate dates
            appli_date = form.cleaned_data.get('appli_date')
            ses_date = branch.session_date

            if ses_date and appli_date and appli_date > ses_date:
                messages.error(request, "Application date cannot be after the current session date.")
                return render(request, 'loans/loans_application.html', {
                    'form': form,
                    'customer': customer,
                    'loan_account': loan_account,
                    'branch': branch,
                    'branch_date': branch_date,
                })

            gl_no = form.cleaned_data['gl_no']
            ac_no = form.cleaned_data['ac_no']

            with transaction.atomic():
                # Get last loan cycle
                existing_loan = Loans.objects.filter(gl_no=gl_no, ac_no=ac_no).last()

                # Create new loan
                new_loan = Loans(
                    branch=cust_branch,
                    appli_date=appli_date,
                    loan_amount=form.cleaned_data.get('loan_amount', 0),
                    interest_rate=form.cleaned_data.get('interest_rate', 0),
                    payment_freq=form.cleaned_data.get('payment_freq'),
                    interest_calculation_method=form.cleaned_data.get('interest_calculation_method'),
                    loan_officer=form.cleaned_data.get('loan_officer'),
                    business_sector=form.cleaned_data.get('business_sector'),
                    customer=customer,
                    gl_no=gl_no,
                    ac_no=ac_no,
                    num_install=form.cleaned_data.get('num_install', 0),
                    cycle=existing_loan.cycle + 1 if existing_loan else 1,
                )
                new_loan.save()

                # Update customer's loan status
                customer.loan = 'T'
                customer.save()

                messages.success(request, 'Loan applied successfully!')
                return redirect('choose_to_apply_loan')

        else:
            messages.error(request, 'Form is not valid. Please check the entered data.')
    else:
        form = LoansForm(initial=initial_values)

    return render(request, 'loans/loans_application.html', {
        'form': form,
        'customer': customer,
        'loan_account': loan_account,
        'branch': branch,
        'branch_date': branch_date,
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_to_modify_loan(request):
    # Filter loans with approval status 'F' or 'R'
    customers = Loans.objects.select_related('customer').filter(approval_status__in=['F', 'R'])

    return render(request, 'loans/choose_to_modify_loan.html', {'customers': customers})



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def loan_modification(request, id):
    loan_instance = get_object_or_404(Loans, id=id)
    cust_data = Account.objects.filter(gl_no__startswith='200').exclude(gl_no='200100').exclude(gl_no='200200').exclude(gl_no='200000')
    gl_no_list = Account.objects.all().values_list('gl_no', flat=True).filter(gl_no__startswith='200')
    cust_branch = Company.objects.all()
    customers = loan_instance.customer
    officer = Account_Officer.objects.all()
    user = User.objects.get(id=request.user.id)
    branch_id = user.branch_id
    company = get_object_or_404(Company, id=branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    
    
    if company.session_status == 'Closed':
        
        return HttpResponse("You can not post any transaction. Session is closed.") 
    else:

        if request.method == 'POST':
            form = LoansModifyForm(request.POST, request.FILES, instance=loan_instance)
            if form.is_valid():
                form.instance.approval_status = 'F'
                form.save()
                messages.success(request, 'Loan modified successfully!')
                return redirect('choose_to_modify_loan')
        else:
            form = LoansModifyForm(instance=loan_instance)

    return render(request, 'loans/loan_application_modification.html', {
        'form': form,
        'loan_instance': loan_instance,
        'customers': customers,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no_list': gl_no_list,
        'officer': officer,'company':company, 'company_date':company_date,
    })

   



@login_required(login_url='login')
@user_passes_test(check_role_admin)

def choose_loan_approval(request):
    # Get the logged-in user's branch
    user_branch = request.user.branch

    # Filter loans with approval_status 'F' and related customers in the user's branch
    customers = Loans.objects.select_related('customer').filter(
        approval_status='F',
        customer__branch=user_branch
    )

    # Optional: Print customer first names for debugging
    for customer in customers:
        if customer.customer:
            print(customer.customer.first_name)
        else:
            print("No associated customer for this loan.")

    # Pass the filtered customers to the template
    return render(request, 'loans/choose_loan_approval.html', {'customers': customers})



@login_required(login_url='login')
@user_passes_test(check_role_admin)


def loan_approval(request, id):
    customer = get_object_or_404(Loans, id=id)
    cust_data = Account.objects.filter(gl_no__startswith='200').exclude(
        gl_no='200100').exclude(gl_no='200200').exclude(gl_no='200000')
    gl_no = Account.objects.filter(gl_no__startswith='200').values_list('gl_no', flat=True)
    cust_branch = Company.objects.all()
    customers = customer.customer
    officer = Account_Officer.objects.all()
    user = User.objects.get(id=request.user.id)
    branch_id = user.branch_id
    company = get_object_or_404(Branch, id=branch_id)
    
    # Format dates for display
    appli_date = customer.appli_date.strftime('%Y-%m-%d') if customer.appli_date else ''
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    
    if company.session_status == 'Closed':
        return HttpResponse("You cannot post any transaction. Session is closed.") 
    
    if request.method == 'POST':
        form = LoansApproval(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            # Get the approval date from the form
            approval_date = form.cleaned_data.get('approval_date')
            ses_date = company.session_date
            
            # Validate that approval date is not after session date
            if ses_date and approval_date and approval_date > ses_date:
                messages.error(request, "Approval date cannot be after the current session date.")
                return render(request, 'loans/loan_approval.html', {
                    'form': form,
                    'customer': customer,
                    'customers': customers,
                    'cust_data': cust_data,
                    'cust_branch': cust_branch,
                    'gl_no': gl_no,
                    'officer': officer,
                    'appli_date': appli_date,
                    'company_date': company_date,
                })
            
            # Proceed with approval if dates are valid
            customer.approval_status = 'T'
            customer.save()
            form.save()

            messages.success(request, 'Loan Approved successfully!')
            return redirect('choose_loan_approval')
    else:
        initial_data = {'gl_no': customer.gl_no}
        form = LoansApproval(instance=customer, initial=initial_data)

    return render(request, 'loans/loan_approval.html', {
        'form': form,
        'customer': customer,
        'customers': customers,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'appli_date': appli_date,
        'company_date': company_date,
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def reject_loan(request, id):
    customer = get_object_or_404(Loans, id=id)
    cust_data = Account.objects.filter(gl_no__startswith='200').exclude(gl_no='200100').exclude(gl_no='200200').exclude(gl_no='200000')
    gl_no = Account.objects.all().values_list('gl_no', flat=True).filter(gl_no__startswith='200')
    cust_branch = Company.objects.all()
    customers = customer.customer
 
    officer = Account_Officer.objects.all()
    if request.method == 'POST':
        form = LoansRejectForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            customer.approval_status= 'R'
            form.save()
            messages.success(request, 'Loan Approved successfully!')
            
            return redirect('choose_loan_approval')
    else:
        initial_data = {'gl_no': customer.gl_no}
        form = LoansRejectForm(instance=customer, initial=initial_data)
        # form = CustomerForm(instance=customer)
    return render(request, 'loans/reject_loan.html', {'form': form, 'customer': customer , 'customers': customers, 'cust_data': cust_data,
     'cust_branch': cust_branch, 'gl_no': gl_no, 'officer':officer})


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_approved_loan(request):
    customers = Loans.objects.filter(approval_status='T')
 
  
    return render(request, 'loans/choose_reverse_loan_approval.html', {'customers': customers})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def reverse_loan_approval(request, id):
    customer = get_object_or_404(Loans, id=id)
    cust_data = Account.objects.filter(gl_no__startswith='200').exclude(gl_no='200100').exclude(gl_no='200200').exclude(gl_no='200000')
    gl_no = Account.objects.all().values_list('gl_no', flat=True).filter(gl_no__startswith='200')
    cust_branch = Company.objects.all()
    customers = customer.customer
 
    officer = Account_Officer.objects.all()
    if request.method == 'POST':
        form = LoansModifyForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            customer.approval_status= 'F'
            form.save()
            messages.success(request, 'Approved Loan Reversal successfully!')
            
            return redirect('choose_approved_loan')
    else:
        initial_data = {'gl_no': customer.gl_no}
        form = LoansModifyForm(instance=customer, initial=initial_data)
        # form = CustomerForm(instance=customer)
    return render(request, 'loans/reverse_loan_approval.html', {'form': form, 'customer': customer , 'customers': customers, 'cust_data': cust_data,
     'cust_branch': cust_branch, 'gl_no': gl_no, 'officer':officer})



@login_required(login_url='login')
@user_passes_test(check_role_admin)



@login_required(login_url='login')
@user_passes_test(check_role_admin)
@login_required(login_url='login')
@user_passes_test(check_role_admin)
def loan_disbursement_reversal(request, id):

    customer = get_object_or_404(Loans, id=id)
    account = get_object_or_404(Account, gl_no=customer.gl_no)
    customers = customer.customer

    cust_data = Account.objects.filter(
        gl_no__startswith='20'
    ).exclude(gl_no__in=['20100', '20200', '20000'])

    gl_no = Account.objects.filter(
        gl_no__startswith='200'
    ).values_list('gl_no', flat=True)

    ac_no_list = Memtrans.objects.filter(
        ac_no=customer.ac_no
    ).values_list('ac_no', flat=True).distinct()

    cust_branch = Company.objects.all()
    officer = Account_Officer.objects.all()

    amounts = Memtrans.objects.filter(
        ac_no=customer.ac_no,
        gl_no__startswith='2'
    ).values('gl_no').annotate(
        total_amount=Sum('amount')
    ).order_by('-total_amount')

    user = User.objects.get(id=request.user.id)
    company = get_object_or_404(Company, id=user.branch_id)

    # ✅ KEEP DATE AS DATE
    company_date = company.session_date if company.session_date else None

    if company.session_status == 'Closed':
        return HttpResponse("You can not post any transaction. Session is closed.")

    if request.method == 'POST':
        form = MemtransForm(request.POST, request.FILES, instance=customer)

        if form.is_valid():
            with transaction.atomic():

                if not all([
                    account.int_to_recev_gl_dr,
                    account.int_to_recev_ac_dr,
                    account.unearned_int_inc_gl,
                    account.unearned_int_inc_ac
                ]):
                    messages.warning(
                        request,
                        'Please Define all Required Loan Before Disbursement.'
                    )
                    return redirect('choose_to_disburse')

                # ===============================
                # LOAN DISBURSEMENT
                # ===============================
                debit_transaction = Memtrans.objects.create(
                    branch=customer.branch,
                    gl_no=customer.gl_no,
                    ac_no=customer.ac_no,
                    amount=-customer.loan_amount,
                    description='Loan Disbursement - Debit',
                    type='D',
                    ses_date=company_date
                )

                debit_transaction.trx_no = generate_loan_disbursement_id()
                debit_transaction.save()

                credit_transaction = Memtrans.objects.create(
                    branch=form.cleaned_data['branch'],
                    gl_no=form.cleaned_data['gl_no_cashier'],
                    ac_no=form.cleaned_data['ac_no_cashier'],
                    amount=customer.loan_amount,
                    description='Loan Disbursement - Credit',
                    error='A',
                    type='C',
                    ses_date=form.cleaned_data['ses_date']
                )

                credit_transaction.trx_no = debit_transaction.trx_no
                credit_transaction.save()

                # ===============================
                # LOAN SCHEDULE
                # ===============================
                loan_schedule = customer.calculate_loan_schedule()
                customer.disb_status = 'T'
                customer.disbursement_date = form.cleaned_data['ses_date']
                customer.save()

                for payment in loan_schedule:
                    LoanHist.objects.create(
                        branch=customer.branch,
                        gl_no=customer.gl_no,
                        ac_no=customer.ac_no,
                        cycle=customer.cycle,
                        period=payment['period'],
                        trx_date=payment['payment_date'],
                        trx_type='LD',
                        principal=payment['principal_payment'],
                        interest=payment['interest_payment'],
                        penalty=0,
                        trx_no=debit_transaction.trx_no
                    )

                total_interest = LoanHist.objects.filter(
                    gl_no=customers.gl_no,
                    ac_no=customers.ac_no,
                    cycle=customer.cycle
                ).aggregate(
                    total_interest=Sum('interest')
                )['total_interest'] or 0

                customer.total_interest = total_interest
                customer.total_loan = customer.loan_amount + total_interest
                customer.save()

                # ===============================
                # INTEREST POSTINGS
                # ===============================
                int_debit = Memtrans.objects.create(
                    branch=customer.branch,
                    gl_no=account.int_to_recev_gl_dr,
                    ac_no=account.int_to_recev_ac_dr,
                    amount=-customer.total_interest,
                    description='Interest on Loan - Debit',
                    type='L',
                    ses_date=company_date
                )

                int_debit.trx_no = generate_loan_disbursement_id()
                int_debit.save()

                int_credit = Memtrans.objects.create(
                    branch=form.cleaned_data['branch'],
                    gl_no=account.unearned_int_inc_gl,
                    ac_no=account.unearned_int_inc_ac,
                    amount=customer.total_interest,
                    description='Interest on Loan - Credit',
                    type='L',
                    ses_date=company_date
                )

                int_credit.trx_no = int_debit.trx_no
                int_credit.save()

                messages.success(request, 'Loan Disbursed successfully!')
                return redirect('choose_to_disburse')

    else:
        form = LoansModifyForm(instance=customer, initial={'gl_no': customer.gl_no})

    return render(request, 'loans/loan_disbursement_reversal.html', {
        'form': form,
        'customers': customers,
        'customer': customer,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'ac_no_list': ac_no_list,
        'amounts': amounts,
        'account': account,
        'company': company,
        'company_date': company_date,
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Loans

@login_required
def choose_to_disburse(request):
    # Get the branch of the logged-in user
    user_branch = request.user.branch  

    # Filter loans that belong to the user's branch, approved but not disbursed
    customers = Loans.objects.select_related('customer').filter(
        approval_status='T',
        disb_status='F',
        branch=user_branch
    )

    # Debugging (optional): print customer names
    for customer in customers:
        if customer.customer:
            print(customer.customer.first_name)
        else:
            print("No associated customer for this loan.")

    # Render results
    return render(request, 'loans/choose_to_disburse.html', {'customers': customers})


 # Assuming you have this utility function




from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Loans

@login_required
def choose_to_direct_disburse(request):
    # Get the logged-in user's branch
    user_branch = request.user.branch  

    # Filter loans that belong to this branch, not approved yet and not disbursed
    customers = Loans.objects.select_related('customer').filter(
        approval_status='F',
        disb_status='F',
        branch=user_branch
    )

    # Debugging: print customer names
    for customer in customers:
        if customer.customer:
            print(customer.customer.first_name)
        else:
            print("No associated customer for this loan.")

    # Pass the customers data to the template
    return render(request, 'loans/choose_to_disburse.html', {'customers': customers})


from decimal import InvalidOperation

@login_required(login_url='login')
@user_passes_test(check_role_admin)

def loan_disbursement(request, id):
    loan = get_object_or_404(Loans, id=id)
    account = get_object_or_404(Account, gl_no=loan.gl_no)
    customer = loan.customer
    
    cust_data = Account.objects.filter(gl_no__startswith='20').exclude(gl_no__in=['20100', '20200', '20000'])
    gl_no = Account.objects.filter(gl_no__startswith='200').values_list('gl_no', flat=True)
    ac_no_list = Memtrans.objects.filter(ac_no=loan.ac_no).values_list('ac_no', flat=True).distinct()
    cust_branch = Company.objects.all()
    amounts = Memtrans.objects.filter(ac_no=loan.ac_no, gl_no__startswith='2').values('gl_no').annotate(total_amount=Sum('amount')).order_by('-total_amount')
    officer = Account_Officer.objects.all()
    
    user = request.user
    branch_id = user.branch_id
    company = get_object_or_404(Branch, id=branch_id)
    company_date = company.session_date  # keep it as date

    customer_branch = customer.branch
    user_branch = request.user.branch

    if loan.appli_date:
        appli_date = loan.appli_date.strftime('%Y-%m-%d')
    else:
        appli_date = ''
    
    if loan.approval_date:
        approve_date = loan.approval_date.strftime('%Y-%m-%d')
    else:
        approve_date = ''
    
    if company.session_status == 'Closed':
        return HttpResponse("You cannot post any transaction. Session is closed.")
    else:
        if request.method == 'POST':
            form = MemtransForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    # Get VAT and application fee amounts from POST data
                    loan_appl_vat = Decimal(request.POST.get('loan_appl_vat', '0'))
                    application_fee = Decimal(request.POST.get('application_fee', '0'))
                    
                    if loan_appl_vat < 0 or application_fee < 0:
                        raise ValueError("Amounts cannot be negative")
                        
                except (ValueError, InvalidOperation) as e:
                    messages.error(request, f"Invalid amount: {str(e)}")
                    return redirect('choose_to_disburse')

                ses_date = form.cleaned_data['ses_date']
                disbursement_date = request.POST.get('disbursement_date')

                if ses_date > company.session_date:
                    messages.warning(request, 'Transaction date cannot be greater than the session date.')
                    return redirect('choose_to_disburse')
                
                # Define all required GL/AC parameters
                required_gl_ac_params = [
                    ('interest_gl', account.interest_gl),
                    ('interest_ac', account.interest_ac),
                    ('pen_gl_no', account.pen_gl_no),
                    ('pen_ac_no', account.pen_ac_no),
                    ('prov_cr_gl_no', account.prov_cr_gl_no),
                    ('prov_cr_ac_no', account.prov_cr_ac_no),
                    ('prov_dr_gl_no', account.prov_dr_gl_no),
                    ('prov_dr_ac_no', account.prov_dr_ac_no),
                    ('writ_off_dr_gl_no', account.writ_off_dr_gl_no),
                    ('writ_off_dr_ac_no', account.writ_off_dr_ac_no),
                    ('writ_off_cr_gl_no', account.writ_off_cr_gl_no),
                    ('writ_off_cr_ac_no', account.writ_off_cr_ac_no),
                    ('loan_com_gl_no', account.loan_com_gl_no),
                    ('loan_com_ac_no', account.loan_com_ac_no),
                    ('int_to_recev_gl_dr', account.int_to_recev_gl_dr),
                    ('int_to_recev_ac_dr', account.int_to_recev_ac_dr),
                    ('unearned_int_inc_gl', account.unearned_int_inc_gl),
                    ('unearned_int_inc_ac', account.unearned_int_inc_ac),
                    ('loan_com_gl_vat', account.loan_com_gl_vat),
                    ('loan_com_ac_vat', account.loan_com_ac_vat),
                    ('loan_proc_gl_vat', account.loan_proc_gl_vat),
                    ('loan_proc_ac_vat', account.loan_proc_ac_vat),
                    ('loan_appl_gl_vat', account.loan_appl_gl_vat),
                    ('loan_appl_ac_vat', account.loan_appl_ac_vat),
                    ('loan_commit_gl_vat', account.loan_commit_gl_vat),
                    ('loan_commit_ac_vat', account.loan_commit_ac_vat)
                ]

                # Check required parameters
                missing_params = [name for name, value in required_gl_ac_params if not value]
                if missing_params:
                    messages.warning(
                        request,
                        f'Please define all required loan paramenters before disbursement' 
                        # f'Missing required parameters: {", ".join(missing_params)}'
                    )
                    return redirect('choose_to_disburse')

                # Verify GL/AC numbers exist
                missing_customer_accounts = []
                for name, gl_no in required_gl_ac_params[::2]:
                    ac_name = name.replace('_gl', '_ac')
                    ac_no = next((value for n, value in required_gl_ac_params if n == ac_name), None)
                    
                    if gl_no and ac_no:
                        try:
                            Customer.objects.get(gl_no=gl_no, ac_no=ac_no)
                        except Customer.DoesNotExist:
                            missing_customer_accounts.append(f"{gl_no}/{ac_no}")

                if missing_customer_accounts:
                    messages.warning(
                        request,
                        f'Missing customer accounts: {", ".join(missing_customer_accounts)}'
                    )
                    return redirect('choose_to_disburse')

                customer_id = customer.id
                with transaction.atomic():
                    unique_trx_no = generate_loan_disbursement_id()

                    # ===== APPLICATION FEE PROCESSING =====
                    if application_fee > 0:
                        # 1. Debit Customer (loan account)
                        Memtrans.objects.create(
                            branch=user_branch,
                            cust_branch=customer_branch,
                            customer_id=customer_id,
                            cycle=loan.cycle,
                            gl_no=form.cleaned_data['gl_no_cashier'],
                            ac_no=form.cleaned_data['ac_no_cashier'],
                            amount=-application_fee,
                            description=f'Loan Application Fee - {customer.first_name}',
                            type='D',
                            account_type='L',
                            code='LA',
                            sys_date=timezone.now(),
                            ses_date=ses_date,
                            app_date=form.cleaned_data['app_date'],
                            trx_no=unique_trx_no,
                            user=request.user
                        )

                        # 2. Credit Application Fee Account
                        Memtrans.objects.create(
                            branch=user_branch,
                            cust_branch=customer_branch,
                            customer_id=customer_id,
                            cycle=loan.cycle,
                            gl_no=account.loan_appl_fee_gl_vat,
                            ac_no=account.loan_appl_fee_ac_vat,
                            amount=application_fee,
                            description=f'App Fee from {customer.gl_no}-{customer.ac_no}',
                            type='C',
                            account_type='I',
                            code='LA',
                            sys_date=timezone.now(),
                            ses_date=ses_date,
                            app_date=form.cleaned_data['app_date'],
                            trx_no=unique_trx_no,
                            user=request.user
                        )

                    # ===== VAT PROCESSING =====
                    if loan_appl_vat > 0:
                        # 1. Debit Customer (loan account)
                        Memtrans.objects.create(
                            branch=user_branch,
                            cust_branch=customer_branch,
                            customer_id=customer_id,
                            cycle=loan.cycle,
                            gl_no=form.cleaned_data['gl_no_cashier'],
                            ac_no=form.cleaned_data['ac_no_cashier'],
                            amount=-loan_appl_vat,
                            description=f'Loan VAT - {customer.first_name}',
                            type='D',
                            account_type='L',
                            code='LV',
                            sys_date=timezone.now(),
                            ses_date=ses_date,
                            app_date=form.cleaned_data['app_date'],
                            trx_no=unique_trx_no,
                            user=request.user
                        )

                        # 2. Credit VAT Account
                        Memtrans.objects.create(
                            branch=user_branch,
                            cust_branch=customer_branch,
                            customer_id=customer_id,
                            cycle=loan.cycle,
                            gl_no=account.loan_appl_gl_vat,
                            ac_no=account.loan_appl_ac_vat,
                            amount=loan_appl_vat,
                            description=f'VAT from {customer.gl_no}-{customer.ac_no}',
                            type='C',
                            account_type='V',
                            code='LV',
                            sys_date=timezone.now(),
                            ses_date=ses_date,
                            app_date=form.cleaned_data['app_date'],
                            trx_no=unique_trx_no,
                            user=request.user
                        )

                    # ===== MAIN LOAN DISBURSEMENT =====
                    # Debit transaction
                    Memtrans.objects.create(
                        branch=user_branch,
                        cust_branch=customer_branch,
                        customer_id=customer_id,
                        cycle=loan.cycle,
                        gl_no=loan.gl_no,
                        ac_no=loan.ac_no,
                        amount=-loan.loan_amount,
                        description='Loan Disbursement - Debit',
                        type='D',
                        account_type='L',
                        code='LD',
                        sys_date=timezone.now(),
                        ses_date=ses_date,
                        app_date=form.cleaned_data['app_date'],
                        trx_no=unique_trx_no,
                        user=request.user
                    )

                    # Credit transaction
                    Memtrans.objects.create(
                        branch=user_branch,
                        cust_branch=customer_branch,
                        customer_id=customer_id,
                        cycle=loan.cycle,
                        gl_no=form.cleaned_data['gl_no_cashier'],
                        ac_no=form.cleaned_data['ac_no_cashier'],
                        amount=loan.loan_amount,
                        description=f'{customer.first_name} {customer.last_name}',
                        error='A',
                        type='C',
                        account_type='C',
                        code='LD',
                        sys_date=timezone.now(),
                        ses_date=ses_date,
                        app_date=form.cleaned_data['app_date'],
                        trx_no=unique_trx_no,
                        user=request.user
                    )

                    # Calculate and save loan schedule
                    loan_schedule = loan.calculate_loan_schedule()
                    loan.approval_status = 'T'
                    loan.disb_status = 'T'
                    loan.cust_gl_no = form.cleaned_data['gl_no_cashier']
                    loan.disbursement_date = disbursement_date
                    loan.save()

                    # Save schedule to LoanHist
                    for payment in loan_schedule:
                        LoanHist.objects.create(
                            branch=loan.branch,
                            gl_no=loan.gl_no,
                            ac_no=loan.ac_no,
                            cycle=loan.cycle,
                            period=payment['period'],
                            trx_date=payment['payment_date'],
                            trx_type='LD',
                            trx_naration='Repayment Due',
                            principal=payment['principal_payment'],
                            interest=payment['interest_payment'],
                            penalty=0,
                            trx_no=unique_trx_no
                        )

                    # Calculate total interest
                    total_interest = LoanHist.objects.filter(
                        gl_no=loan.gl_no, 
                        ac_no=loan.ac_no, 
                        cycle=loan.cycle
                    ).aggregate(total_interest=Sum('interest'))['total_interest'] or 0

                    # Update loan totals
                    loan.total_loan = loan.loan_amount + total_interest
                    loan.total_interest = total_interest
                    loan.save()

                    # Interest accounting entries
                    Memtrans.objects.create(
                        branch=user_branch,
                        cust_branch=customer_branch,
                        customer_id=customer_id,
                        cycle=loan.cycle,
                        gl_no=account.int_to_recev_gl_dr,
                        ac_no=account.int_to_recev_ac_dr,
                        amount=-loan.total_interest,
                        description=f'Interest for {customer.gl_no}-{customer.ac_no}',
                        type='D',
                        account_type='I',
                        code='LD',
                        sys_date=timezone.now(),
                        ses_date=ses_date,
                        app_date=form.cleaned_data['app_date'],
                        trx_no=unique_trx_no,
                        user=request.user
                    )

                    Memtrans.objects.create(
                        branch=user_branch,
                        cust_branch=customer_branch,
                        customer_id=customer_id,
                        cycle=loan.cycle,
                        gl_no=account.unearned_int_inc_gl,
                        ac_no=account.unearned_int_inc_ac,
                        amount=loan.total_interest,
                        description=f'Interest Income for {customer.gl_no}-{customer.ac_no}',
                        type='C',
                        account_type='I',
                        code='LD',
                        sys_date=timezone.now(),
                        ses_date=ses_date,
                        app_date=form.cleaned_data['app_date'],
                        trx_no=unique_trx_no,
                        user=request.user
                    )

                    success_msg = 'Loan disbursed successfully'
                    if application_fee > 0:
                        success_msg += ' with application fee'
                    if loan_appl_vat > 0:
                        success_msg += ' and VAT'
                    messages.success(request, success_msg + '!')
                    
                    return redirect('choose_to_disburse')
            else:
                messages.error(request, 'Form is not valid')
                return redirect('choose_to_disburse')
        else:
            initial_data = {'gl_no': loan.gl_no}
            form = LoansModifyForm(instance=loan, initial=initial_data)

    return render(request, 'loans/loan_disbursement.html', {
        'form': form,
        'customers': customer,
        'loan': loan,
        'customer': loan,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'ac_no_list': ac_no_list,
        'amounts': amounts,
        'account': account,
        'company': company,
        'company_date': company_date,
        'appli_date': appli_date,
        'approve_date': approve_date,
        'default_vat': getattr(loan, 'application_fee_vat', 0),
        'default_app_fee': getattr(loan, 'application_fee', 0)
    })



from django.db.models import Sum

@login_required(login_url='login')
@user_passes_test(check_role_admin)

def loan_schedule_view(request, loan_id):
    loan_instance = get_object_or_404(Loans, id=loan_id)
    loan_schedule = loan_instance.calculate_loan_schedule()
    customers = loan_instance.customer

    # ✅ Get the branch from the loan
    branch = loan_instance.branch  
    # ✅ Get the company from the branch
    company = branch.company  

    print(f"Loan Instance: {loan_id}")

    total_interest_sum = sum(payment['interest_payment'] for payment in loan_schedule)
    total_principal_sum = sum(payment['principal_payment'] for payment in loan_schedule)
    total_payments_sum = sum(payment['total_payment'] for payment in loan_schedule)

    context = {
        'loan_instance': loan_instance,
        'loan_schedule': loan_schedule,
        'total_interest_sum': total_interest_sum,
        'total_principal_sum': total_principal_sum,
        'total_payments_sum': total_payments_sum,
        'customers': customers,
        'company': company,
        'branch': branch,   # ✅ Pass branch separately
    }

    return render(request, 'loans/loan_schedule_template.html', context)









# views.py

from django.shortcuts import render
from .forms import LoanApplicationForm, LoanApplicationForm, LoansApproval, LoansChooseRepaymeny, LoansModifyForm, LoansRejectForm, MemtransForm
from .utils import calculate_loan_schedule # Create a utility function for calculating loan schedule


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def loan_schedule_demo(request):
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST)
        if form.is_valid():
            form.set_numerical_value()
            # Calculate loan schedule using form data
            loan_schedule = form.calculate_loan_schedule()

            # Pass form and loan_schedule to the context
            total_interest_sum = sum(payment['interest_payment'] for payment in loan_schedule)
            total_principal_sum = sum(payment['principal_payment'] for payment in loan_schedule)
            total_payments_sum = sum(payment['total_payment'] for payment in loan_schedule)

            context = {
                'form': form,
                'loan_schedule': loan_schedule,
                'total_interest_sum': total_interest_sum,
                'total_principal_sum': total_principal_sum,
                'total_payments_sum': total_payments_sum,
            }

            return render(request, 'loans/loan_schedule_demo.html', context)

    # If it's a GET request or the form is not valid, display an empty form
    form = LoanApplicationForm()
    context = {
        'form': form,
    }
    return render(request, 'loans/loan_schedule_form.html', context)




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_loan_repayment(request):
    # Filter customers with loan approval status set to 'F'
    customers = Loans.objects.select_related('customer').filter(total_loan__gt=0)
    
  
    # Pass the customers data to the template
    return render(request, 'loans/choose_loan_repayment.html', {'customers': customers})










from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Sum
from django.contrib import messages
from .forms import LoanHistForm
from company.models import Company



@login_required(login_url='login')
@user_passes_test(check_role_admin)  

def loan_repayment(request, id):
    customer = get_object_or_404(Loans, id=id)
    account = get_object_or_404(Account, gl_no=customer.gl_no)
    customers = customer.customer

    cust_data = Account.objects.filter(gl_no__startswith='20').exclude(gl_no__in=['20100', '20200', '20000'])
    gl_no = Account.objects.filter(gl_no__startswith='200').values_list('gl_no', flat=True)
    ac_no_list = Memtrans.objects.filter(ac_no=customer.ac_no).values_list('ac_no', flat=True).distinct()
    cust_branch = Branch.objects.all()
    amounts = Memtrans.objects.filter(ac_no=customer.ac_no, gl_no__startswith='2').values('gl_no').annotate(total_amount=Sum('amount')).order_by('-total_amount')
    officer = Account_Officer.objects.all()

    user = User.objects.get(id=request.user.id)
    branch_id = user.branch_id
    company = get_object_or_404(Branch, id=branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    
    customer_branch = customer.branch
    user_branch = request.user.branch
    total_principal_currently = LoanHist.objects.filter(trx_date__lt=company_date, gl_no=customer.gl_no, ac_no=customer.ac_no, cycle=customer.cycle).aggregate(Sum('principal'))['principal__sum'] or 0
    total_interest_currently = LoanHist.objects.filter(trx_date__lt=company_date, gl_no=customer.gl_no, ac_no=customer.ac_no, cycle=customer.cycle).aggregate(Sum('interest'))['interest__sum'] or 0

    total_principal = LoanHist.objects.filter(gl_no=customer.gl_no, ac_no=customer.ac_no, cycle=customer.cycle).aggregate(Sum('principal'))['principal__sum'] or 0
    total_interest = LoanHist.objects.filter(gl_no=customer.gl_no, ac_no=customer.ac_no, cycle=customer.cycle).aggregate(Sum('interest'))['interest__sum'] or 0

    disbursement_date = customer.disbursement_date
    total_principal_between_dates = LoanHist.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        cycle=customer.cycle,
        trx_date__gte=disbursement_date,
        trx_date__lte=company_date
    ).aggregate(total_principal=Sum('principal'))['total_principal'] or 0

    total_interest_between_dates = LoanHist.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        cycle=customer.cycle,
        trx_date__gte=disbursement_date,
        trx_date__lte=company_date
    ).aggregate(total_interest=Sum('interest'))['total_interest'] or 0

    last_lp_date = LoanHist.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        cycle=customer.cycle,
        trx_type='LP'
    ).aggregate(Max('trx_date'))['trx_date__max']

    if company.session_status == 'Closed':
        return HttpResponse("You cannot post any transaction. Session is closed.")

    if request.method == 'POST':
        form = MemtransForm(request.POST, request.FILES, instance=customer)
        app_date = request.POST.get('app_date')
        if form.is_valid():
            app_date = form.cleaned_data['app_date']
            ses_date = form.cleaned_data['ses_date']

            if app_date > ses_date:
                messages.error(request, 'Error: The Application Date (app_date) cannot be greater than the Session Date (ses_date).')
                return redirect('loan_repayment', id=id)

            principal = float(request.POST.get('principal'))
            interest = float(request.POST.get('interest'))
            penalty = float(request.POST.get('penalty'))
            total_paid = float(request.POST.get('total_paid'))
            
            with transaction.atomic():
                unique_id = generate_loan_repayment_id()
                
                if account.int_to_recev_gl_dr and account.int_to_recev_ac_dr and account.unearned_int_inc_gl and account.unearned_int_inc_ac:
                    debit_transaction = Memtrans(
                        branch=user_branch,
                        cust_branch=customer_branch,
                        gl_no=form.cleaned_data['gl_no_cashier'],
                        ac_no=form.cleaned_data['ac_no_cashier'],
                        cycle=customer.cycle,
                        amount=-principal,
                        description='Principal Loan Repayment - Debit',
                        type='D',
                        account_type='C',
                        ses_date=company_date if company_date else None,
                        app_date=form.cleaned_data['app_date'],
                        trx_no=unique_id,
                        code='LP',
                        user=request.user
                    )
                    debit_transaction.save()

                    credit_transaction = Memtrans(
                        branch=user_branch,
                        cust_branch=customer_branch,
                        gl_no=customer.gl_no,
                        ac_no=customer.ac_no,
                        cycle=customer.cycle,
                        amount=principal,
                        description=f'{customers.first_name}, {customers.last_name}, {customers.gl_no}-{customers.ac_no} Principal Loan Repayment - Debit',
                        error='A',
                        type='C',
                        account_type='L',
                        ses_date=form.cleaned_data['ses_date'],
                        app_date=form.cleaned_data['app_date'],
                        trx_no=unique_id,
                        code='LP',
                        user=request.user
                    )
                    credit_transaction.save()

                    debit_transaction_interest = Memtrans(
                        cust_branch=customer_branch,
                        branch=user_branch,
                        gl_no=form.cleaned_data['gl_no_cashier'],
                        ac_no=form.cleaned_data['ac_no_cashier'],
                        cycle=customer.cycle,
                        amount=-interest,
                        description='Loan Interest - Debit',
                        type='D',
                        account_type='C',
                        ses_date=company_date,
                        app_date=form.cleaned_data['app_date'],
                        trx_no=unique_id,
                        code='LP',
                        user=request.user
                    )
                    debit_transaction_interest.save()

                    credit_transaction_interest = Memtrans(
                        cust_branch=customer_branch,
                        branch=user_branch,
                        gl_no=account.interest_gl,
                        ac_no=account.interest_ac,
                        cycle=customer.cycle,
                        amount=interest,
                        description=f'{customers.first_name}, {customers.last_name}, {customers.gl_no}-{customers.ac_no} Interest Repayment - Debit',
                        error='A',
                        type='C',
                        account_type='I',
                        ses_date=form.cleaned_data['ses_date'],
                        app_date=form.cleaned_data['app_date'],
                        trx_no=unique_id,
                        code='LP',
                        user=request.user
                    )
                    credit_transaction_interest.save()

                    lp_count = LoanHist.objects.filter(
                        gl_no=customer.gl_no,
                        ac_no=customer.ac_no,
                        cycle=customer.cycle,
                        trx_type='LP'
                    ).count()
                    period = lp_count + 1

                    loanhist_entry = LoanHist(
                        branch=customer_branch,
                        gl_no=customer.gl_no,
                        ac_no=customer.ac_no,
                        cycle=customer.cycle,
                        trx_date=app_date,
                        period=str(period),
                        trx_type='LP',
                        trx_naration='Loan Repayment',
                        principal=-principal,
                        interest=-interest,
                        penalty=-penalty,
                        trx_no=unique_id
                    )
                    loanhist_entry.save()

                    total_interest = LoanHist.objects.filter(gl_no=customers.gl_no, ac_no=customers.ac_no, cycle=customer.cycle).aggregate(Sum('interest'))['interest__sum'] or 0
                    total_principal = LoanHist.objects.filter(gl_no=customers.gl_no, ac_no=customers.ac_no, cycle=customer.cycle).aggregate(Sum('principal'))['principal__sum'] or 0

                    customer.total_loan = total_principal + total_interest
                    customer.total_interest = total_interest
                    customer.save()

                    debit_transaction_interest_accounting = Memtrans(
                        cust_branch=customer_branch,
                        branch=user_branch,
                        gl_no=account.int_to_recev_gl_dr,
                        ac_no=account.int_to_recev_ac_dr,
                        cycle=customer.cycle,
                        amount=-interest,
                        description=f'{customers.first_name}-{customers.last_name}-{customers.gl_no}-{customers.ac_no}',
                        type='D',
                        account_type='I',
                        ses_date=company_date,
                        app_date=form.cleaned_data['app_date'],
                        trx_no=unique_id,
                        code='LP',
                        user=request.user
                    )
                    debit_transaction_interest_accounting.save()

                    credit_transaction_interest_accounting = Memtrans(
                        cust_branch=customer_branch,
                        branch=user_branch,
                        gl_no=account.unearned_int_inc_gl,
                        ac_no=account.unearned_int_inc_ac,
                        cycle=customer.cycle,
                        amount=interest,
                        description=f'{customers.first_name}-{customers.last_name}-{customers.gl_no}-{customers.ac_no}',
                        type='C',
                        account_type='I',
                        ses_date=company_date,
                        app_date=form.cleaned_data['app_date'],
                        trx_no=unique_id,
                        code='LP',
                        user=request.user
                    )
                    credit_transaction_interest_accounting.save()

                    messages.success(request, 'Loan Repayment successfully!')
                    return redirect('choose_loan_repayment')
                else:
                    messages.warning(request, 'Please define all required loan parameters before disbursement.')
                    return redirect('choose_loan_repayment')
    else:
        initial_data = {'gl_no': customer.gl_no}
        form = LoansModifyForm(instance=customer, initial=initial_data)

    return render(request, 'loans/loan_repayment.html', {
        'form': form,
        'customers': customers,
        'customer': customer,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'ac_no_list': ac_no_list,
        'amounts': amounts,
        'account': account,
        'company': company,
        'company_date': company_date,
        'total_principal_currently': total_principal_currently,
        'total_interest_currently': total_interest_currently,
        'total_principal_between_dates': total_principal_between_dates,
        'total_interest_between_dates': total_interest_between_dates,
        'total_principal': total_principal,
        'total_interest': total_interest,
        'last_lp_date': last_lp_date,
    })



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_loan_written_off(request):
    # Filter customers with loan approval status set to 'F'
    customers = Loans.objects.select_related('customer').filter(total_loan__gt=0)
  
    # Pass the customers data to the template
    return render(request, 'loans/choose_loan_written_off.html', {'customers': customers})


#Written-off Loan
@login_required(login_url='login')
@user_passes_test(check_role_admin)  

def loan_written_off(request, id):
    customer = get_object_or_404(Loans, id=id)
    account = get_object_or_404(Account, gl_no=customer.gl_no)
    customers = customer.customer

    cust_data = Account.objects.filter(gl_no__startswith='20').exclude(gl_no__in=['20100', '20200', '20000'])
    gl_no = Account.objects.filter(gl_no__startswith='200').values_list('gl_no', flat=True)
    ac_no_list = Memtrans.objects.filter(ac_no=customer.ac_no).values_list('ac_no', flat=True).distinct()
    cust_branch = Company.objects.all()
    amounts = Memtrans.objects.filter(ac_no=customer.ac_no, gl_no__startswith='2').values('gl_no').annotate(total_amount=Sum('amount')).order_by('-total_amount')
    officer = Account_Officer.objects.all()

    user = User.objects.get(id=request.user.id)
    branch_id = user.branch_id
    company = get_object_or_404(Company, id=branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    
    total_principal_currently = LoanHist.objects.filter(trx_date__lt=company_date, gl_no=customer.gl_no,ac_no=customer.ac_no,cycle=customer.cycle).aggregate(Sum('principal'))['principal__sum'] or 0
    total_interest_currently = LoanHist.objects.filter(trx_date__lt=company_date,gl_no=customer.gl_no,ac_no=customer.ac_no, cycle=customer.cycle).aggregate(Sum('interest'))['interest__sum'] or 0

    # Sum the principal using gl_no, ac_no, and cycle
    total_principal = LoanHist.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        cycle=customer.cycle
    ).aggregate(Sum('principal'))['principal__sum'] or 0

    # Sum the interest using gl_no, ac_no, and cycle
    total_interest = LoanHist.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        cycle=customer.cycle
    ).aggregate(Sum('interest'))['interest__sum'] or 0

    # Calculate the total balance of the loan
    # total_balance = total_principal + total_interest
    # Sum the principal between disbursement and session date
    disbursement_date = customer.disbursement_date
    total_principal_between_dates = LoanHist.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        cycle=customer.cycle,
        trx_date__gte=disbursement_date,
        trx_date__lte=company_date
    ).aggregate(total_principal=Sum('principal'))['total_principal'] or 0

    total_interest_between_dates = LoanHist.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        cycle=customer.cycle,
        trx_date__gte=disbursement_date,
        trx_date__lte=company_date
    ).aggregate(total_interest=Sum('interest'))['total_interest'] or 0

        # Get the last LP date
    # Calculate the last LP date
    last_lp_date = LoanHist.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        cycle=customer.cycle,
        trx_type='LP'
    ).aggregate(Max('trx_date'))['trx_date__max']

    if company.session_status == 'Closed':
        return HttpResponse("You cannot post any transaction. Session is closed.")

    if request.method == 'POST':
        form = MemtransForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            principal = float(request.POST.get('principal'))
            interest = float(request.POST.get('interest'))
            penalty = float(request.POST.get('penalty'))
            total_paid = float(request.POST.get('total_paid'))
            
            with transaction.atomic():
                # Generate a unique transaction ID for this repayment session
                unique_id = generate_loan_written_off_id()
                
                if account.int_to_recev_gl_dr and account.int_to_recev_ac_dr and account.unearned_int_inc_gl and account.unearned_int_inc_ac:
                    debit_transaction = Memtrans(
                        branch=customer.branch,
                        gl_no=account.writ_off_dr_gl_no,
                        ac_no=account.writ_off_dr_ac_no,
                        cycle=customer.cycle,
                        amount=-principal,
                        description=f'{customers.first_name}, {customers.last_name}, {customers.gl_no}-{customers.ac_no} - Loan Written Off Principal',
                        type='D',
                        account_type='I',
                        ses_date=company_date,
                        trx_no=unique_id  # Set trx_no to the unique ID
                    )
                    debit_transaction.save()

                    credit_transaction = Memtrans(
                        branch=form.cleaned_data['branch'],
                        gl_no=customer.gl_no,
                        ac_no=customer.ac_no,
                        cycle=customer.cycle,
                        amount=principal,
                        description=f'{customers.first_name}, {customers.last_name}, {customers.gl_no}-{customers.ac_no} - Loan Written Off Principal',
                        error='A',
                        type='C',
                        account_type='L',
                        ses_date=form.cleaned_data['ses_date'],
                        trx_no=unique_id  # Set trx_no to the unique ID
                    )
                    credit_transaction.save()


               

                    # Counting existing 'LP' transactions to set the period
                    lp_count = LoanHist.objects.filter(
                        gl_no=customer.gl_no,
                        ac_no=customer.ac_no,
                        cycle=customer.cycle,
                        trx_type='LW'
                    ).count()
                    period = lp_count + 1

                    loanhist_entry = LoanHist(
                        branch=customer.branch,
                        gl_no=customer.gl_no,
                        ac_no=customer.ac_no,
                        cycle=customer.cycle,
                        trx_date=credit_transaction.ses_date,
                        period=str(period),  # Setting the period based on the count
                        trx_type='LW',
                        principal=-principal,
                        interest=-interest,
                        penalty=-penalty,
                        trx_no=unique_id  # Set trx_no to the unique ID
                    )
                    loanhist_entry.save()

                    total_interest = LoanHist.objects.filter(gl_no=customers.gl_no, ac_no=customers.ac_no, cycle=customer.cycle).aggregate(Sum('interest'))['interest__sum'] or 0
                    total_principal = LoanHist.objects.filter(gl_no=customers.gl_no, ac_no=customers.ac_no, cycle=customer.cycle).aggregate(Sum('principal'))['principal__sum'] or 0

                    customer.total_loan = total_principal + total_interest
                    customer.total_interest = total_interest
                    customer.save()

                    # Additional interest transaction for accounting
                    debit_transaction_interest_accounting = Memtrans(
                        branch=customer.branch,
                        gl_no=account.unearned_int_inc_gl,
                        ac_no=account.unearned_int_inc_ac,
                        cycle=customer.cycle,
                        amount=-interest,
                        description=f'{customers.first_name}-{customers.last_name}-{customers.gl_no}-{customers.ac_no} - Loan Written Off interest',
                        type='D',
                        account_type='I',
                        ses_date=company_date,
                        trx_no=unique_id  # Set trx_no to the unique ID
                    )
                    debit_transaction_interest_accounting.save()

                    credit_transaction_interest_accounting = Memtrans(
                        branch=form.cleaned_data['branch'],
                        gl_no=account.int_to_recev_gl_dr,
                        ac_no=account.int_to_recev_ac_dr,
                        cycle=customer.cycle,
                        amount=interest,
                        description=f'{customers.first_name}-{customers.last_name}-{customers.gl_no}-{customers.ac_no} - Loan Written Off interest',
                        type='C',
                        account_type='I',
                        ses_date=company_date,
                        trx_no=unique_id  # Set trx_no to the unique ID
                    )
                    credit_transaction_interest_accounting.save()

                    messages.success(request, 'Loan Repayment successfully!')
                    return redirect('choose_loan_repayment')
                else:
                    messages.warning(request, 'Please define all required loan parameters before disbursement.')
                    return redirect('choose_loan_repayment')
    else:
        initial_data = {'gl_no': customer.gl_no}
        form = LoansModifyForm(instance=customer, initial=initial_data)

    return render(request, 'loans/loan_written_off.html', {
        'form': form,
        'customers': customers,
        'customer': customer,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'ac_no_list': ac_no_list,
        'amounts': amounts,
        'account': account,
        'company': company,
        'company_date': company_date,
        'total_principal_currently': total_principal_currently,
        'total_interest_currently': total_interest_currently,
        'total_principal_between_dates': total_principal_between_dates,
        'total_interest_between_dates':total_interest_between_dates,  # Added to context
        'total_principal':total_principal,
        'total_interest':total_interest,
        'last_lp_date':last_lp_date,
    })





from django.db.models import Sum


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def loan_due(request):
    # Filter customers with approval status 'T'
    customers = Loans.objects.filter(approval_status='T')

    user = User.objects.get(id=request.user.id)
    branch_id = user.branch_id
    company = get_object_or_404(Company, id=branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''

    # Annotate each customer with their total principal and total interest
    for customer in customers:
        customer.total_principal = LoanHist.objects.filter(trx_date__lt=company_date, cycle=customer.cycle).aggregate(total_principal=Sum('principal'))['total_principal'] or 0
        customer.total_interest = LoanHist.objects.filter(trx_date__lt=company_date, cycle=customer.cycle).aggregate(total_interest=Sum('interest'))['total_interest'] or 0

    return render(request, 'loans/loan_due.html', {'customers': customers})







from django.shortcuts import render, redirect, get_object_or_404
from .models import Loans
from django.db.models import F
from transactions.models import Memtrans
from django.contrib import messages

def display_loan_disbursements(request):
    # Query loans that have been disbursed
    disbursement_reversals = Loans.objects.filter(disb_status='T').select_related('customer')

    # Prepare data for rendering in the template
    disbursement_reversals_details = []

    for reversal in disbursement_reversals:
        # Fetch customer details
        customer = reversal.customer
        gl_no = customer.gl_no
        ac_no = customer.ac_no
        cycle = reversal.cycle
        customer_name = f"{customer.first_name} {customer.last_name}"
        
        # Retrieve transaction number and reversal date from Memtrans model
        memtrans_instance = Memtrans.objects.filter(gl_no=gl_no, ac_no=ac_no, cycle=cycle).first()
        trx_no = memtrans_instance.trx_no if memtrans_instance else None
        reversal_date = memtrans_instance.ses_date if memtrans_instance else None
        
        # Append loan details to the list
        disbursement_reversals_details.append({
            'id': reversal.id,
            'customer_name': customer_name,
            'loan_amount': reversal.loan_amount,
            'disbursement_date': reversal.disbursement_date,
            'reversal_date': reversal_date,
            'trx_no': trx_no,
        })

    # Pass data to the template for rendering
    return render(request, 'loans/display_loan_disbursements.html', {'disbursement_reversals': disbursement_reversals_details})

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import Loans, LoanHist
from transactions.models import Memtrans

def display_loan_disbursements(request):
    """
    Display loans that have been disbursed, with reversal option.
    """
    disbursement_reversals = Loans.objects.filter(disb_status='T').select_related('customer')

    disbursement_reversals_details = []

    for reversal in disbursement_reversals:
        customer = reversal.customer
        gl_no = customer.gl_no
        ac_no = customer.ac_no
        cycle = reversal.cycle
        customer_name = f"{customer.first_name} {customer.last_name}"

        memtrans_instance = Memtrans.objects.filter(gl_no=gl_no, ac_no=ac_no, cycle=cycle).first()
        trx_no = memtrans_instance.trx_no if memtrans_instance else None
        reversal_date = memtrans_instance.ses_date if memtrans_instance else None

        disbursement_reversals_details.append({
            'id': reversal.id,
            'customer_name': customer_name,
            'loan_amount': reversal.loan_amount,
            'disbursement_date': reversal.disbursement_date,
            'reversal_date': reversal_date,
            'trx_no': trx_no,
        })

    context = {
        'disbursement_reversals': disbursement_reversals_details,
        'today': timezone.now().date(),  # Used for max date in the form
    }
    return render(request, 'loans/display_loan_disbursements.html', context)


def delete_loan_transactions(request, trx_no, id):
    """
    Delete loan transactions for a given trx_no and loan id.
    Requires user to specify a deletion date.
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method. Please submit the deletion form.")
        return redirect('display_loan_disbursements')

    deletion_date_str = request.POST.get('deletion_date')
    if not deletion_date_str:
        messages.error(request, "Deletion date is required. Please select a valid date.")
        return redirect('display_loan_disbursements')

    try:
        deletion_date = timezone.datetime.strptime(deletion_date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, f"Invalid date format: '{deletion_date_str}'. Please use YYYY-MM-DD.")
        return redirect('display_loan_disbursements')

    system_date = timezone.now().date()

    if deletion_date > system_date:
        messages.error(
            request,
            f"Deletion date ({deletion_date}) cannot be in the future relative to system date ({system_date})."
        )
        return redirect('display_loan_disbursements')

    try:
        loan = Loans.objects.get(id=id)
    except Loans.DoesNotExist:
        messages.error(request, f"Loan with ID {id} does not exist.")
        return redirect('display_loan_disbursements')

    memtrans_exists = Memtrans.objects.filter(trx_no=trx_no).exists()
    if not memtrans_exists:
        messages.error(request, f"No transactions found with trx_no '{trx_no}' to delete.")
        return redirect('display_loan_disbursements')

    try:
        with transaction.atomic():
            # Mark Memtrans records as history
            Memtrans.objects.filter(trx_no=trx_no).update(error='H')

            # Mark loan as reversed temporarily
            loan.disb_status = 'H'
            loan.save()

            # Delete LoanHist records if any
            LoanHist.objects.filter(trx_no=trx_no).delete()

            # Reset loan status
            loan.disb_status = ''
            loan.save()

        messages.success(
            request,
            f"Transactions with trx_no '{trx_no}' have been successfully deleted for loan ID {id} on {deletion_date}."
        )
        return redirect('display_loan_disbursements')

    except Exception as e:
        messages.error(request, f"An unexpected error occurred while deleting transactions: {str(e)}")
        return redirect('display_loan_disbursements')


from transactions.models import Memtrans
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Loans, LoanHist
from customers.models import Customer

def delete_transactions(request, customer_id):
    # Get the customer object
    customer = get_object_or_404(Customer, id=customer_id)

    # Delete transactions associated with the customer's gl_no or ac_no from Memtrans
    Memtrans.objects.filter(gl_no=customer.gl_no).delete()
    Memtrans.objects.filter(ac_no=customer.ac_no).delete()

    messages.success(request, 'Transactions deleted successfully!')
    return redirect('display_customers')






def display_loans(request):
    if request.method == "POST":
        id = request.POST.get('id')
        loan_entry = get_object_or_404(Loans, id=id)
        loan_entry.delete()
        messages.success(request, 'Loan entry deleted successfully!')
        return redirect('display_loans')  # Assuming 'display_loans' is the name of the URL pattern for this view

    loans = Loans.objects.all()
    return render(request, 'loans/display_loans.html', {'loans': loans})



# views.py
from django.shortcuts import render, get_object_or_404
from .models import Loans, LoanHist

def loan_repayment_reversal(request):
    loans = Loans.objects.filter(total_loan__gt=0)
    return render(request, 'loans/loan_repayment_reversal.html', {'loans': loans})

def loan_history(request, loan_id):
    loan = get_object_or_404(Loans, id=loan_id)
    loan_histories = LoanHist.objects.filter(gl_no=loan.gl_no, ac_no=loan.ac_no, cycle=loan.cycle, trx_type='LP')
    return render(request, 'loans/loan_history.html', {'loan': loan, 'loan_histories': loan_histories})


def delete_loan_history(request, loan_hist_id, loan_id):
    loan_hist = get_object_or_404(LoanHist, id=loan_hist_id)
    trx_no = loan_hist.trx_no
    loan_hist.delete()
    Memtrans.objects.filter(trx_no=trx_no).update(error='H')
    return redirect('loan_history', loan_id=loan_id)











# views.py
from datetime import timedelta, date, datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Max
from django.db import transaction
from django.contrib import messages
from .models import Loans, LoanHist
from transactions.models import Memtrans
from company.models import Company
from accounts_admin.models import Account

def calculate_due_date(disbursement_date, payment_freq, num_install):
    if disbursement_date is None:
        return None

    if payment_freq == 'monthly':
        due_date = disbursement_date + timedelta(days=num_install * 30)  # Approximation for monthly
    elif payment_freq == 'weekly':
        due_date = disbursement_date + timedelta(weeks=num_install)
    else:
        due_date = disbursement_date  # Default or unsupported payment frequency
    return due_date

def due_loans(request):
    gl_no = request.GET.get('gl_no', None)
    ac_no = request.GET.get('ac_no', None)
    cycle = request.GET.get('cycle', None)

    company = get_object_or_404(Company, id=request.user.branch_id)
    company_date_str = company.session_date.strftime('%Y-%m-%d') if company.session_date else date.today().strftime('%Y-%m-%d')
    company_date = datetime.strptime(company_date_str, '%Y-%m-%d').date()

    due_loans = Loans.objects.all()
    if gl_no:
        due_loans = due_loans.filter(gl_no=gl_no)
    if ac_no:
        due_loans = due_loans.filter(ac_no=ac_no)
    if cycle:
        due_loans = due_loans.filter(cycle=cycle)

    due_loans = [loan for loan in due_loans if calculate_due_date(loan.disbursement_date, loan.payment_freq, loan.num_install) <= company_date]

    loans_data = []
    for loan in due_loans:
        customer = loan.customer
        disbursement_date = loan.disbursement_date
        total_principal_between_dates = LoanHist.objects.filter(
            gl_no=loan.gl_no,
            ac_no=loan.ac_no,
            cycle=loan.cycle,
            trx_date__gte=disbursement_date,
            trx_date__lte=company_date
        ).aggregate(total_principal=Sum('principal'))['total_principal'] or 0

        total_interest_between_dates = LoanHist.objects.filter(
            gl_no=loan.gl_no,
            ac_no=loan.ac_no,
            cycle=loan.cycle,
            trx_date__gte=disbursement_date,
            trx_date__lte=company_date
        ).aggregate(total_interest=Sum('interest'))['total_interest'] or 0

        last_lp_date = LoanHist.objects.filter(
            gl_no=loan.gl_no,
            ac_no=loan.ac_no,
            cycle=loan.cycle,
            trx_type='LP'
        ).aggregate(Max('trx_date'))['trx_date__max']

        customer_balance = Memtrans.objects.filter(
            gl_no=loan.cust_gl_no,
            ac_no=customer.ac_no,
            error='A'
        ).aggregate(total_amount=Sum('amount'))['total_amount'] or 0

        if total_principal_between_dates > 0:
            loans_data.append({
                'loan': loan,
                'due_date': calculate_due_date(loan.disbursement_date, loan.payment_freq, loan.num_install),
                'total_principal_between_dates': total_principal_between_dates,
                'total_interest_between_dates': total_interest_between_dates,
                'last_lp_date': last_lp_date,
                'loan_amount': loan.loan_amount,
                'cycle': loan.cycle,
                'customer_gl_no': customer.gl_no,
                'customer_phone': customer.phone_no,
                'loan_cust_gl_no': loan.cust_gl_no,
                'customer_ac_no': customer.ac_no,
                'customer_balance': customer_balance  # Add customer balance
            })

    return render(request, 'loans/due_loans.html', {
        'loans_data': loans_data,
        'company_date': company_date,
        'gl_no': gl_no,
        'ac_no': ac_no,
        'cycle': cycle,
    })

def process_repayments(request):
    if request.method == 'POST':
        company = get_object_or_404(Company, id=request.user.branch_id)
        company_date_str = company.session_date.strftime('%Y-%m-%d') if company.session_date else date.today().strftime('%Y-%m-%d')
        company_date = datetime.strptime(company_date_str, '%Y-%m-%d').date()

        loans_data = request.POST.getlist('loans_data')
        for loan_id in loans_data:
            loan = get_object_or_404(Loans, id=loan_id)
            account = get_object_or_404(Account, gl_no=loan.gl_no)
            customer = loan.customer

            principal = LoanHist.objects.filter(
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle,
                trx_date__gte=loan.disbursement_date,
                trx_date__lte=company_date
            ).aggregate(total_principal=Sum('principal'))['total_principal'] or 0

            interest = LoanHist.objects.filter(
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle,
                trx_date__gte=loan.disbursement_date,
                trx_date__lte=company_date
            ).aggregate(total_interest=Sum('interest'))['total_interest'] or 0

            gl_no_cashier = customer.gl_no  # Get gl_no from Customer model where it starts with '2'
            ac_no_cashier = customer.ac_no

            with transaction.atomic():
                unique_id = generate_loan_repayment_id()

                if account.int_to_recev_gl_dr and account.int_to_recev_ac_dr and account.unearned_int_inc_gl and account.unearned_int_inc_ac:
                    debit_transaction = Memtrans(
                        branch=loan.branch,
                        gl_no=loan.cust_gl_no,
                        ac_no=ac_no_cashier,
                        cycle=loan.cycle,
                        amount=-principal,
                        description='Loan Repayment - Debit',
                        type='C',
                        ses_date=company_date,
                        trx_no=unique_id
                    )
                    debit_transaction.save()

                    credit_transaction = Memtrans(
                        branch=loan.branch,
                        gl_no=loan.gl_no,
                        ac_no=loan.ac_no,
                        cycle=loan.cycle,
                        amount=principal,
                        description=f'{customer.first_name}, {customer.last_name}, {customer.gl_no}-{customer.ac_no}',
                        error='A',
                        type='D',
                        ses_date=company_date,
                        trx_no=unique_id
                    )
                    credit_transaction.save()

                    debit_transaction_interest = Memtrans(
                        branch=loan.branch,
                        gl_no=loan.cust_gl_no,
                        ac_no=ac_no_cashier,
                        cycle=loan.cycle,
                        amount=-interest,
                        description='Loan Interest - Debit',
                        type='C',
                        ses_date=company_date,
                        trx_no=unique_id
                    )
                    debit_transaction_interest.save()

                    credit_transaction_interest = Memtrans(
                        branch=loan.branch,
                        gl_no=account.interest_gl,
                        ac_no=account.interest_ac,
                        cycle=loan.cycle,
                        amount=interest,
                        description=f'{customer.first_name}, {customer.last_name}, {loan.gl_no}-{loan.ac_no}',
                        error='A',
                        type='D',
                        ses_date=company_date,
                        trx_no=unique_id
                    )
                    credit_transaction_interest.save()

                    lp_count = LoanHist.objects.filter(
                        gl_no=loan.gl_no,
                        ac_no=loan.ac_no,
                        cycle=loan.cycle,
                        trx_type='LP'
                    ).count()
                    period = lp_count + 1

                    loanhist_entry = LoanHist(
                        branch=loan.branch,
                        gl_no=loan.gl_no,
                        ac_no=loan.ac_no,
                        cycle=loan.cycle,
                        trx_date=credit_transaction.ses_date,
                        period=str(period),
                        trx_type='LP',
                        principal=-principal,
                        interest=-interest,
                        penalty=0,
                        trx_no=unique_id
                    )
                    loanhist_entry.save()

                    loan.total_loan = principal + interest
                    loan.total_interest = interest
                    loan.save()

        messages.success(request, 'All due loans have been processed for repayment.')
        return redirect('due_loans')
    return redirect('due_loans')



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def eop_loans(request):
    return render(request, 'loans/eop_loans.html')






@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_to_apply_simple_loan(request):
    data = Memtrans.objects.all().order_by('-id').first()
    customers = Customer.objects.filter(label='L').order_by('-id')
    total_amounts = []
    for customer in customers:
        # Calculate the total amount for each customer
        total_amount = Memtrans.objects.filter(gl_no=customer.gl_no, ac_no=customer.ac_no, error='A').aggregate(total_amount=Sum('amount'))['total_amount']
        total_amounts.append({
            'customer': customer,
            'total_amount': total_amount or 0.0,
        })
    return render(request, 'loans/choose_to_apply_simple_loan.html',{'customers':customers,'total_amounts':total_amounts,'data':data})


# loan application
@login_required(login_url='login')
@user_passes_test(check_role_admin)


def loan_application_and_approval(request, id):
    customer = get_object_or_404(Customer, id=id)
    loan_account = Account.objects.filter(gl_no__startswith='104').exclude(gl_no='10400').exclude(gl_no='104100').exclude(gl_no='104200')
    initial_values = {'gl_no_cust': customer.gl_no, 'ac_no_cust': customer.ac_no}
    user = User.objects.get(id=request.user.id)
    branch_id = user.branch_id
    company = get_object_or_404(Company, id=branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    
    if company.session_status == 'Closed':
        return HttpResponse("You can not post any transaction. Session is closed.")
    else:
        if request.method == 'POST':
            form = LoansForm(request.POST, request.FILES)
            if form.is_valid():
                gl_no = form.cleaned_data['gl_no']
                ac_no = form.cleaned_data['ac_no']

                with transaction.atomic():
                    # Check if there is an existing loan with the same 'gl_no' and 'ac_no'
                    existing_loan = Loans.objects.filter(gl_no=gl_no, ac_no=ac_no).last()

                    if existing_loan:
                        # If an existing loan is found, create a new loan with an incremented cycle
                        new_loan = Loans(
                            branch=form.cleaned_data.get('branch', 0),
                            appli_date=form.cleaned_data.get('appli_date', 0),
                            loan_amount=form.cleaned_data.get('loan_amount', 0),
                            interest_rate=form.cleaned_data.get('interest_rate', 0),
                            payment_freq=form.cleaned_data.get('payment_freq', 0),
                            interest_calculation_method=form.cleaned_data.get('interest_calculation_method', 0),
                            loan_officer=form.cleaned_data.get('loan_officer', 0),
                            business_sector=form.cleaned_data.get('business_sector', 0),
                            customer=customer,
                            gl_no=gl_no,
                            ac_no=ac_no,
                            approval_status='T',
                            approval_date=form.cleaned_data.get('appli_date', 0),
                            num_install=form.cleaned_data.get('num_install', 0),
                            cycle=existing_loan.cycle + 1 if existing_loan.cycle is not None else 1,
                            # ... other fields ...
                        )
                    else:
                        # If no existing loan is found, create a new loan with cycle 1
                        new_loan = Loans(
                            branch=form.cleaned_data.get('branch', 0),
                            appli_date=form.cleaned_data.get('appli_date', 0),
                            loan_amount=form.cleaned_data.get('loan_amount', 0),
                            interest_rate=form.cleaned_data.get('interest_rate', 0),
                            payment_freq=form.cleaned_data.get('payment_freq', 0),
                            interest_calculation_method=form.cleaned_data.get('interest_calculation_method', 0),
                            loan_officer=form.cleaned_data.get('loan_officer', 0),
                            business_sector=form.cleaned_data.get('business_sector', 0),
                            customer=customer,
                            gl_no=gl_no,
                            ac_no=ac_no,
                            approval_status='T',
                            approval_date=form.cleaned_data.get('appli_date', 0),
                            num_install=form.cleaned_data.get('num_install', 0),
                            cycle=1,
                            # ... other fields ...
                        )

                    new_loan.save()
                    customer.loan = 'T'
                    customer.save()
                    print("Customer:", customer)  # Print the customer object for debugging

                    messages.success(request, 'Loan Applied successfully!')
                    return redirect('choose_to_apply_simple_loan')
            else:
                messages.error(request, 'Form is not valid. Please check the entered data.')
        else:
            form = LoansForm(initial=initial_values)

    return render(request, 'loans/loan_application_and_approval.html', {'form': form, 'customer': customer, 'loan_account': loan_account, 'company': company, 'company_date': company_date})




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_simple_disburse(request):
    customers = Loans.objects.select_related('customer').filter(approval_status='T',disb_status='F')
    for customer in customers:
        if customer.customer:
            print(customer.customer.first_name)
        else:
            print("No associated customer for this loan.")
    # Pass the customers data to the template
    return render(request, 'loans/choose_simple_disburse.html', {'customers': customers})




def simple_loan_disbursement(request, id):
    loan = get_object_or_404(Loans, id=id)
    account = get_object_or_404(Account, gl_no=loan.gl_no)
    customer = loan.customer  # Assuming loan.customer is a ForeignKey to Customer model
    
    cust_data = Account.objects.filter(gl_no__startswith='20').exclude(gl_no__in=['20100', '20200', '20000'])
    gl_no = Account.objects.filter(gl_no__startswith='200').values_list('gl_no', flat=True)
    ac_no_list = Memtrans.objects.filter(ac_no=loan.ac_no).values_list('ac_no', flat=True).distinct()
    cust_branch = Company.objects.all()
    amounts = Memtrans.objects.filter(ac_no=loan.ac_no, gl_no__startswith='2').values('gl_no').annotate(total_amount=Sum('amount')).order_by('-total_amount')
    officer = Account_Officer.objects.all()
    
    user = request.user
    branch_id = user.branch_id
    company = get_object_or_404(Company, id=branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    
    if loan.appli_date:
        appli_date = loan.appli_date.strftime('%Y-%m-%d')
    else:
        appli_date = ''
    
    if loan.approval_date:
        approve_date = loan.approval_date.strftime('%Y-%m-%d')
    else:
        approve_date = ''
    
    if company.session_status == 'Closed':
        return HttpResponse("You cannot post any transaction. Session is closed.")
    else:
        if request.method == 'POST':
            form = MemtransForm(request.POST, request.FILES)
            if form.is_valid():
                ses_date = form.cleaned_data['ses_date']
                if ses_date > company.session_date:
                    messages.warning(request, 'Transaction date cannot be greater than the session date.')
                    return redirect('choose_to_disburse')
                
                customer_id = customer.id  # Assuming the customer ID is in the form data
                with transaction.atomic():
                    if account.int_to_recev_gl_dr and account.int_to_recev_ac_dr and account.unearned_int_inc_gl and account.unearned_int_inc_ac:
                        # Generate a unique transaction number
                        unique_trx_no = generate_loan_disbursement_id()

                        debit_transaction = Memtrans(
                            branch=loan.branch,
                            customer_id=customer_id,  # Use the customer ID from the form data
                            cycle=loan.cycle,
                            gl_no=loan.gl_no,
                            ac_no=loan.ac_no,
                            amount=-loan.loan_amount,
                            description='Loan Disbursement - Debit',
                            type='D',
                            ses_date=company_date,
                            trx_no=unique_trx_no
                        )
                        debit_transaction.save()

                        credit_transaction = Memtrans(
                            branch=form.cleaned_data['branch'],
                            customer_id=customer_id,  # Use the customer ID from the form data
                            cycle=loan.cycle,
                            gl_no=form.cleaned_data['gl_no_cashier'],
                            ac_no=form.cleaned_data['ac_no_cashier'],
                            amount=loan.loan_amount,
                            description=f'{customer.first_name}, {customer.last_name}, {customer.gl_no}-{customer.ac_no}',
                            error='A',
                            type='C',
                            ses_date=form.cleaned_data['ses_date'],
                            trx_no=unique_trx_no
                        )
                        credit_transaction.save()

                        # Calculate loan schedule
                        loan_schedule = loan.calculate_loan_schedule()
                        loan.disb_status = 'T'
                        loan.cust_gl_no = form.cleaned_data['gl_no_cashier']
                        loan.disbursement_date = form.cleaned_data['ses_date']
                        loan.save()

                        # Insert loan schedule into LoanHist
                        for payment in loan_schedule:
                            loanhist_entry = LoanHist(
                                branch=loan.branch,
                                gl_no=loan.gl_no,
                                ac_no=loan.ac_no,
                                cycle=loan.cycle,
                                period=payment['period'],
                                trx_date=payment['payment_date'],
                                trx_type='LD',
                                principal=payment['principal_payment'],
                                interest=payment['interest_payment'],
                                penalty=0,
                                trx_no=unique_trx_no
                            )
                            loanhist_entry.save()

                        # Sum the interest from LoanHist
                        total_interest = LoanHist.objects.filter(gl_no=loan.gl_no, ac_no=loan.ac_no, cycle=loan.cycle).aggregate(total_interest=Sum('interest'))['total_interest'] or 0

                        # Update loan balance in Loans model
                        loan.total_loan = loan.loan_amount + total_interest
                        loan.total_interest = total_interest
                        loan.save()

                        debit_transaction = Memtrans(
                            branch=loan.branch,
                            customer_id=customer_id,
                            gl_no=account.int_to_recev_gl_dr,
                            ac_no=account.int_to_recev_ac_dr,
                            amount=-loan.total_interest,
                            description=f'{customer.first_name}, {customer.last_name}, {customer.gl_no}-{customer.ac_no}, Disbursement',
                            type='L',
                            ses_date=timezone.now(),
                            trx_no=unique_trx_no
                        )
                        debit_transaction.save()

                        credit_transaction = Memtrans(
                            branch=form.cleaned_data['branch'],
                            customer_id=customer_id,
                            gl_no=account.unearned_int_inc_gl,
                            ac_no=account.unearned_int_inc_ac,
                            amount=loan.total_interest,
                            description=f'{customer.first_name}, {customer.last_name}, {customer.gl_no}-{customer.ac_no}, Interest on Loan - Credit',
                            type='L',
                            ses_date=timezone.now(),
                            trx_no=unique_trx_no
                        )
                        credit_transaction.save()

                        messages.success(request, 'Loan Disbursed successfully!')
                        return redirect('choose_to_disburse')
                    else:
                        messages.warning(request, 'Please define all required loan parameters before disbursement.')
                        return redirect('choose_to_disburse')
        else:
            initial_data = {'gl_no': loan.gl_no}
            form = LoansModifyForm(instance=loan, initial=initial_data)

    return render(request, 'loans/simple_loan_disbursement.html', {
        'form': form,
        'customers': customer,
        'loan': loan,
        'customer': loan,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'ac_no_list': ac_no_list,
        'amounts': amounts,
        'account': account,
        'company': company,
        'company_date': company_date,
        'appli_date': appli_date,
        'approve_date': approve_date,
    })










@login_required(login_url='login')
@user_passes_test(check_role_admin)
def auto_loan_due_schedule(request):
    """
    Auto-generated loan due and repayment schedule with batch processing
    Enhanced with days overdue calculation
    """
    from datetime import datetime, date
    from decimal import Decimal
    from django.db.models import Sum, Max, Q
    from django.contrib import messages
    from django.db import transaction
    
    # Get current user's branch and company
    user = request.user
    user_branch = user.branch
    company = get_object_or_404(Branch, id=user.branch_id)
    company_date = company.session_date
    
    if company.session_status == 'Closed':
        return HttpResponse("You cannot process transactions. Session is closed.")
    
    # Get all active loans that are disbursed
    active_loans = Loans.objects.filter(
        disb_status='T',  # Disbursed
        approval_status='T',  # Approved
        branch=user_branch
    ).select_related('customer', 'loan_officer', 'business_sector')
    
    loan_schedule_data = []
    
    for loan in active_loans:
        # Calculate outstanding amounts
        disbursement_date = loan.disbursement_date
        if not disbursement_date:
            continue
            
        # Get total principal and interest due up to session date
        total_principal_due = LoanHist.objects.filter(
            gl_no=loan.gl_no,
            ac_no=loan.ac_no,
            cycle=loan.cycle,
            trx_date__gte=disbursement_date,
            trx_date__lte=company_date,
            trx_type='LD'  # Loan disbursement schedule
        ).aggregate(total=Sum('principal'))['total'] or Decimal('0.00')
        
        total_interest_due = LoanHist.objects.filter(
            gl_no=loan.gl_no,
            ac_no=loan.ac_no,
            cycle=loan.cycle,
            trx_date__gte=disbursement_date,
            trx_date__lte=company_date,
            trx_type='LD'
        ).aggregate(total=Sum('interest'))['total'] or Decimal('0.00')
        
        # Get total payments made
        total_principal_paid = LoanHist.objects.filter(
            gl_no=loan.gl_no,
            ac_no=loan.ac_no,
            cycle=loan.cycle,
            trx_type='LP'  # Loan payment
        ).aggregate(total=Sum('principal'))['total'] or Decimal('0.00')
        
        total_interest_paid = LoanHist.objects.filter(
            gl_no=loan.gl_no,
            ac_no=loan.ac_no,
            cycle=loan.cycle,
            trx_type='LP'
        ).aggregate(total=Sum('interest'))['total'] or Decimal('0.00')
        
        # Calculate outstanding amounts
        outstanding_principal = abs(total_principal_due) - abs(total_principal_paid)
        outstanding_interest = abs(total_interest_due) - abs(total_interest_paid)
        
        # Get customer balance
        customer_balance = Memtrans.objects.filter(
            gl_no=loan.cust_gl_no,
            ac_no=loan.customer.ac_no,
            error='A'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Get next due date and calculate days overdue
        next_due_payment = LoanHist.objects.filter(
            gl_no=loan.gl_no,
            ac_no=loan.ac_no,
            cycle=loan.cycle,
            trx_date__gte=company_date,
            trx_type='LD'
        ).order_by('trx_date').first()
        
        # Calculate days overdue
        days_overdue = 0
        overdue_status = 'current'
        first_overdue_payment = LoanHist.objects.filter(
            gl_no=loan.gl_no,
            ac_no=loan.ac_no,
            cycle=loan.cycle,
            trx_date__lt=company_date,
            trx_type='LD'
        ).order_by('trx_date').first()
        
        if first_overdue_payment:
            # Check if there are any unpaid installments before today
            unpaid_installments = LoanHist.objects.filter(
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle,
                trx_date__lte=company_date,
                trx_type='LD'
            ).count()
            
            paid_installments = LoanHist.objects.filter(
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle,
                trx_type='LP'
            ).count()
            
            if unpaid_installments > paid_installments:
                # Find the earliest unpaid due date
                earliest_unpaid = LoanHist.objects.filter(
                    gl_no=loan.gl_no,
                    ac_no=loan.ac_no,
                    cycle=loan.cycle,
                    trx_date__lte=company_date,
                    trx_type='LD'
                ).order_by('trx_date')[paid_installments:paid_installments+1].first()
                
                if earliest_unpaid:
                    days_overdue = (company_date - earliest_unpaid.trx_date).days
                    if days_overdue > 0:
                        if days_overdue <= 30:
                            overdue_status = 'overdue_minor'  # 1-30 days
                        elif days_overdue <= 90:
                            overdue_status = 'overdue_moderate'  # 31-90 days
                        else:
                            overdue_status = 'overdue_severe'  # 90+ days
        
        # Only include loans with outstanding amounts
        if outstanding_principal > 0 or outstanding_interest > 0:
            loan_data = {
                'loan': loan,
                'customer': loan.customer,
                'outstanding_principal': outstanding_principal,
                'outstanding_interest': outstanding_interest,
                'total_outstanding': outstanding_principal + outstanding_interest,
                'customer_balance': customer_balance,
                'next_due_date': next_due_payment.trx_date if next_due_payment else None,
                'days_overdue': days_overdue,
                'overdue_status': overdue_status,
                'can_pay': customer_balance >= (outstanding_principal + outstanding_interest),
                'loan_officer': loan.loan_officer.user if loan.loan_officer else 'N/A',
                'business_sector': loan.business_sector.sector_name if loan.business_sector else 'N/A'
            }
            loan_schedule_data.append(loan_data)
    
    # Handle form submission for batch processing (same as before...)
    if request.method == 'POST':
        selected_loan_ids = request.POST.getlist('selected_loans')
        
        if not selected_loan_ids:
            messages.error(request, 'No loans selected for processing.')
            return redirect('auto_loan_due_schedule')
        
        processed_count = 0
        total_amount_processed = Decimal('0.00')
        errors = []
        
        with transaction.atomic():
            for loan_id in selected_loan_ids:
                try:
                    loan = Loans.objects.get(id=loan_id, branch=user_branch)
                    account = Account.objects.get(gl_no=loan.gl_no)
                    customer = loan.customer
                    
                    # Find the corresponding loan data
                    loan_info = next((item for item in loan_schedule_data if item['loan'].id == int(loan_id)), None)
                    if not loan_info:
                        continue
                    
                    outstanding_principal = loan_info['outstanding_principal']
                    outstanding_interest = loan_info['outstanding_interest']
                    
                    # Check if customer has sufficient balance
                    if loan_info['customer_balance'] < (outstanding_principal + outstanding_interest):
                        errors.append(f"Insufficient balance for {customer.first_name} {customer.last_name}")
                        continue
                    
                    # Generate unique transaction number
                    unique_id = generate_loan_repayment_id()
                    
                    # Process repayment transactions (same processing logic as before...)
                    if account.int_to_recev_gl_dr and account.int_to_recev_ac_dr and account.unearned_int_inc_gl and account.unearned_int_inc_ac:
                        
                        # Principal repayment transactions
                        if outstanding_principal > 0:
                            # Debit customer account (reduce customer balance)
                            Memtrans.objects.create(
                                branch=user_branch,
                                cust_branch=loan.branch,
                                customer=customer,
                                gl_no=loan.cust_gl_no,
                                ac_no=customer.ac_no,
                                cycle=loan.cycle,
                                amount=-outstanding_principal,
                                description=f'Auto Loan Repayment - Principal - {customer.first_name} {customer.last_name}',
                                type='D',
                                account_type='C',
                                ses_date=company_date,
                                app_date=company_date,
                                sys_date=timezone.now(),
                                trx_no=unique_id,
                                code='LP',
                                user=request.user,
                                error='A'
                            )
                            
                            # Credit loan account (reduce loan balance)
                            Memtrans.objects.create(
                                branch=user_branch,
                                cust_branch=loan.branch,
                                customer=customer,
                                gl_no=loan.gl_no,
                                ac_no=loan.ac_no,
                                cycle=loan.cycle,
                                amount=outstanding_principal,
                                description=f'Auto Principal Repayment - {customer.first_name} {customer.last_name}',
                                error='A',
                                type='C',
                                account_type='L',
                                ses_date=company_date,
                                app_date=company_date,
                                sys_date=timezone.now(),
                                trx_no=unique_id,
                                code='LP',
                                user=request.user
                            )
                        
                        # Interest repayment transactions (same as before...)
                        if outstanding_interest > 0:
                            # Debit customer account for interest
                            Memtrans.objects.create(
                                branch=user_branch,
                                cust_branch=loan.branch,
                                customer=customer,
                                gl_no=loan.cust_gl_no,
                                ac_no=customer.ac_no,
                                cycle=loan.cycle,
                                amount=-outstanding_interest,
                                description=f'Auto Loan Interest Payment - {customer.first_name} {customer.last_name}',
                                type='D',
                                account_type='C',
                                ses_date=company_date,
                                app_date=company_date,
                                sys_date=timezone.now(),
                                trx_no=unique_id,
                                code='LP',
                                user=request.user,
                                error='A'
                            )
                            
                            # Credit interest income account
                            Memtrans.objects.create(
                                branch=user_branch,
                                cust_branch=loan.branch,
                                customer=customer,
                                gl_no=account.interest_gl,
                                ac_no=account.interest_ac,
                                cycle=loan.cycle,
                                amount=outstanding_interest,
                                description=f'Auto Interest Income - {customer.first_name} {customer.last_name}',
                                error='A',
                                type='C',
                                account_type='I',
                                ses_date=company_date,
                                app_date=company_date,
                                sys_date=timezone.now(),
                                trx_no=unique_id,
                                code='LP',
                                user=request.user
                            )
                            
                            # Interest accounting entries (same as before...)
                            Memtrans.objects.create(
                                branch=user_branch,
                                cust_branch=loan.branch,
                                customer=customer,
                                gl_no=account.int_to_recev_gl_dr,
                                ac_no=account.int_to_recev_ac_dr,
                                cycle=loan.cycle,
                                amount=-outstanding_interest,
                                description=f'Auto Interest Receivable Adjustment - {customer.first_name} {customer.last_name}',
                                type='D',
                                account_type='I',
                                ses_date=company_date,
                                app_date=company_date,
                                sys_date=timezone.now(),
                                trx_no=unique_id,
                                code='LP',
                                user=request.user
                            )
                            
                            Memtrans.objects.create(
                                branch=user_branch,
                                cust_branch=loan.branch,
                                customer=customer,
                                gl_no=account.unearned_int_inc_gl,
                                ac_no=account.unearned_int_inc_ac,
                                cycle=loan.cycle,
                                amount=outstanding_interest,
                                description=f'Auto Unearned Interest Adjustment - {customer.first_name} {customer.last_name}',
                                type='C',
                                account_type='I',
                                ses_date=company_date,
                                app_date=company_date,
                                sys_date=timezone.now(),
                                trx_no=unique_id,
                                code='LP',
                                user=request.user
                            )
                        
                        # Create loan history entry
                        lp_count = LoanHist.objects.filter(
                            gl_no=loan.gl_no,
                            ac_no=loan.ac_no,
                            cycle=loan.cycle,
                            trx_type='LP'
                        ).count()
                        
                        LoanHist.objects.create(
                            branch=loan.branch,
                            gl_no=loan.gl_no,
                            ac_no=loan.ac_no,
                            cycle=loan.cycle,
                            period=str(lp_count + 1),
                            trx_date=company_date,
                            trx_type='LP',
                            trx_naration='Auto Loan Repayment',
                            principal=-outstanding_principal,
                            interest=-outstanding_interest,
                            penalty=Decimal('0.00'),
                            trx_no=unique_id
                        )
                        
                        # Update loan totals
                        total_interest = LoanHist.objects.filter(
                            gl_no=loan.gl_no,
                            ac_no=loan.ac_no,
                            cycle=loan.cycle
                        ).aggregate(total=Sum('interest'))['total'] or Decimal('0.00')
                        
                        total_principal = LoanHist.objects.filter(
                            gl_no=loan.gl_no,
                            ac_no=loan.ac_no,
                            cycle=loan.cycle
                        ).aggregate(total=Sum('principal'))['total'] or Decimal('0.00')
                        
                        loan.total_loan = total_principal + total_interest
                        loan.total_interest = total_interest
                        loan.save()
                        
                        processed_count += 1
                        total_amount_processed += outstanding_principal + outstanding_interest
                        
                except Exception as e:
                    errors.append(f"Error processing loan {loan_id}: {str(e)}")
                    continue
        
        # Show results
        if processed_count > 0:
            messages.success(
                request,
                f'Successfully processed {processed_count} loan(s). Total amount: ₦{total_amount_processed:,.2f}'
            )
        
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                messages.error(request, error)
            if len(errors) > 5:
                messages.error(request, f'... and {len(errors) - 5} more errors.')
        
        return redirect('auto_loan_due_schedule')
    
    # Enhanced context with overdue statistics
    overdue_loans = len([item for item in loan_schedule_data if item['days_overdue'] > 0])
    severe_overdue = len([item for item in loan_schedule_data if item['overdue_status'] == 'overdue_severe'])
    
    context = {
        'loan_schedule_data': loan_schedule_data,
        'company': company,
        'company_date': company_date,
        'total_loans': len(loan_schedule_data),
        'total_outstanding': sum(item['total_outstanding'] for item in loan_schedule_data),
        'payable_loans': len([item for item in loan_schedule_data if item['can_pay']]),
        'overdue_loans': overdue_loans,
        'severe_overdue_loans': severe_overdue,
    }
    
    return render(request, 'loans/auto_loan_due_schedule.html', context)