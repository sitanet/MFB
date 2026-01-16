
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

from accounts.utils import send_sms
from django.core.mail import send_mail

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.mail import EmailMessage




def send_email(to_email, subject, template_name, context):
    """
    Helper function to send emails using Django's EmailMessage and HTML templates.
    """
    from django.conf import settings

    # Render the HTML template
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)  # Strip HTML tags for the plain text version

    # Create the email
    email = EmailMessage(
        subject,
        html_message,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
    )
    email.content_subtype = "html"  # Set the content type to HTML
    email.send(fail_silently=False)



from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404

@login_required(login_url='login')
@user_passes_test(check_role_admin)

def deposit(request, uuid):
    # Get user and branch - FIXED: use get_branch() method
    user = request.user
    user_branch = user.get_branch()  # ✅ This gets the Branch instance
    
    # ✅ Add error handling for missing branch
    if not user_branch:
        messages.error(request, 'No valid branch assigned to user')
        return HttpResponse("No valid branch assigned to user", status=400)
    
    customer = get_object_or_404(Customer.all_objects, uuid=uuid)
    formatted_balance = '{:,.2f}'.format(customer.balance)
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()

    # Get cashier customer - ensure this returns a Customer instance
    cashier_gl_value = request.user.cashier_gl
    cashier_customer = Customer.all_objects.filter(gl_no=cashier_gl_value).first()
    
    # Get company info - this line was already correct
    company = get_object_or_404(Branch, id=user.branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    customer_branch = customer.branch  # This should be a Branch instance

    # Initial form values - all using model instances
    initial_values = {
        'branch': user_branch,  # Branch instance
        'gl_no_cashier': cashier_customer.gl_no,
        'ac_no_cashier': cashier_customer.ac_no,
        'gl_no_cust': customer.gl_no,
        'ac_no_cust': customer.ac_no,
    }

    # Balance calculations - using Branch instance in filters
    sum_of_amount_cash = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cashier'],
        ac_no=initial_values['ac_no_cashier'],
        error='A',
        branch=user_branch  # Using Branch instance
    ).aggregate(total_amount1=Sum('amount'))['total_amount1'] or 0

    sum_of_amount_cust = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cust'],
        ac_no=initial_values['ac_no_cust'],
        error='A',
       
    ).aggregate(total_amount2=Sum('amount'))['total_amount2'] or 0

    if company.session_status == 'Closed':
        messages.success(request, 'Session Closed!')
        return HttpResponse("You cannot post any transaction. Session is closed.")

    if request.method == 'POST':
        form = MemtransForm(request.POST)
        if form.is_valid():
            try:
                # Ensure we're using Branch instances, not codes
                form.cleaned_data['branch'] = user_branch  # Branch instance
                
                amount = form.cleaned_data['amount']
                description = form.cleaned_data['description']
                app_date = form.cleaned_data['app_date']

                # Date validation
                if app_date and company.session_date and app_date > company.session_date:
                    form.add_error('app_date', 'Application date cannot be greater than the company session date.')
                else:
                    with transaction.atomic():
                        # Customer transaction - using Branch instances
                        customer_transaction = Memtrans(
                            branch=user_branch,  # Branch instance
                            cust_branch=customer_branch,  # Branch instance
                            gl_no=form.cleaned_data['gl_no'],
                            ac_no=form.cleaned_data['ac_no'],
                            amount=amount,
                            description=description,
                            error='A',
                            account_type=customer.label,
                            type='C',
                            ses_date=form.cleaned_data['ses_date'],
                            app_date=app_date,
                            sys_date=timezone.now(),
                            customer=customer,
                            code='DP',
                            user=request.user
                        )
                        customer_transaction.save()

                        unique_id = generate_deposit_id()
                        customer_transaction.trx_no = unique_id
                        customer_transaction.save()

                        # Cashier transaction - using Branch instances
                        cashier_transaction = Memtrans(
                            branch=user_branch,  # Branch instance
                            cust_branch=user_branch,  # Branch instance
                            gl_no=form.cleaned_data['gl_no_cashier'],
                            ac_no=form.cleaned_data['ac_no_cashier'],
                            amount=-amount,
                            description=f'{customer.first_name}, {customer.last_name}, {customer.gl_no}-{customer.ac_no}',
                            account_type=cashier_customer.label,
                            type='D',
                            ses_date=form.cleaned_data['ses_date'],
                            app_date=app_date,
                            sys_date=timezone.now(),
                            customer=cashier_customer,
                            code='DP',
                            user=request.user,
                            trx_no=unique_id
                        )
                        cashier_transaction.save()

                        # Update balances - using Branch instances in filters
                        sum_of_amounts = Memtrans.objects.filter(
                            gl_no=customer.gl_no,
                            ac_no=customer.ac_no,
                            error='A',
                            branch=user_branch  # Branch instance
                        ).aggregate(total_amount=Sum('amount'))['total_amount'] or 0

                        Customer.objects.filter(
                            gl_no=customer.gl_no,
                            ac_no=customer.ac_no
                        ).update(balance=sum_of_amounts)

                        sum_of_amounts = Memtrans.objects.filter(
                            gl_no=cashier_customer.gl_no,
                            ac_no=cashier_customer.ac_no,
                            error='A',
                            branch=user_branch  # Branch instance
                        ).aggregate(total_amount=Sum('amount'))['total_amount'] or 0

                        Customer.objects.filter(
                            gl_no=cashier_customer.gl_no,
                            ac_no=cashier_customer.ac_no
                        ).update(balance=sum_of_amounts)

                        # Send SMS notification
                        if customer.sms:
                            current_balance = Customer.objects.get(
                                gl_no=customer.gl_no,
                                ac_no=customer.ac_no
                            ).balance
                            sms_message = f"Dear {customer.first_name}, Credit of {amount} with A/C XXXXX{customer.ac_no} has been successful. Bal:NGN{current_balance}."
                            send_sms(customer.phone_no, sms_message)
                        
                        # Send email notification if email_alert is True and email exists
                        if customer.email_alert and customer.email:
                            current_balance = Customer.objects.get(
                                gl_no=customer.gl_no,
                                ac_no=customer.ac_no
                            ).balance
                            
                            email_context = {
                                'customer_name': customer.first_name,
                                'amount': amount,
                                'new_balance': current_balance,
                                'transaction_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'transaction_id': unique_id,
                                'description': description,
                            }
                            
                            try:
                                send_email(
                                    to_email=customer.email,
                                    subject=f"Deposit Confirmation - Transaction #{unique_id}",
                                    template_name='transactions/emails/deposit_email.html',  # You'll need to create this template
                                    context=email_context
                                )
                            except Exception as e:
                                # Log the email error but don't fail the transaction
                                print(f"Failed to send email notification: {str(e)}")

                        messages.success(request, 'Deposit successful!')
                        return redirect('deposit', uuid=uuid)
            except Exception as e:
                messages.error(request, f'Error processing deposit: {str(e)}')
                return redirect('deposit', uuid=uuid)
    else:
        form = MemtransForm(initial=initial_values)
        form.fields['branch'].disabled = True

    return render(request, 'transactions/cash_trans/deposit.html', {
        'form': form,
        'data': data,
        'customer': customer,
        'total_amount': sum_of_amount_cust,
        'formatted_balance': formatted_balance,
        'customers': cashier_customer,
        'sum_of_amount_cash': sum_of_amount_cash,
        'sum_of_amount_cust': sum_of_amount_cust,
        'company': company,
        'company_date': company_date,
        'last_transaction': Memtrans.objects.filter(
            gl_no=customer.gl_no,
            ac_no=customer.ac_no,
            error='A',
            branch=user_branch  # Branch instance
        ).order_by('-id').first(),
        'last_transactions': Memtrans.all_objects.filter(
            gl_no=customer.gl_no,
            ac_no=customer.ac_no,
            error='A'
        ).order_by('-sys_date')[:50],
        'cashier_transactions': Memtrans.all_objects.filter(
            gl_no=cashier_customer.gl_no if cashier_customer else None,
            ac_no=cashier_customer.ac_no if cashier_customer else None,
            error='A'
        ).order_by('-sys_date')[:50] if cashier_customer else [],
    })

    
     
