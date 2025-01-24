
import locale
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

# Create your views here.
from django.utils import timezone
from django.shortcuts import render, redirect
from accounts.models import User
from accounts.views import check_role_admin
from company.models import Company, Branch
from customers.forms import CustomerForm
from customers.models import Customer

from loans.models import Loans
from transactions.utils import generate_expense_id, generate_general_journal_id, generate_withdrawal_id, generate_deposit_id, generate_income_id
from .forms import MemtransForm, SeekAndUpdateForm
from .models import Memtrans
from django.contrib import messages
from django.db.models import Sum

from django.db import transaction
from django.contrib.auth.decorators import login_required, user_passes_test

from customers.sms_service import send_sms

@login_required(login_url='login')
@user_passes_test(check_role_admin)

def deposit(request, id):
    user_branch = request.user.branch
    customer = get_object_or_404(Customer, id=id)
    formatted_balance = '{:,.2f}'.format(customer.balance)
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()
    total_amount = None
    cashier_gl_value = request.user.cashier_gl
    customers = Customer.objects.get(gl_no=cashier_gl_value)
    user = User.objects.get(id=request.user.id)
    branch_id = user.branch_id
    company = get_object_or_404(Branch, id=branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    customer_branch = customer.branch
    
    # Retrieve the user's branch
    user_branch = user.branch

    # Retrieve the last transaction for the customer
    last_transaction = Memtrans.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        error='A'
    ).order_by('-id').first()

    initial_values = {
        'branch': user_branch,  # Set branch to the user's branch
        'gl_no_cashier': customers.gl_no,
        'ac_no_cashier': customers.ac_no,
        'gl_no_cust': customer.gl_no,
        'ac_no_cust': customer.ac_no,
    }

    sum_of_amount_cash = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cashier'],
        ac_no=initial_values['ac_no_cashier'],
        error='A',
        branch=user_branch  # Filter by the logged-in user's branch
    ).aggregate(total_amount1=Sum('amount'))['total_amount1']

    sum_of_amount_cust = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cust'],
        ac_no=initial_values['ac_no_cust'],
        error='A'
    ).aggregate(total_amount2=Sum('amount'))['total_amount2']

    sum_of_amounts = None

    if company.session_status == 'Closed':
        messages.success(request, 'Session Closed!')
        return HttpResponse("You cannot post any transaction. Session is closed.")
    else:
        if request.method == 'POST':
            form = MemtransForm(request.POST)
            if form.is_valid():
                form.cleaned_data['branch'] = user_branch  # Ensure the branch is set to the user's branch
                
                branch_customer = form.cleaned_data['branch']
                gl_no_customer = form.cleaned_data['gl_no']
                ac_no_customer = form.cleaned_data['ac_no']
                amount = form.cleaned_data['amount']
                description = form.cleaned_data['description']
                app_date = form.cleaned_data['app_date']

                # Validate if app_date is greater than company_date
                if app_date and company.session_date and app_date > company.session_date:
                    form.add_error('app_date', 'Application date cannot be greater than the company session date.')
                else:
                    with transaction.atomic():
                        customer_transaction = Memtrans(
                            branch=branch_customer,
                            cust_branch=customer_branch,
                            gl_no=gl_no_customer,
                            ac_no=ac_no_customer,
                            amount=amount,
                            description=description,
                            error='A',
                            account_type=customer.label,
                            type='C',
                            ses_date=form.cleaned_data['ses_date'],
                            app_date=form.cleaned_data['app_date'],
                            sys_date=timezone.now(),
                            customer=customer,
                            code='DP',
                            user=request.user
                        )
                        customer_transaction.save()

                        unique_id = generate_deposit_id()
                        customer_transaction.trx_no = unique_id
                        customer_transaction.save()

                        branch_cashier = form.cleaned_data['branch']
                        gl_no_cashier = form.cleaned_data['gl_no_cashier']
                        ac_no_cashier = form.cleaned_data['ac_no_cashier']
                        
                        user = request.user
                        customer_with_gl = get_object_or_404(Customer, gl_no=user.cashier_gl)
                        
                        cashier_transaction = Memtrans(
                            branch=branch_cashier,
                            cust_branch=user_branch,
                            gl_no=gl_no_cashier,
                            ac_no=ac_no_cashier,
                            amount=-amount,
                            description=f'{customer.first_name}, {customer.last_name}, {customer.gl_no}-{customer.ac_no}',
                            account_type=customers.label,
                            type='D',
                            ses_date=form.cleaned_data['ses_date'],
                            app_date=form.cleaned_data['app_date'],
                            sys_date=timezone.now(),
                            customer=customer_with_gl,
                            code='DP',
                            user=request.user
                        )
                        cashier_transaction.trx_no = customer_transaction.trx_no
                        cashier_transaction.save()

                        sum_of_amounts = Memtrans.objects.filter(
                            gl_no=gl_no_customer,
                            ac_no=ac_no_customer,
                            error='A'
                        ).aggregate(total_amount=Sum('amount'))['total_amount']

                        if sum_of_amounts is not None:
                            customer_to_update = Customer.objects.get(gl_no=gl_no_customer, ac_no=ac_no_customer)
                            customer_to_update.balance = sum_of_amounts
                            customer_to_update.save()

                        sum_of_amounts = Memtrans.objects.filter(
                            gl_no=gl_no_cashier,
                            ac_no=ac_no_cashier,
                            error='A'
                        ).aggregate(total_amount=Sum('amount'))['total_amount']

                        if sum_of_amounts is not None:
                            customer_to_update = Customer.objects.get(gl_no=gl_no_cashier, ac_no=ac_no_cashier)
                            customer_to_update.balance = sum_of_amounts
                            customer_to_update.save()

                        # Send SMS if the 'sms' field is True
                        if customer.sms:
                            sms_message = f"Dear {customer.first_name}, your deposit of {amount} has been successful. Your new balance is {customer.balance}."
                            send_sms(customer.phone_no, sms_message)

                        messages.success(request, 'Account saved successfully!')
                        return redirect('deposit', id=id)
        else:
            form = MemtransForm(initial=initial_values)
            form.fields['branch'].disabled = True  # Disable the branch field to prevent changes

        return render(request, 'transactions/cash_trans/deposit.html', {
            'form': form,
            'data': data,
            'customer': customer,
            'total_amount': total_amount,
            'formatted_balance': formatted_balance,
            'customers': customers,
            'sum_of_amount_cust': sum_of_amount_cust,
            'sum_of_amount_cash': sum_of_amount_cash,
            'company': company,
            'company_date': company_date,
            'last_transaction': last_transaction,  # Pass the last transaction to the template
        })
@login_required(login_url='login')
@user_passes_test(check_role_admin)

def withdraw(request, id):
    user_branch = request.user.branch

    # Retrieve the customer based on the provided ID
    customer = get_object_or_404(Customer, id=id)
    formatted_balance = '{:,.2f}'.format(customer.balance)
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()
    total_amount = None

    # Get cashier and company details
    cashier_gl_value = request.user.cashier_gl
    customers = Customer.objects.get(gl_no=cashier_gl_value)
    user = User.objects.get(id=request.user.id)
    branch_id = user.branch_id
    company = get_object_or_404(Branch, id=branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''

    customer_branch = customer.branch
    
    # Retrieve the user's branch
    user_branch = user.branch
    
    # Retrieve the last transaction for the customer
    last_transaction = Memtrans.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        error='A'
    ).order_by('-id').first()

    # Prepare initial form values
    initial_values = {
        'gl_no_cashier': customers.gl_no,
        'ac_no_cashier': customers.ac_no,
        'gl_no_cust': customer.gl_no,
        'ac_no_cust': customer.ac_no,
    }

    # Calculate total amounts for cashier and customer
    sum_of_amount_cash = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cashier'],
        ac_no=initial_values['ac_no_cashier'],
        error='A',
        branch=user_branch  # Filter by the logged-in user's branch
    ).aggregate(total_amount1=Sum('amount'))['total_amount1']

    sum_of_amount_cust = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cust'],
        ac_no=initial_values['ac_no_cust'],
        error='A'
    ).aggregate(total_amount2=Sum('amount'))['total_amount2']

    # Check if the session is closed
    if company.session_status == 'Closed':
        messages.success(request, 'Session Closed!')
        return HttpResponse("You cannot post any transaction. Session is closed.") 

    if request.method == 'POST':
        form = MemtransForm(request.POST)
        
        if form.is_valid():
            gl_no_customer = form.cleaned_data['gl_no']
            ac_no_customer = form.cleaned_data['ac_no']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            ses_date = form.cleaned_data['ses_date']
            app_date = form.cleaned_data['app_date']

            # Set branch to user's branch
            branch_customer = user_branch

            # Validate if app_date is greater than company_date
            if app_date and company.session_date and app_date > company.session_date:
                form.add_error('app_date', 'Application date cannot be greater than the company session date.')
            else:
                # Check if the customer has sufficient balance
                total_amount = Memtrans.objects.filter(
                    gl_no=gl_no_customer, 
                    ac_no=ac_no_customer,
                    error='A'
                ).aggregate(total_amount=Sum('amount'))['total_amount'] or 0

                if total_amount >= amount:
                    # Start a database transaction
                    with transaction.atomic():
                        # Create a transaction record in Memtrans
                        customer_transaction = Memtrans(
                            branch=branch_customer,
                            cust_branch=customer_branch,
                            gl_no=gl_no_customer,
                            ac_no=ac_no_customer,
                            ses_date=ses_date,
                            app_date=app_date,
                            sys_date=timezone.now(),
                            amount=-amount,
                            description=description,
                            error='A',
                            account_type=customer.label,
                            type='D',
                            customer=customer,
                            code='WD',
                            user=request.user
                        )
                        customer_transaction.save()

                        # Generate a unique ID for the transaction
                        unique_id = generate_withdrawal_id()
                        customer_transaction.trx_no = unique_id
                        customer_transaction.save()

                        # Update customer balance
                        customer_to_update = Customer.objects.get(gl_no=gl_no_customer, ac_no=ac_no_customer)
                        customer_to_update.balance -= amount
                        customer_to_update.save()

                        # Credit the cashier's account
                    
                        gl_no_cashier = form.cleaned_data['gl_no_cashier']
                        ac_no_cashier = form.cleaned_data['ac_no_cashier']

                        cashier_transaction = Memtrans(
                            branch=user_branch,
                            cust_branch=user_branch,
                            gl_no=gl_no_cashier,
                            ac_no=ac_no_cashier,
                            ses_date=ses_date,
                            app_date=app_date,
                            sys_date=timezone.now(),
                            amount=amount,
                            description=f'{customer.first_name}, {customer.last_name}, {customer.gl_no}-{customer.ac_no}',
                            error='A',
                            type='C',
                            account_type=customers.label,
                            customer=Customer.objects.get(gl_no=request.user.cashier_gl),
                            code='WD',
                            user=request.user
                        )
                        cashier_transaction.trx_no = customer_transaction.trx_no
                        cashier_transaction.save()

                        # Update the balances of the customer and cashier in the Customer table
                        sum_of_amounts = Memtrans.objects.filter(
                            gl_no=gl_no_customer, 
                            ac_no=ac_no_customer,
                            error='A'
                        ).aggregate(total_amount=Sum('amount'))['total_amount']

                        if sum_of_amounts is not None:
                            customer_to_update.balance = sum_of_amounts
                            customer_to_update.save()

                        sum_of_amounts = Memtrans.objects.filter(
                            gl_no=gl_no_cashier, 
                            ac_no=ac_no_cashier,
                            error='A'
                        ).aggregate(total_amount=Sum('amount'))['total_amount']

                        if sum_of_amounts is not None:
                            cashier_to_update = Customer.objects.get(gl_no=gl_no_cashier, ac_no=ac_no_cashier)
                            cashier_to_update.balance = sum_of_amounts
                            cashier_to_update.save()

                        messages.success(request, 'Withdrawal successful!')
                    return redirect('withdraw', id=id)
                else:
                    messages.warning(request, 'Insufficient Balance!')
                    return redirect('choose_withdrawal')
    else:
        form = MemtransForm()

    return render(request, 'transactions/cash_trans/withdraw.html', {
        'form': form,
        'data': data,
        'customer': customer,
        'total_amount': total_amount,
        'formatted_balance': formatted_balance,
        'customers': customers,
        'sum_of_amount_cash': sum_of_amount_cash,
        'sum_of_amount_cust': sum_of_amount_cust,
        'company': company,
        'company_date': company_date,
        'last_transaction': last_transaction,  # Pass the last transaction to the template
    })