@login_required(login_url='login')
@user_passes_test(check_role_admin)

def withdraw(request, uuid):
    # Get user and branch information
    user = request.user
    user_branch = user.branch
    customer = get_object_or_404(Customer.all_objects, uuid=uuid)
    formatted_balance = '{:,.2f}'.format(customer.balance)
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()

    # Get cashier information
    cashier_gl_value = user.cashier_gl
    cashier_customer = Customer.all_objects.filter(gl_no=cashier_gl_value).first()
    
    # Get company information
    company = get_object_or_404(Branch, id=user.branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    customer_branch = customer.branch
    
    # Retrieve the last transaction for the customer
    last_transaction = Memtrans.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        error='A'
    ).order_by('-id').first()

    # Initial form values
    initial_values = {
        'branch': user_branch,
        'gl_no_cashier': cashier_customer.gl_no,
        'ac_no_cashier': cashier_customer.ac_no,
        'gl_no_cust': customer.gl_no,
        'ac_no_cust': customer.ac_no,
    }

    # Compute balances
    sum_of_amount_cash = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cashier'],
        ac_no=initial_values['ac_no_cashier'],
        error='A',
        branch=user_branch
    ).aggregate(total_amount1=Sum('amount'))['total_amount1'] or 0

    sum_of_amount_cust = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cust'],
        ac_no=initial_values['ac_no_cust'],
        error='A',
    ).aggregate(total_amount2=Sum('amount'))['total_amount2'] or 0

    # Check session status
    if company.session_status == 'Closed':
        messages.success(request, 'Session Closed!')
        return HttpResponse("You cannot post any transaction. Session is closed.")

    if request.method == 'POST':
        form = MemtransForm(request.POST)
        if form.is_valid():
            form.cleaned_data['branch'] = user_branch
            
            amount = form.cleaned_data['amount']
            app_date = form.cleaned_data['app_date']

            # Validate application date
            if app_date and company.session_date and app_date > company.session_date:
                form.add_error('app_date', 'Application date cannot be greater than the company session date.')
            else:
                # Check sufficient balance
                if sum_of_amount_cust < amount:
                    messages.warning(request, 'Insufficient Balance!')
                    return redirect('choose_withdrawal')

                with transaction.atomic():
                    # Generate unique ID
                    unique_id = generate_withdrawal_id()

                    # Customer transaction (debit)
                    customer_transaction = Memtrans(
                        branch=user_branch,
                        cust_branch=customer_branch,
                        gl_no=customer.gl_no,
                        ac_no=customer.ac_no,
                        amount=-amount,
                        description=form.cleaned_data['description'],
                        error='A',
                        account_type=customer.label,
                        type='D',
                        ses_date=form.cleaned_data['ses_date'],
                        app_date=form.cleaned_data['app_date'],
                        sys_date=timezone.now(),
                        customer=customer,
                        code='WD',
                        user=user,
                        trx_no=unique_id
                    )
                    customer_transaction.save()

                    # Cashier transaction (credit)
                    cashier_transaction = Memtrans(
                        branch=user_branch,
                        cust_branch=user_branch,
                        gl_no=cashier_customer.gl_no,
                        ac_no=cashier_customer.ac_no,
                        amount=amount,
                        description=f'{customer.first_name}, {customer.last_name}, {customer.gl_no}-{customer.ac_no}',
                        error='A',
                        type='C',
                        account_type=cashier_customer.label,
                        customer=cashier_customer,
                        code='WD',
                        user=user,
                        trx_no=unique_id,
                        ses_date=form.cleaned_data['ses_date'],
                        app_date=form.cleaned_data['app_date'],
                        sys_date=timezone.now()
                    )
                    cashier_transaction.save()

                    # Update balances
                    sum_of_amounts = Memtrans.objects.filter(
                        gl_no=customer.gl_no,
                        ac_no=customer.ac_no,
                        error='A',
                        branch=user_branch
                    ).aggregate(total_amount=Sum('amount'))['total_amount']

                    if sum_of_amounts is not None:
                        customer_to_update = Customer.all_objects.get(
                            gl_no=customer.gl_no, 
                            ac_no=customer.ac_no
                        )
                        customer_to_update.balance = sum_of_amounts
                        customer_to_update.save()

                    sum_of_amounts = Memtrans.objects.filter(
                        gl_no=cashier_customer.gl_no,
                        ac_no=cashier_customer.ac_no,
                        error='A',
                        branch=user_branch
                    ).aggregate(total_amount=Sum('amount'))['total_amount']

                    if sum_of_amounts is not None:
                        cashier_to_update = Customer.all_objects.get(
                            gl_no=cashier_customer.gl_no,
                            ac_no=cashier_customer.ac_no
                        )
                        cashier_to_update.balance = sum_of_amounts
                        cashier_to_update.save()

                    # Send SMS if enabled
                    if customer.sms:
                        current_balance = Customer.all_objects.get(
                            gl_no=customer.gl_no,
                            ac_no=customer.ac_no
                        ).balance
                        sms_message = f"Dear {customer.first_name}, Debit of {amount} with A/C XXXXX{customer.ac_no} has been successful. Bal:NGN{current_balance}."
                        send_sms(customer.phone_no, sms_message)
                    
                    # Send email notification if email_alert is True and email exists
                    if customer.email_alert and customer.email:
                        current_balance = Customer.all_objects.get(
                            gl_no=customer.gl_no,
                            ac_no=customer.ac_no
                        ).balance
                        
                        email_context = {
                            'customer_name': customer.first_name,
                            'amount': amount,
                            'new_balance': current_balance,
                            'transaction_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'transaction_id': unique_id,
                            'description': form.cleaned_data['description'],
                            'transaction_type': 'Withdrawal',  # Added for email template
                        }
                        
                        try:
                            send_email(
                                to_email=customer.email,
                                subject=f"Withdrawal Confirmation - Transaction #{unique_id}",
                                template_name='transactions/emails/withdrawal_email.html',  # Separate template for withdrawals
                                context=email_context
                            )
                        except Exception as e:
                            # Log the email error but don't fail the transaction
                            print(f"Failed to send email notification: {str(e)}")

                    messages.success(request, 'Withdrawal successful!')
                    return redirect('withdraw', uuid=uuid)
    else:
        form = MemtransForm(initial=initial_values)
        form.fields['branch'].disabled = True

    return render(request, 'transactions/cash_trans/withdraw.html', {
        'form': form,
        'data': data,
        'customer': customer,
        'total_amount': sum_of_amount_cust,
        'formatted_balance': formatted_balance,
        'customers': cashier_customer,
        'sum_of_amount_cash': sum_of_amount_cash,
        'sum_of_amount_cust': sum_of_amount_cust,
        'company': company,
        'company_date': company_date,
        'last_transaction': last_transaction,
        'last_transactions': Memtrans.all_objects.filter(
            gl_no=customer.gl_no,
            ac_no=customer.ac_no,
            error='A'
        ).order_by('-sys_date')[:50],
        'cashier_transactions': Memtrans.all_objects.filter(
            gl_no=cashier_customer.gl_no if cashier_customer else None,
            ac_no=cashier_customer.ac_no if cashier_customer else None,
            error='A'
        ).order_by('-sys_date')[:50] if cashier_customer else [],
    })

@login_required(login_url='login')
@user_passes_test(check_role_admin)
# or generate_deposit_id() as appropriate



def income(request, uuid):
    # Retrieve the logged-in user's branch (Branch instance)
    user_branch = request.user.branch
    # Retrieve the customer based on the provided UUID
    customer = get_object_or_404(Customer.all_objects, uuid=uuid)
    formatted_balance = '{:,.2f}'.format(customer.balance)
    
    # Retrieve the latest transaction for the branch
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()
    total_amount = None

    # Get cashier and company details
    cashier_gl_value = request.user.cashier_gl
    # Use filter().first() to avoid MultipleObjectsReturned error
    customers = Customer.objects.filter(gl_no=cashier_gl_value).first()
    user = User.objects.get(id=request.user.id)
    branch_id = user.branch_id
    company = get_object_or_404(Branch, id=branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    customer_branch = customer.branch  # This is used for cust_branch (likely a ForeignKey)

    # Retrieve the last transaction for the customer
    last_transaction = Memtrans.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        error='A'
    ).order_by('-id').first()

    # Prepare initial form values
    initial_values = {
        'branch': user_branch.branch_code,  # Display value only
        'gl_no_cashier': customers.gl_no if customers else None,
        'ac_no_cashier': customers.ac_no if customers else None,
        'gl_no_cust': customer.gl_no,
        'ac_no_cust': customer.ac_no,
    }

    # Calculate total amounts for cashier and customer
    sum_of_amount_cash = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cashier'],
        ac_no=initial_values['ac_no_cashier'],
        error='A',
        branch=user_branch
    ).aggregate(total_amount1=Sum('amount'))['total_amount1'] or 0

    sum_of_amount_cust = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cust'],
        ac_no=initial_values['ac_no_cust'],
        error='A'
    ).aggregate(total_amount2=Sum('amount'))['total_amount2'] or 0

    # Check if the session is closed
    if company.session_status == 'Closed':
        messages.error(request, 'Session Closed!')
        return HttpResponse("You cannot post any transaction. Session is closed.")
    
    if request.method == 'POST':
        form = MemtransForm(request.POST)
        if form.is_valid():
            # Replace branch code with Branch instance before saving
            form.cleaned_data['branch'] = user_branch
            branch_customer = user_branch  # Use Branch instance
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
                # Start a database transaction
                with transaction.atomic():
                    # Create customer transaction (credit)
                    customer_transaction = Memtrans(
                        branch=user_branch,  # Branch instance
                        cust_branch=customer_branch,
                        gl_no=gl_no_customer,
                        ac_no=ac_no_customer,
                        ses_date=ses_date,
                        app_date=app_date,
                        sys_date=timezone.now(),
                        amount=amount,
                        description=description,
                        error='A',
                        account_type=customer.label,
                        type='C',  # Credit
                        customer=customer,
                        code='DP',
                        user=request.user
                    )
                    customer_transaction.save()

                    # Generate a unique ID for the transaction
                    unique_id = generate_income_id()
                    customer_transaction.trx_no = unique_id
                    customer_transaction.save()

                    # Create cashier transaction (debit)
                    customer_with_gl = Customer.all_objects.filter(gl_no=request.user.cashier_gl).first()
                    
                    cashier_transaction = Memtrans(
                        branch=user_branch,  # Branch instance
                        cust_branch=user_branch,
                        gl_no=initial_values['gl_no_cashier'],
                        ac_no=initial_values['ac_no_cashier'],
                        ses_date=ses_date,
                        app_date=app_date,
                        sys_date=timezone.now(),
                        amount=-amount,  # Debit is negative
                        description=f'{customer.first_name}, {customer.last_name}, {customer.gl_no}-{customer.ac_no}',
                        error='A',
                        type='D',  # Debit
                        account_type=customers.label if customers else None,
                        customer=customer_with_gl,
                        code='DP',
                        user=request.user
                    )
                    cashier_transaction.trx_no = customer_transaction.trx_no
                    cashier_transaction.save()

                    # Update customer balance
                    customer.balance = sum_of_amount_cust + amount
                    customer.save()

                    # Update cashier balance if exists
                    if customers:
                        customers.balance = sum_of_amount_cash - amount
                        customers.save()

                    messages.success(request, 'Transaction completed successfully!')
                    return redirect('income', uuid=uuid)
    else:
        form = MemtransForm(initial=initial_values)
        form.fields['branch'].disabled = True  # Disable the branch field to prevent changes

    context = {
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
        'last_transaction': last_transaction,
        'last_transactions': Memtrans.all_objects.filter(
            gl_no=customer.gl_no,
            ac_no=customer.ac_no,
            error='A'
        ).order_by('-sys_date')[:50],
        'cashier_transactions': Memtrans.all_objects.filter(
            gl_no=customers.gl_no if customers else None,
            ac_no=customers.ac_no if customers else None,
            error='A'
        ).order_by('-sys_date')[:50] if customers else [],
    }
    return render(request, 'transactions/non_cash/income.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_admin)
# Ensure this function exists


def expense(request, uuid):
    # Get user and branch information
    user = request.user
    user_branch = user.branch
    customer = get_object_or_404(Customer.all_objects, uuid=uuid)
    formatted_balance = '{:,.2f}'.format(customer.balance)
    data = Memtrans.objects.filter(branch=user_branch).order_by('-id').first()

    # Get cashier information
    cashier_gl_value = user.cashier_gl
    cashier_customer = Customer.all_objects.filter(gl_no=cashier_gl_value).first()
    
    # Get company information
    company = get_object_or_404(Branch, id=user.branch_id)
    company_date = company.session_date.strftime('%Y-%m-%d') if company.session_date else ''
    customer_branch = customer.branch
    
    # Retrieve the last transaction for the customer
    last_transaction = Memtrans.objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        error='A'
    ).order_by('-id').first()

    # Initial form values
    initial_values = {
        'branch': user_branch,
        'cust_branch': customer_branch,
        'gl_no_cashier': cashier_customer.gl_no,
        'ac_no_cashier': cashier_customer.ac_no,
        'gl_no_cust': customer.gl_no,
        'ac_no_cust': customer.ac_no,
    }

    # Compute balances
    sum_of_amount_cash = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cashier'],
        ac_no=initial_values['ac_no_cashier'],
        error='A',
        branch=user_branch
    ).aggregate(total_amount1=Sum('amount'))['total_amount1'] or 0

    sum_of_amount_cust = Memtrans.objects.filter(
        gl_no=initial_values['gl_no_cust'],
        ac_no=initial_values['ac_no_cust'],
        error='A',
    ).aggregate(total_amount2=Sum('amount'))['total_amount2'] or 0

    # Check session status
    if company.session_status == 'Closed':
        messages.error(request, 'Session Closed! You cannot post any transaction.')
        return redirect('dashboard')  # Redirect to appropriate page

    if request.method == 'POST':
        form = MemtransForm(request.POST)
        if form.is_valid():
            # Use the branch from form or fallback to customer's branch
            branch_customer = form.cleaned_data.get('cust_branch', customer_branch)
            amount = form.cleaned_data['amount']
            app_date = form.cleaned_data['app_date']

            # Validate application date
            if app_date and company.session_date and app_date > company.session_date:
                form.add_error('app_date', 'Application date cannot be greater than the company session date.')
            else:
                with transaction.atomic():
                    # Generate unique transaction ID
                    unique_id = generate_expense_id()

                    # Customer transaction (debit)
                    customer_transaction = Memtrans(
                        branch=branch_customer,
                        cust_branch=customer_branch,
                        gl_no=customer.gl_no,
                        ac_no=customer.ac_no,
                        amount=-amount,
                        description=form.cleaned_data['description'],
                        error='A',
                        account_type=customer.label,
                        type='D',
                        ses_date=form.cleaned_data['ses_date'],
                        app_date=form.cleaned_data['app_date'],
                        sys_date=timezone.now(),
                        customer=customer,
                        code='EX',  # Changed to EX for expense
                        user=user,
                        trx_no=unique_id
                    )
                    customer_transaction.save()

                    # Cashier transaction (credit)
                    cashier_transaction = Memtrans(
                        branch=user_branch,
                        cust_branch=user_branch,
                        gl_no=cashier_customer.gl_no,
                        ac_no=cashier_customer.ac_no,
                        amount=amount,
                        description=f'Expense: {customer.first_name}, {customer.last_name}',
                        error='A',
                        type='C',
                        account_type=cashier_customer.label,
                        customer=cashier_customer,
                        code='EX',  # Changed to EX for expense
                        user=user,
                        trx_no=unique_id,
                        ses_date=form.cleaned_data['ses_date'],
                        app_date=form.cleaned_data['app_date'],
                        sys_date=timezone.now()
                    )
                    cashier_transaction.save()

                    # Update customer balance directly (more efficient than recalculating)
                    customer.balance -= amount
                    customer.save()

                    # Update cashier balance directly
                    cashier_customer.balance += amount
                    cashier_customer.save()

                    # Notification logic (similar to withdraw)
                    if customer.sms:
                        try:
                            sms_message = f"Dear {customer.first_name}, Expense of {amount} from A/C XXXXX{customer.ac_no} has been processed. Bal: {customer.balance}."
                            send_sms(customer.phone_no, sms_message)
                        except Exception as e:
                            print(f"SMS sending failed: {str(e)}")

                    if customer.email_alert and customer.email:
                        try:
                            email_context = {
                                'customer_name': customer.first_name,
                                'amount': amount,
                                'new_balance': customer.balance,
                                'transaction_date': timezone.now(),
                                'transaction_id': unique_id,
                                'description': form.cleaned_data['description'],
                                'transaction_type': 'Expense',
                            }
                            send_email(
                                to_email=customer.email,
                                subject=f"Expense Confirmation - #{unique_id}",
                                template_name='transactions/emails/expense_email.html',
                                context=email_context
                            )
                        except Exception as e:
                            print(f"Email sending failed: {str(e)}")

                    messages.success(request, 'Expense processed successfully!')
                    return redirect('expense', uuid=uuid)
    else:
        form = MemtransForm(initial=initial_values)
        # Disable branch fields if needed
        form.fields['branch'].disabled = True
        form.fields['cust_branch'].disabled = True

    context = {
        'form': form,
        'data': data,
        'customer': customer,
        'total_amount': sum_of_amount_cust,
        'formatted_balance': formatted_balance,
        'customers': cashier_customer,
        'sum_of_amount_cash': sum_of_amount_cash,
        'sum_of_amount_cust': sum_of_amount_cust,
        'company': company,
        'company_date': company_date,
        'last_transaction': last_transaction,
        'last_transactions': Memtrans.all_objects.filter(
            gl_no=customer.gl_no,
            ac_no=customer.ac_no,
            error='A'
        ).order_by('-sys_date')[:50],
        'cashier_transactions': Memtrans.all_objects.filter(
            gl_no=cashier_customer.gl_no if cashier_customer else None,
            ac_no=cashier_customer.ac_no if cashier_customer else None,
            error='A'
        ).order_by('-sys_date')[:50] if cashier_customer else [],
    }
    return render(request, 'transactions/non_cash/expense.html', context)