@login_required(login_url='login')
@user_passes_test(check_role_admin)
def income(request, id):
    # Retrieve the user's branch

    user_branch = request.user.branch
    customer = get_object_or_404(Customer, id=id)
    formatted_balance = '{:,.2f}'.format(customer.balance)
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()
    total_amount = None
    cashier_gl_value = request.user.cashier_gl
    customers = Customer.objects.get(gl_no=cashier_gl_value)
    user = User.objects.get(id=request.user.id)
    branch_id = user.branch_id
    company = get_object_or_404(Branch, id=branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    customer_branch = customer.branch
    # Retrieve the user's branch
    user_branch = user.branch

    # Retrieve the last transaction for the customer
    last_transaction = Memtrans.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        error='A'
    ).order_by('-id').first()

    initial_values = {
        'branch': user_branch,  # Set branch to the user's branch
        'gl_no_cashier': customers.gl_no,
        'ac_no_cashier': customers.ac_no,
        'gl_no_cust': customer.gl_no,
        'ac_no_cust': customer.ac_no,
    }

    sum_of_amount_cash = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cashier'],
        ac_no=initial_values['ac_no_cashier'],
        error='A',
        branch=user_branch  # Filter by the logged-in user's branch
    ).aggregate(total_amount1=Sum('amount'))['total_amount1']

    sum_of_amount_cust = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cust'],
        ac_no=initial_values['ac_no_cust'],
        error='A'
    ).aggregate(total_amount2=Sum('amount'))['total_amount2']

    sum_of_amounts = None

    if company.session_status == 'Closed':
        messages.success(request, 'Session Closed!')
        return HttpResponse("You cannot post any transaction. Session is closed.")
    else:
        if request.method == 'POST':
            form = MemtransForm(request.POST)
            if form.is_valid():
                form.cleaned_data['branch'] = user_branch  # Ensure the branch is set to the user's branch
                
                branch_customer = form.cleaned_data['branch']
                gl_no_customer = form.cleaned_data['gl_no']
                ac_no_customer = form.cleaned_data['ac_no']
                amount = form.cleaned_data['amount']
                description = form.cleaned_data['description']
                app_date = form.cleaned_data['app_date']

                # Validate if app_date is greater than company_date
                if app_date and company.session_date and app_date > company.session_date:
                    form.add_error('app_date', 'Application date cannot be greater than the company session date.')
                else:
                    with transaction.atomic():
                        customer_transaction = Memtrans(
                            branch=branch_customer,
                            cust_branch=customer_branch,
                            gl_no=gl_no_customer,
                            ac_no=ac_no_customer,
                            amount=amount,
                            description=description,
                            error='A',
                            account_type=customer.label,
                            type='C',
                            ses_date=form.cleaned_data['ses_date'],
                            app_date=form.cleaned_data['app_date'],
                            sys_date=timezone.now(),
                            customer=customer,
                            code='DP',
                            user=request.user
                        )
                        customer_transaction.save()

                        unique_id = generate_deposit_id()
                        customer_transaction.trx_no = unique_id
                        customer_transaction.save()

                        branch_cashier = form.cleaned_data['branch']
                        gl_no_cashier = form.cleaned_data['gl_no_cashier']
                        ac_no_cashier = form.cleaned_data['ac_no_cashier']
                        
                        user = request.user
                        customer_with_gl = get_object_or_404(Customer, gl_no=user.cashier_gl)
                        
                        cashier_transaction = Memtrans(
                            branch=branch_cashier,
                            cust_branch=user_branch,
                            gl_no=gl_no_cashier,
                            ac_no=ac_no_cashier,
                            amount=-amount,
                            description=f'{customer.first_name}, {customer.last_name}, {customer.gl_no}-{customer.ac_no}',
                            account_type=customers.label,
                            type='D',
                            ses_date=form.cleaned_data['ses_date'],
                            app_date=form.cleaned_data['app_date'],
                            sys_date=timezone.now(),
                            customer=customer_with_gl,
                            code='DP',
                            user=request.user
                        )
                        cashier_transaction.trx_no = customer_transaction.trx_no
                        cashier_transaction.save()

                        sum_of_amounts = Memtrans.objects.filter(
                            gl_no=gl_no_customer,
                            ac_no=ac_no_customer,
                            error='A'
                        ).aggregate(total_amount=Sum('amount'))['total_amount']

                        if sum_of_amounts is not None:
                            customer_to_update = Customer.objects.get(gl_no=gl_no_customer, ac_no=ac_no_customer)
                            customer_to_update.balance = sum_of_amounts
                            customer_to_update.save()

                        sum_of_amounts = Memtrans.objects.filter(
                            gl_no=gl_no_cashier,
                            ac_no=ac_no_cashier,
                            error='A'
                        ).aggregate(total_amount=Sum('amount'))['total_amount']

                        if sum_of_amounts is not None:
                            customer_to_update = Customer.objects.get(gl_no=gl_no_cashier, ac_no=ac_no_cashier)
                            customer_to_update.balance = sum_of_amounts
                            customer_to_update.save()

                        # Send SMS if the 'sms' field is True
                        if customer.sms:
                            sms_message = f"Dear {customer.first_name}, your deposit of {amount} has been successful. Your new balance is {customer.balance}."
                            send_sms(customer.phone_no, sms_message)

                        messages.success(request, 'Account saved successfully!')
                        return redirect('income', id=id)
        else:
            form = MemtransForm(initial=initial_values)
            form.fields['branch'].disabled = True  # Disable the branch field to prevent changes

        return render(request, 'transactions/non_cash/income.html', {
            'form': form,
            'data': data,
            'customer': customer,
            'total_amount': total_amount,
            'formatted_balance': formatted_balance,
            'customers': customers,
            'sum_of_amount_cust': sum_of_amount_cust,
            'sum_of_amount_cash': sum_of_amount_cash,
            'company': company,
            'company_date': company_date,
            'last_transaction': last_transaction,  # Pass the last transaction to the template
        })

  



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def expense(request, id):
    user_branch = request.user.branch
    # Retrieve the customer based on the provided ID
    customer = get_object_or_404(Customer, id=id)
    formatted_balance = '{:,.2f}'.format(customer.balance)
    # data = Memtrans.objects.all().order_by('-id').first()
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()
    total_amount = None

    # Get cashier and company details
    cashier_gl_value = request.user.cashier_gl
    customers = Customer.objects.get(gl_no=cashier_gl_value)
    user = User.objects.get(id=request.user.id)
    branch_id = user.branch_id
    company = get_object_or_404(Branch, id=branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    customer_branch = customer.branch
    
    # Retrieve the user's branch
    user_branch = user.branch
    
    # Retrieve the last transaction for the customer
    last_transaction = Memtrans.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        error='A'
    ).order_by('-id').first()

    # Prepare initial form values
    initial_values = {
        'gl_no_cashier': customers.gl_no,
        'ac_no_cashier': customers.ac_no,
        'gl_no_cust': customer.gl_no,
        'ac_no_cust': customer.ac_no,
    }

    # Calculate total amounts for cashier and customer
    # sum_of_amount_cash = Memtrans.objects.filter(
    #     gl_no=initial_values['gl_no_cashier'],
    #     ac_no=initial_values['ac_no_cashier'],
    #     error='A'
    # ).aggregate(total_amount1=Sum('amount'))['total_amount1']

    sum_of_amount_cash = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cashier'],
        ac_no=initial_values['ac_no_cashier'],
        error='A',
        branch=user_branch  # Filter by the logged-in user's branch
    ).aggregate(total_amount1=Sum('amount'))['total_amount1']

    sum_of_amount_cust = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cust'],
        ac_no=initial_values['ac_no_cust'],
        error='A'
    ).aggregate(total_amount2=Sum('amount'))['total_amount2']

    # Check if the session is closed
    if company.session_status == 'Closed':
        messages.success(request, 'Session Closed!')
        return HttpResponse("You cannot post any transaction. Session is closed.") 
    else:
        if request.method == 'POST':
            form = MemtransForm(request.POST)
            
            if form.is_valid():
                branch_customer = form.cleaned_data['cust_branch']
                gl_no_customer = form.cleaned_data['gl_no']
                ac_no_customer = form.cleaned_data['ac_no']
                amount = form.cleaned_data['amount']
                description = form.cleaned_data['description']
                ses_date = form.cleaned_data['ses_date']
                app_date = form.cleaned_data['app_date']

                # Validate if app_date is greater than company_date
            if app_date and company.session_date and app_date > company.session_date:
                form.add_error('app_date', 'Application date cannot be greater than the company session date.')
            else:
                
                # Check if the customer has sufficient balance
                total_amount = Memtrans.objects.filter(
                    gl_no=gl_no_customer, 
                    ac_no=ac_no_customer,
                    error='A'
                ).aggregate(total_amount=Sum('amount'))['total_amount'] or 0

                if total_amount >= amount:
                    # Start a database transaction
                    with transaction.atomic():
                        # Create a transaction record in Memtrans
                        customer_transaction = Memtrans(
                            branch=branch_customer,
                            cust_branch=customer_branch,
                            gl_no=gl_no_customer,
                            ac_no=ac_no_customer,
                            ses_date=form.cleaned_data['ses_date'],
                            app_date=form.cleaned_data['app_date'],
                            sys_date=timezone.now(),
                            amount=-amount,
                            description=description,
                            error='A',
                            account_type=customer.label,
                            type='D',
                            customer=customer,
                            code='WD',
                            user=request.user
                        )
                        customer_transaction.save()

                        # Generate a unique ID for the transaction
                        unique_id = generate_withdrawal_id()
                        customer_transaction.trx_no = unique_id
                        customer_transaction.save()

                        # Update customer balance
                        customer_to_update = Customer.objects.get(gl_no=gl_no_customer, ac_no=ac_no_customer)
                        customer_to_update.balance -= amount
                        customer_to_update.save()

                        # Credit the cashier's account
                        gl_no_cashier = form.cleaned_data['gl_no_cashier']
                        ac_no_cashier = form.cleaned_data['ac_no_cashier']

                        cashier_transaction = Memtrans(
                            branch=user_branch,
                            cust_branch=user_branch,
                            gl_no=gl_no_cashier,
                            ac_no=ac_no_cashier,
                            ses_date=form.cleaned_data['ses_date'],
                            app_date=form.cleaned_data['app_date'],
                            sys_date=timezone.now(),
                            amount=amount,
                            description=f'{customer.first_name}, {customer.last_name}, {customer.gl_no}-{customer.ac_no}',
                            error='A',
                            type='C',
                            account_type=customers.label,
                            customer=Customer.objects.get(gl_no=request.user.cashier_gl),
                            code='WD',
                            user=request.user
                        )
                        cashier_transaction.trx_no = customer_transaction.trx_no
                        cashier_transaction.save()

                        # Update the balances of the customer and cashier in the Customer table
                        sum_of_amounts = Memtrans.objects.filter(
                            gl_no=gl_no_customer, 
                            ac_no=ac_no_customer,
                            error='A'
                        ).aggregate(total_amount=Sum('amount'))['total_amount']

                        if sum_of_amounts is not None:
                            customer_to_update.balance = sum_of_amounts
                            customer_to_update.save()

                        sum_of_amounts = Memtrans.objects.filter(
                            gl_no=gl_no_cashier, 
                            ac_no=ac_no_cashier,
                            error='A'
                        ).aggregate(total_amount=Sum('amount'))['total_amount']

                        if sum_of_amounts is not None:
                            cashier_to_update = Customer.objects.get(gl_no=gl_no_cashier, ac_no=ac_no_cashier)
                            cashier_to_update.balance = sum_of_amounts
                            cashier_to_update.save()

                        messages.success(request, 'Withdrawal successful!')
                    return redirect('withdraw', id=id)
                else:
                    messages.warning(request, 'Insufficient Balance!')
                    return redirect('choose_withdrawal')
        else:
            form = MemtransForm()

    return render(request, 'transactions/non_cash/expense.html', {
        'form': form,
        'data': data,
        'customer': customer,
        'total_amount': total_amount,
        'formatted_balance': formatted_balance,
        'customers': customers,
        'sum_of_amount_cash': sum_of_amount_cash,
        'sum_of_amount_cust': sum_of_amount_cust,
        'company': company,
        'company_date': company_date,
        'last_transaction': last_transaction,  # Pass the last transaction to the template
    })



  


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_deposit(request):
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
  
   return render(request, 'transactions/cash_trans/choose_deposit.html', {'data': data, 'total_amounts': total_amounts})



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_withdrawal(request):
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
  
   return render(request, 'transactions/cash_trans/choose_withdrawal.html', {'data': data, 'total_amounts': total_amounts})