# @login_required(login_url='login')
# @user_passes_test(check_role_admin)
# def choose_deposit(request):
#     user_company_name = request.user.branch.company_name  # get logged-in user's company name
    
#     # Filter customers whose company_name matches user's branch company name
#     customers = Customer.objects.filter(label='C', company_name=user_company_name).order_by('-id')
    
#     # Prepare GL/AC pairs for customers filtered by company
#     gl_ac_pairs = customers.values_list('gl_no', 'ac_no')
    
#     # Get all balances for these customers
#     balances = Memtrans.objects.filter(
#         gl_no__in=[pair[0] for pair in gl_ac_pairs],
#         ac_no__in=[pair[1] for pair in gl_ac_pairs],
#         error='A'
#     ).values('gl_no', 'ac_no').annotate(
#         total_amount=Sum('amount')
#     )
    
#     balance_dict = {
#         (b['gl_no'], b['ac_no']): b['total_amount'] or 0.0
#         for b in balances
#     }
    
#     customer_data = []
#     for customer in customers:
#         balance = balance_dict.get((customer.gl_no, customer.ac_no), 0.0)
#         customer_data.append({
#             'customer': customer,
#             'total_amount': balance,
#             'formatted_balance': '{:,.2f}'.format(balance)
#         })
    
#     latest_transaction = Memtrans.objects.order_by('-id').first()
    
#     context = {
#         'data': latest_transaction,
#         'customer_data': customer_data,
#         'total_customers': customers.count(),
#     }
    
#     return render(request, 'transactions/cash_trans/choose_deposit.html', context)

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_deposit(request):
    data = Memtrans.objects.all().order_by('-id').first()

    # Get user's branch directly from user model
    user_branch = request.user.get_branch()  # ✅ Use the helper method we added

    if user_branch:
        # Filter customers for this branch
        customers = Customer.objects.filter(label='C').order_by('-id')
    else:
        # If user has no branch, show all
        customers = Customer.objects.filter(label='C').order_by('-id')
    
    total_amounts = []
    for customer in customers:
        total_amount = Memtrans.objects.filter(
            gl_no=customer.gl_no,
            ac_no=customer.ac_no,
            error='A',
             # keep filtering consistent
        ).aggregate(total_amount=Sum('amount'))['total_amount']

        total_amounts.append({
            'customer': customer,
            'total_amount': total_amount or 0.0,
        })

    return render(request, 'transactions/cash_trans/choose_deposit.html', {
        'data': data,
        'total_amounts': total_amounts,
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def choose_withdrawal(request):
    # Get the latest transaction (if any exists)
    latest_transaction = Memtrans.objects.order_by('-id').first()

    # Get branch by the user's branch_id
    from accounts.utils import get_branch_from_vendor_db
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    
    # Filter customers based on branch access - head office sees all company branches
    if user_branch:
        if user_branch.head_office:
            customers = Customer.objects.filter(
                label='C',
                branch__company=user_branch.company
            ).order_by('-id')
        else:
            customers = Customer.objects.filter(
                label='C',
                branch=user_branch
            ).order_by('-id')
    else:
        customers = Customer.objects.none()

    # Prepare GL/AC pairs for all filtered customers
    gl_ac_pairs = customers.values_list('gl_no', 'ac_no')

    # Get all balances for these GL/AC pairs in one query
    balances = Memtrans.objects.filter(
        gl_no__in=[pair[0] for pair in gl_ac_pairs],
        ac_no__in=[pair[1] for pair in gl_ac_pairs],
        error='A'
    ).values('gl_no', 'ac_no').annotate(
        total_amount=Sum('amount')
    )

    # Create quick lookup dictionary for balances
    balance_dict = {
        (b['gl_no'], b['ac_no']): b['total_amount'] or 0.0
        for b in balances
    }

    # Prepare customer data including formatted balances and withdrawal eligibility
    customer_data = []
    for customer in customers:
        balance = balance_dict.get((customer.gl_no, customer.ac_no), 0.0)
        customer_data.append({
            'customer': customer,
            'total_amount': balance,
            'formatted_balance': '{:,.2f}'.format(balance),
            'can_withdraw': balance > 0
        })

    context = {
        'data': latest_transaction,
        'customer_data': customer_data,
        'total_customers': customers.count(),
    }

    return render(request, 'transactions/cash_trans/choose_withdrawal.html', context)

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



def general_journal(request, uuid):
    user_branch = request.user.branch
    # Fetch the customer with the given UUID
    customer = get_object_or_404(Customer.all_objects, uuid=uuid)
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
                        return redirect('general_journal', uuid=uuid)

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

            # Fetch the branch code from the first Memtrans record
            branch_code = transactions.first().branch  # Assuming 'branch' stores the branch code as a string

            # Get the Branch object using branch_code
            company = get_object_or_404(Branch, branch_code=branch_code)  # Corrected lookup

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
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    memtrans_list = Memtrans.all_objects.filter(branch_id__in=branch_ids)
    return render(request, 'transactions/non_cash/memtrans_list.html', {'memtrans_list': memtrans_list})


@login_required(login_url='login')
def customer_transaction_history(request, uuid):
    customer = get_object_or_404(Customer.all_objects, uuid=uuid)
    transactions = Memtrans.all_objects.filter(
        gl_no=customer.gl_no,
        ac_no=customer.ac_no,
        error='A'
    ).order_by('-sys_date')[:50]
    return render(request, 'transactions/cash_trans/customer_history.html', {
        'customer': customer,
        'transactions': transactions
    })

def delete_memtrans(request, uuid):
    memtrans = get_object_or_404(Memtrans, uuid=uuid)
    trx_no = memtrans.trx_no
    Memtrans.objects.filter(trx_no=trx_no).delete()
    return redirect(reverse('memtrans_list'))



from django.shortcuts import render
# from loans.models import Loans
from django.urls import reverse 


def loan_list(request):
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    loan_list = Loans.all_objects.filter(branch_id__in=branch_ids)
    return render(request, 'loans/loan_list.html', {'loan_list': loan_list})



def delete_loan(request, uuid):
    loan = get_object_or_404(Loans, uuid=uuid)
    loan.delete()
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
                # Fetch the branch instance
                branch = Branch.objects.filter(branch_code=row['branch']).first()
                if not branch:
                    # Skip or handle missing branch
                    continue

                # Fetch the customer instance
                customer = Customer.objects.filter(gl_no=row['gl_no'], ac_no=row['ac_no']).first()
                if customer:
                    customer_name = f"{customer.first_name} {customer.middle_name} {customer.last_name}"
                    error_message = ''
                else:
                    customer_name = 'Unknown'
                    error_message = 'Account not found'

                # Create a Memtrans instance
                transaction = Memtrans(
                    branch=branch,
                    customer=customer,
                    loans=row.get('loans', ''),
                    cycle=row.get('cycle', 0),
                    gl_no=row['gl_no'],
                    ac_no=row['ac_no'],
                    trx_no=generate_upload_excel(),  # Automatically generated transaction ID
                    ses_date=row['ses_date'],
                    app_date=row.get('app_date'),
                    sys_date=timezone.now(),
                    amount=row['amount'],
                    description=row.get('description', ''),
                    error='A',  # Automatically set
                    type='D',   # Automatically set
                    user=request.user,
                    code='UP'
                )
                
                # Add transaction details to the session for preview
                transactions.append({
                    'branch': branch.branch_code,
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
                    'error': error_message if error_message else transaction.error,
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
        company = Branch.objects.first()
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
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    rates = InterestRate.all_objects.filter(branch_id__in=branch_ids) if hasattr(InterestRate, 'all_objects') else InterestRate.objects.filter(branch_id__in=branch_ids)
    return render(request, 'transactions/interest_rate_list.html', {'rates': rates})



def edit_interest_rate(request, uuid):
    rate = get_object_or_404(InterestRate, uuid=uuid)
    if request.method == 'POST':
        form = InterestRateForm(request.POST, instance=rate)
        if form.is_valid():
            form.save()
            return redirect('interest_rate_list')  # Redirect to the list page
    else:
        form = InterestRateForm(instance=rate)
    
    return render(request, 'transactions/edit_interest_rate.html', {'form': form})

def delete_interest_rate(request, uuid):
    rate = get_object_or_404(InterestRate, uuid=uuid)
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