@login_required(login_url='login')
@user_passes_test(check_role_admin)
@login_required
def choose_income(request):
    # Get the branch of the logged-in user
    user_branch = request.user.branch

    # Get the latest transaction
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()

    # Filter customers based on the user's branch
    customers = Customer.objects.filter(branch=user_branch).order_by('-id')

    total_amounts = []

    for customer in customers:
        # Calculate the total amount for each customer, filtering by GL number, account number, and error
        total_amount = Memtrans.objects.filter(
            branch=user_branch, 
            gl_no=customer.gl_no, 
            ac_no=customer.ac_no, 
            error='A'
        ).aggregate(total_amount=Sum('amount'))['total_amount']
        
        total_amounts.append({
            'customer': customer,
            'total_amount': total_amount or 0.0,  # Default to 0.0 if no transactions found
        })

    context = {
        'data': data,
        'total_amounts': total_amounts,
    }

    return render(request, 'transactions/non_cash/choose_income.html', context)

    



@login_required(login_url='login')
@user_passes_test(check_role_admin)

@login_required
def choose_expense(request):
    # Get the branch of the logged-in user
    user_branch = request.user.branch

    # Get the latest transaction for the user's branch
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()

    # Filter customers based on the user's branch
    customers = Customer.objects.filter(branch=user_branch).order_by('-id')

    total_amounts = []

    for customer in customers:
        # Calculate the total amount for each customer, filtering by GL number, account number, and error
        total_amount = Memtrans.objects.filter(
            branch=user_branch, 
            gl_no=customer.gl_no, 
            ac_no=customer.ac_no, 
            error='A'
        ).aggregate(total_amount=Sum('amount'))['total_amount']
        
        total_amounts.append({
            'customer': customer,
            'total_amount': total_amount or 0.0,  # Default to 0.0 if no transactions found
        })

    context = {
        'data': data,
        'total_amounts': total_amounts,
    }

    return render(request, 'transactions/non_cash/choose_expense.html', context)

   


@login_required(login_url='login')
@user_passes_test(check_role_admin)
@login_required
def choose_general_journal(request):
    # Get the branch of the logged-in user
    user_branch = request.user.branch

    # Get the latest transaction for the user's branch
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()

    # Filter customers based on the user's branch
    customers = Customer.objects.filter(branch=user_branch).order_by('-id')

    total_amounts = []

    for customer in customers:
        # Calculate the total amount for each customer, filtering by GL number, account number, and error
        total_amount = Memtrans.objects.filter(
            branch=user_branch,
            gl_no=customer.gl_no,
            ac_no=customer.ac_no,
            error='A'
        ).aggregate(total_amount=Sum('amount'))['total_amount']
        
        total_amounts.append({
            'customer': customer,
            'total_amount': total_amount or 0.0,  # Default to 0.0 if no transactions found
        })

    context = {
        'data': data,
        'total_amounts': total_amounts,
    }

    return render(request, 'transactions/non_cash/choose_general_journal.html', context)



def general_journal(request, id):
    user_branch = request.user.branch
    # Fetch the customer with the given ID and ensure it belongs to the user's branch
    customer = get_object_or_404(Customer, id=id, branch=user_branch)
    formatted_balance = '{:,.2f}'.format(customer.balance)
    data = Memtrans.objects.all().order_by('-id').first()  # Get the last transaction
    total_amount = None
    company = get_object_or_404(Branch, id=user_branch.id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    customers = Customer.objects.filter(branch=user_branch)  # Fetch all customers in the user's branch

    last_transaction = Memtrans.objects.filter(gl_no=customer.gl_no, ac_no=customer.ac_no).order_by('-id').first()
    customer_branch = customer.branch

    if company.session_status == 'Closed':
        messages.success(request, 'Session Closed!')
        return HttpResponse("You cannot post any transaction. The session is closed.")
    else:
        if request.method == 'POST':
            form = MemtransForm(request.POST)
            if form.is_valid():
                # Automatically use the user's branch for the transaction
                branch_customer = user_branch
                gl_no_customer = form.cleaned_data['gl_no']
                ac_no_customer = form.cleaned_data['ac_no']
                amount = form.cleaned_data['amount']
                description = form.cleaned_data['description']
                app_date = form.cleaned_data['app_date']

                # Validate if app_date is greater than company_date
                if app_date and company.session_date and app_date > company.session_date:
                    form.add_error('app_date', 'Application date cannot be greater than the company session date.')
                else:
                    with transaction.atomic():
                        customer_transaction = Memtrans(
                            branch=branch_customer,
                            cust_branch=customer_branch, # Set the user's branch
                            gl_no=gl_no_customer,
                            ac_no=ac_no_customer,
                            amount=-amount,
                            description=description,
                            ses_date=form.cleaned_data['ses_date'],
                            app_date=app_date,
                            sys_date=timezone.now(),
                            error='A',
                            type='D',
                            account_type=form.cleaned_data['label_select'],
                            code='GL',
                            user=request.user
                        )
                        customer_transaction.save()

                        unique_id = generate_general_journal_id()
                        customer_transaction.trx_no = unique_id
                        customer_transaction.save()

                        gl_no_cashier = form.cleaned_data['gl_no_cashier']
                        ac_no_cashier = form.cleaned_data['ac_no_cashier']
                        description = form.cleaned_data['description']

                        cashier_transaction = Memtrans(
                            branch=user_branch,
                            cust_branch=user_branch,  # Set the user's branch for the cashier transaction
                            gl_no=gl_no_cashier,
                            ac_no=ac_no_cashier,
                            amount=amount,
                            description=description,
                            ses_date=form.cleaned_data['ses_date'],
                            app_date=app_date,
                            sys_date=timezone.now(),
                            error='A',
                            type='C',
                            account_type=form.cleaned_data['label_there'],
                            code='GL',
                            user=request.user
                        )
                        cashier_transaction.trx_no = customer_transaction.trx_no
                        cashier_transaction.save()

                        # Update balances for customer and cashier
                        sum_of_amounts = Memtrans.objects.filter(gl_no=gl_no_customer, ac_no=ac_no_customer, error='A').aggregate(total_amount=Sum('amount'))['total_amount']
                        if sum_of_amounts is not None:
                            customer_to_update = Customer.objects.get(gl_no=gl_no_customer, ac_no=ac_no_customer)
                            customer_to_update.balance = sum_of_amounts
                            customer_to_update.save()

                        sum_of_amounts = Memtrans.objects.filter(gl_no=gl_no_cashier, ac_no=ac_no_cashier, error='A').aggregate(total_amount=Sum('amount'))['total_amount']
                        if sum_of_amounts is not None:
                            cashier_to_update = Customer.objects.get(gl_no=gl_no_cashier, ac_no=ac_no_cashier)
                            cashier_to_update.balance = sum_of_amounts
                            cashier_to_update.save()

                        messages.success(request, 'Account saved successfully!')
                        return redirect('general_journal', id=id)

            return render(request, 'transactions/non_cash/general_journal.html', {
                'form': form,
                'data': data,
                'customer': customer,
                'total_amount': total_amount,
                'customers': customers,
                'formatted_balance': formatted_balance,
                'company': company,
                'company_date': company_date,
                'last_transaction': last_transaction
            })

        else:
            form = MemtransForm()

    return render(request, 'transactions/non_cash/general_journal.html', {
        'form': form,
        'data': data,
        'customer': customer,
        'total_amount': total_amount,
        'formatted_balance': formatted_balance,
        'company': company,
        'company_date': company_date,
        'customers': customers,
        'last_transaction': last_transaction
    })



from django.http import JsonResponse
from customers.models import Customer

def get_customer_data(request):
    gl_no = request.GET.get('gl_no')
    ac_no = request.GET.get('ac_no')

    try:
        customer = Customer.objects.get(gl_no=gl_no, ac_no=ac_no)
        data = {
            'success': True,
            'customer': {
                'name': f"{customer.first_name} {customer.middle_name} {customer.last_name}",
                'available_balance': customer.available_balance,
                'total_balance': customer.total_balance,
            }
        }
    except Customer.DoesNotExist:
        data = {'success': False}

    return JsonResponse(data)



@login_required(login_url='login')
@user_passes_test(check_role_admin)


def seek_and_update(request):
    form = SeekAndUpdateForm()
    updated_records = None

    if request.method == 'POST':
        form = SeekAndUpdateForm(request.POST)
        
        if form.is_valid():
            transaction_number = form.cleaned_data['trx_no']

            # Get the current system date
            system_date = timezone.now().date()

            # Retrieve the Memtrans record for the given transaction number
            transactions = Memtrans.objects.filter(trx_no=transaction_number)

            if not transactions.exists():
                messages.error(request, 'No transactions found with the given transaction number.')
                return render(request, 'transactions/non_cash/reverse_trans.html', {'form': form, 'updated_records': updated_records})

            # Fetch the branch from the first Memtrans record
            branch = transactions.first().branch  # Assuming the field is named 'branch' in Memtrans

            # Get the Company object with the matching branch
            company = get_object_or_404(Branch, branch_code=branch.branch_code)  # Ensure 'branch_code' is correct

            # Check if the company's system date is less than the current system date
            if company.system_date_date < system_date:
                messages.error(request, 'You cannot reverse this transaction because the branch has closed for this transaction.')
                return render(request, 'transactions/non_cash/reverse_trans.html', {'form': form, 'updated_records': updated_records})

            # Check which button was clicked
            action = request.POST.get('action', '')

            if action == 'search':
                # For search, simply return the transactions
                updated_records = transactions
            elif action == 'update':
                # Update the 'error' field for each retrieved transaction
                transactions.update(error='H')
                updated_records = transactions
                messages.success(request, f"All transactions with trx_no {transaction_number} updated successfully.")
            else:
                messages.error(request, 'Invalid action.')

    return render(request, 'transactions/non_cash/reverse_trans.html', {'form': form, 'updated_records': updated_records})


from django.shortcuts import render
from .models import Memtrans
from django.urls import reverse 


def memtrans_list(request):
    memtrans_list = Memtrans.objects.all()
    return render(request, 'transactions/non_cash/memtrans_list.html', {'memtrans_list': memtrans_list})

def delete_memtrans(request, memtrans_id):
    memtrans = get_object_or_404(Memtrans, pk=memtrans_id)
    trx_no = memtrans.trx_no
    Memtrans.objects.filter(trx_no=trx_no).delete()
    return redirect(reverse('memtrans_list'))



from django.shortcuts import render
# from loans.models import Loans
from django.urls import reverse 


def loan_list(request):
    loan_list = Loans.objects.all()
    return render(request, 'loans/loan_list.html', {'loan_list': loan_list})



def delete_loan(request, id):
    loan = get_object_or_404(Loans, pk=id)
    id = loan.id
    Loans.objects.filter(id=id).delete()
    return redirect(reverse('loans_list'))

# views.py

import pandas as pd
from django.shortcuts import render, redirect
from .forms import UploadFileForm
from .models import Memtrans, Customer
from .utils import generate_upload_excel  # Ensure you import your utility function

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            df = pd.read_excel(file)
            transactions = []
            for index, row in df.iterrows():
                customer = Customer.objects.filter(gl_no=row['gl_no'], ac_no=row['ac_no']).first()
                if customer:
                    customer_name = f"{customer.first_name} {customer.middle_name} {customer.last_name}"
                else:
                    customer_name = 'Unknown'
                transaction = Memtrans(
                    branch=row['branch'],
                    customer=customer,
                    loans=row.get('loans', ''),
                    cycle=row.get('cycle', 0),
                    gl_no=row['gl_no'],
                    ac_no=row['ac_no'],
                    trx_no=generate_upload_excel(),  # Automatically generated transaction ID
                    ses_date=row['ses_date'],
                    app_date=row.get('app_date'),                          
                    sys_date = timezone.now(),
                    amount=row['amount'],
                    description=row.get('description', ''),
                    error='A',  # Automatically set
                    type='D',   # Automatically set
                    user=request.user,
                    code='UP'
                )
                transactions.append({
                    'branch': transaction.branch,
                    'customer_name': customer_name,
                    'loans': transaction.loans,
                    'cycle': transaction.cycle,
                    'gl_no': transaction.gl_no,
                    'ac_no': transaction.ac_no,
                    'trx_no': transaction.trx_no,
                    'ses_date': transaction.ses_date.strftime('%Y-%m-%d'),
                    'app_date': transaction.app_date.strftime('%Y-%m-%d') if transaction.app_date else '',
                    'amount': str(transaction.amount),
                    'description': transaction.description,
                    'error': transaction.error,
                    'type': transaction.type,
                    'user': transaction.user.username,
                })
            request.session['transactions'] = transactions
            return redirect('preview_data')
    else:
        form = UploadFileForm()
    
    return render(request, 'transactions/upload_file.html', {'form': form})


def preview_data(request):
    if request.method == 'POST':
        transactions = request.session.get('transactions', [])

        # Fetch the latest Company instance (assuming there's only one)
        company = Company.objects.first()
        if not company:
            return render(request, 'transactions/preview_data.html', {
                'transactions': transactions,
                'error_message': 'No company record found.'
            })

        # Calculate the total amount with proper type conversion
        total_amount = 0
        valid_transactions = []
        invalid_transactions = []

        for transaction in transactions:
            try:
                amount = float(transaction.get('amount', 0))  # Convert to float
                total_amount += amount

                # Convert ses_date and app_date strings to date objects for comparison
                ses_date = pd.to_datetime(transaction['ses_date']).date()
                app_date = pd.to_datetime(transaction['app_date']).date() if transaction.get('app_date') else None

                # Validate ses_date and app_date against the company's session_date
                if ses_date <= company.session_date and (app_date is None or app_date <= company.session_date):
                    valid_transactions.append(transaction)
                else:
                    invalid_transactions.append(transaction)

            except ValueError:
                # Handle cases where amount is not a valid number
                print(f"Invalid amount found: {transaction.get('amount', 0)}")  # Debugging print statement

        print(f"Total amount: {total_amount}")  # Debugging print statement

        # If there are invalid transactions, show an error message with session_date included
        if invalid_transactions:
            error_message = (f"Some transactions have invalid ses_date or app_date later than the company's session date "
                             f"({company.session_date.strftime('%Y-%m-%d')}). Please correct these transactions and try again.")
            request.session['error_message'] = error_message
            return redirect('upload_file')  # Redirect back to the upload file page

        # Check if the total amount is exactly 0
        if total_amount != 0:
            # If total amount is not 0, do not save and show an error message
            return render(request, 'transactions/preview_data.html', {
                'transactions': valid_transactions,
                'error_message': 'Summation of amount must be exactly 0 to proceed with saving.'
            })

        # Check if trx_no is already in the session
        common_trx_no = request.session.get('common_trx_no')

        # If not, generate a new trx_no and store it in the session
        if not common_trx_no:
            common_trx_no = generate_upload_excel()
            request.session['common_trx_no'] = common_trx_no
            print(f"Generated trx_no: {common_trx_no}")  # Debugging print statement

        # Save valid transactions
        for transaction_data in valid_transactions:
            customer = Customer.objects.filter(gl_no=transaction_data['gl_no'], ac_no=transaction_data['ac_no']).first()
            Memtrans.objects.create(
                branch=request.user.branch,
                customer=customer,
                loans=transaction_data['loans'],
                cycle=transaction_data['cycle'],
                gl_no=transaction_data['gl_no'],
                ac_no=transaction_data['ac_no'],
                trx_no=common_trx_no,  # Use the same trx_no for all rows
                ses_date=transaction_data['ses_date'],
                app_date=transaction_data['app_date'] if transaction_data['app_date'] else None,                           
                sys_date=timezone.now(),
                amount=transaction_data['amount'],
                description=transaction_data['description'],
                error='A',
                type='B',
                user=request.user,
                code='UP'
            )

        # Clear the session after processing
        request.session.pop('transactions', None)
        request.session.pop('common_trx_no', None)  # Clear the trx_no after processing

        return redirect('upload_success')
    else:
        transactions = request.session.get('transactions', [])
        return render(request, 'transactions/preview_data.html', {'transactions': transactions})






# views.py
from django.shortcuts import render, redirect
from .models import InterestRate
from .forms import InterestRateForm
from .models import Memtrans, Customer, Loans
from django.db.models import Sum

def add_interest_rate(request):
    if request.method == 'POST':
        form = InterestRateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('success')  # Redirect to a success page
    else:
        form = InterestRateForm()
    
    return render(request, 'transactions/add_interest_rate.html', {'form': form})

def interest_rate_list(request):
    rates = InterestRate.objects.all()
    return render(request, 'transactions/interest_rate_list.html', {'rates': rates})



def edit_interest_rate(request, pk):
    rate = get_object_or_404(InterestRate, pk=pk)
    if request.method == 'POST':
        form = InterestRateForm(request.POST, instance=rate)
        if form.is_valid():
            form.save()
            return redirect('interest_rate_list')  # Redirect to the list page
    else:
        form = InterestRateForm(instance=rate)
    
    return render(request, 'transactions/edit_interest_rate.html', {'form': form})

def delete_interest_rate(request, pk):
    rate = get_object_or_404(InterestRate, pk=pk)
    if request.method == 'POST':
        rate.delete()
        return redirect('interest_rate_list')  # Redirect to the list page
    return render(request, 'transactions/delete_interest_rate.html', {'rate': rate})

def success(request):
    return render(request, 'transactions/success.html')


from django.shortcuts import render, redirect
from django.db.models import Sum
from .models import Memtrans, InterestRate
from transactions.utils import generate_int_cal
from datetime import datetime

def calculate_interest(request):
    results = []
    total_amount_sum = 0
    total_interest_sum = 0

    if request.method == 'POST':
        gl_no = request.POST.get('gl_no')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        ses_date = request.POST.get('ses_date')
        action = request.POST.get('action')

        try:
            interest_rate = InterestRate.objects.get(gl_no=gl_no)
        except InterestRate.DoesNotExist:
            return render(request, 'transactions/calculate_interest.html', {
                'error': 'GL Number not found'
            })

        transactions = Memtrans.objects.filter(
            gl_no=gl_no,
            ses_date__range=[start_date, end_date],
            error='A'  # Exclude transactions where error is 'H'
        )

        # Aggregate by gl_no and ac_no
        aggregated_data = transactions.values('gl_no', 'ac_no').annotate(
            total_amount=Sum('amount')
        )

        results = []
        for data in aggregated_data:
            total_amount = data['total_amount']
            total_interest = (total_amount * interest_rate.rate) / 100

            results.append({
                'gl_no': data['gl_no'],
                'ac_no': data['ac_no'],
                'total_amount': total_amount,
                'interest_rate': interest_rate.rate,
                'total_interest': total_interest
            })

            total_amount_sum += total_amount
            total_interest_sum += total_interest

        if action == 'save':
            for result in results:
                Memtrans.objects.create(
                    branch=request.user.branch,  # Adjust if needed
                    customer=None,  # Adjust if needed
                    loans=None,  # Adjust if needed
                    cycle=None,  # Adjust if needed
                    gl_no=result['gl_no'],
                    ac_no=result['ac_no'],
                    trx_no=generate_int_cal(),
                    ses_date=ses_date,  # Assuming today's date
                    app_date=datetime.now().date(),                           
                    sys_date = timezone.now(),
                    amount=result['total_interest'],  # Save total interest instead of total amount
                    description='Interest Calculation',
                    error='A',
                    type='N',
                    user=request.user,
                    code='IN'
                )
            return redirect('success')  # Redirect to the same page or another page after saving

    return render(request, 'transactions/calculate_interest.html', {
        'results': results,
        'total_amount_sum': total_amount_sum,
        'total_interest_sum': total_interest_sum
    })
