import logging
from django.shortcuts import get_object_or_404, render
# from docx import Document
from django.template.loader import render_to_string
# Create your views here.
from django.http import HttpResponse
from django.template.loader import get_template
from django.template import Context
# from weasyprint import HTML
from accounts.views import check_role_admin
from accounts_admin.models import Account, Account_Officer
from company.models import Company, Branch
from django.db.models import Sum
from loans.models import Loans
from profit_solutions.settings import BASE_DIR
from reports.forms import StatementForm
from transactions.models import Memtrans
# from docxtpl import DocxTemplate
from io import BytesIO
import tempfile
import os
from django.contrib.auth.decorators import login_required, user_passes_test
# import cairo

def generate_pdf(request, id):
    customer = get_object_or_404(Loans, id=id)

    # Access the related Customer instance
    customers = customer.customer
    cust_data = Account.objects.filter(gl_no__startswith='20').exclude(gl_no='20100').exclude(
        gl_no='20200').exclude(gl_no='20000')
    gl_no = Account.objects.all().values_list('gl_no', flat=True).filter(gl_no__startswith='200')

    # Filter Memtrans records based on the ac_no of the customer
    ac_no_list = Memtrans.objects.filter(ac_no=customer.ac_no).values_list('ac_no', flat=True).distinct()
    cust_branch = Company.objects.first()
    # Calculate the total amount for each ac_no
    amounts = Memtrans.objects.filter(ac_no=customer.ac_no).values('gl_no').annotate(total_amount=Sum('amount'))
    loan_schedule = customer.calculate_loan_schedule()
    officer = Account_Officer.objects.all()
    total_interest_sum = sum(payment['interest_payment'] for payment in loan_schedule)
    total_principal_sum = sum(payment['principal_payment'] for payment in loan_schedule)
    total_payments_sum = sum(payment['total_payment'] for payment in loan_schedule)

    context = {
        'customers': customers,
        'customer': customer,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'ac_no_list': ac_no_list,
        'amounts': amounts,
        'loan_schedule': loan_schedule,
        'total_interest_sum': total_interest_sum,
        'total_principal_sum': total_principal_sum,
        'total_payments_sum': total_payments_sum,
        }  # Replace with your data

    html_string = render(request, 'reports/loans/generate_pdf.html', context).content.decode('utf-8')
    pdf_file = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'filename="output.pdf"'

    return response



    
from django.http import HttpResponse
from docx import Document
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
import os

def generate_doc(request, id):
    customer = get_object_or_404(Loans, id=id)

    # Access the related Customer instance
    customers = customer.customer
    cust_data = Account.objects.filter(gl_no__startswith='20').exclude(gl_no='20100').exclude(
        gl_no='20200').exclude(gl_no='20000')
    gl_no = Account.objects.all().values_list('gl_no', flat=True).filter(gl_no__startswith='200')

    # Filter Memtrans records based on the ac_no of the customer
    ac_no_list = Memtrans.objects.filter(ac_no=customer.ac_no).values_list('ac_no', flat=True).distinct()
    cust_branch = Company.objects.all()
    # Calculate the total amount for each ac_no
    amounts = Memtrans.objects.filter(ac_no=customer.ac_no).values('gl_no').annotate(total_amount=Sum('amount'))
    loan_schedule = customer.calculate_loan_schedule()
    officer = Account_Officer.objects.all()
    total_interest_sum = sum(payment['interest_payment'] for payment in loan_schedule)
    total_principal_sum = sum(payment['principal_payment'] for payment in loan_schedule)
    total_payments_sum = sum(payment['total_payment'] for payment in loan_schedule)

    context = {
        'customers': customers,
        'customer': customer,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'ac_no_list': ac_no_list,
        'amounts': amounts,
        'loan_schedule': loan_schedule,
        'total_interest_sum': total_interest_sum,
        'total_principal_sum': total_principal_sum,
        'total_payments_sum': total_payments_sum,
    }  # Replace with your data

    # Render HTML content from the template
    html_string = render_to_string('reports/loans/generate_doc.html', context)

    # Create a new Document
    document = Document()

    # Add paragraphs to the document
    for paragraph in html_string.split('<p>'):
        document.add_paragraph(paragraph.strip('</p>'))

    # Save the document to a response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = 'filename="output.docx"'
    document.save(response)

    return response




from openpyxl import Workbook

from django.http import HttpResponse
from io import BytesIO
from django.template.loader import render_to_string

def generate_excel(request, id):
    customer = get_object_or_404(Loans, id=id)

    # Access the related Customer instance
    customers = customer.customer
    cust_data = Account.objects.filter(gl_no__startswith='20').exclude(gl_no='20100').exclude(
        gl_no='20200').exclude(gl_no='20000')
    gl_no = Account.objects.all().values_list('gl_no', flat=True).filter(gl_no__startswith='200')

    # Filter Memtrans records based on the ac_no of the customer
    ac_no_list = Memtrans.objects.filter(ac_no=customer.ac_no).values_list('ac_no', flat=True).distinct()
    cust_branch = Company.objects.all()
    # Calculate the total amount for each ac_no
    amounts = Memtrans.objects.filter(ac_no=customer.ac_no).values('gl_no').annotate(total_amount=Sum('amount'))
    loan_schedule = customer.calculate_loan_schedule()
    officer = Account_Officer.objects.all()
    total_interest_sum = sum(payment['interest_payment'] for payment in loan_schedule)
    total_principal_sum = sum(payment['principal_payment'] for payment in loan_schedule)
    total_payments_sum = sum(payment['total_payment'] for payment in loan_schedule)

    context = {
        'customers': customers,
        'customer': customer,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'ac_no_list': ac_no_list,
        'amounts': amounts,
        'loan_schedule': loan_schedule,
        'total_interest_sum': total_interest_sum,
        'total_principal_sum': total_principal_sum,
        'total_payments_sum': total_payments_sum,
    }  # Replace with your data

  

#     # Render HTML content from the template with the context
    html_string = render_to_string('reports/loans/generate_excel.html', context)

    # Create a new Workbook
    workbook = Workbook()

    # Get the active sheet
    sheet = workbook.active

    # Add headings to the sheet
    sheet.append(['Period', 'Payment Date', 'Principal Payment', 'Interest Payment', 'Total Payment', 'Principal Remaining'])

    # Add data rows to the sheet
    for payment in loan_schedule:
        sheet.append([
            payment['period'],
            payment['payment_date'],
            payment['principal_payment'],
            payment['interest_payment'],
            payment['total_payment'],
            payment['principal_remaining'],
        ])

    # Save the workbook to a BytesIO buffer
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    # Save the workbook to a response
    response = HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=loan_schedule.xlsx'

    return response







import csv
from django.http import HttpResponse
from io import StringIO

def generate_csv(request, id):
    customer = get_object_or_404(Loans, id=id)

    # Access the related Customer instance
    customers = customer.customer
    cust_data = Account.objects.filter(gl_no__startswith='20').exclude(gl_no='20100').exclude(
        gl_no='20200').exclude(gl_no='20000')
    gl_no = Account.objects.all().values_list('gl_no', flat=True).filter(gl_no__startswith='200')

    # Filter Memtrans records based on the ac_no of the customer
    ac_no_list = Memtrans.objects.filter(ac_no=customer.ac_no).values_list('ac_no', flat=True).distinct()
    cust_branch = Company.objects.all()
    # Calculate the total amount for each ac_no
    amounts = Memtrans.objects.filter(ac_no=customer.ac_no).values('gl_no').annotate(total_amount=Sum('amount'))
    loan_schedule = customer.calculate_loan_schedule()
    officer = Account_Officer.objects.all()
    total_interest_sum = sum(payment['interest_payment'] for payment in loan_schedule)
    total_principal_sum = sum(payment['principal_payment'] for payment in loan_schedule)
    total_payments_sum = sum(payment['total_payment'] for payment in loan_schedule)

    context = {
        'customers': customers,
        'customer': customer,
        'cust_data': cust_data,
        'cust_branch': cust_branch,
        'gl_no': gl_no,
        'officer': officer,
        'ac_no_list': ac_no_list,
        'amounts': amounts,
        'loan_schedule': loan_schedule,
        'total_interest_sum': total_interest_sum,
        'total_principal_sum': total_principal_sum,
        'total_payments_sum': total_payments_sum,
    }  # Replace with your data

  
    csv_content = render_to_string('reports/loans/generate_csv.html', {'loan_schedule': loan_schedule})
     # Create a CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=loan_schedule.csv'

    # Create a CSV writer
    csv_writer = csv.writer(response)

    # Write header row
    csv_writer.writerow(['Period', 'Payment Date', 'Principal Payment', 'Interest Payment', 'Total Payment', 'Principal Remaining'])

    # Write data rows
    for payment in loan_schedule:
        csv_writer.writerow([
            payment['period'],
            payment['payment_date'],
            payment['principal_payment'],
            payment['interest_payment'],
            payment['total_payment'],
            payment['principal_remaining'],
        ])
    response.write(csv_content)

    return response




# views.py
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect
from django.urls import reverse



from django.shortcuts import render





from django.shortcuts import render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage



def generate_statement_data(gl_no, ac_no, start_date, end_date):
    transactions = Memtrans.objects.filter(
        gl_no=gl_no,
        ac_no=ac_no,
        ses_date__range=(start_date, end_date)
    ).order_by('ses_date')

    statement_data = []
    running_balance = 0
    total_debit = 0
    total_credit = 0
    opening_balance = 0
    closing_balance = 0

    for transaction in transactions:
        if transaction.ses_date < start_date:
            # Accumulate transactions before the start date for opening balance
            if transaction.amount > 0:
                opening_balance += transaction.amount
            else:
                opening_balance -= abs(transaction.amount)

    # Include a single entry for opening balance in the running balance
    running_balance += opening_balance

    # Include a separate entry for opening balance in the statement data
    statement_data.append({
        'date': start_date,
        'description': 'Opening Balance',
        'trx_no': '',
        'debit': 0,
        'credit': 0,
        'running_balance': running_balance,
    })

    for transaction in transactions:
        if transaction.ses_date >= start_date:
            if transaction.amount > 0:
                credit_amount = transaction.amount
                debit_amount = 0
            else:
                credit_amount = 0
                debit_amount = abs(transaction.amount)

            running_balance += (credit_amount - debit_amount)
            total_debit += debit_amount
            total_credit += credit_amount

            description = transaction.description or ''
            statement_data.append({
                'date': transaction.ses_date,
                'description': description,
                'trx_no': transaction.trx_no,
                'debit': debit_amount,
                'credit': credit_amount,
                'running_balance': running_balance,
            })

    closing_balance = running_balance


# views.py

@login_required(login_url='login')
@user_passes_test(check_role_admin)
def front_office_report(request):
   
    return render(request, 'reports/front_office_report.html')


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def back_office_report(request):
   
    return render(request, 'reports/back_office_report.html')


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def financial_report(request):
   
    return render(request, 'reports/financials/financial_report.html')



@login_required(login_url='login')
@user_passes_test(check_role_admin)
def savings_report(request):
   
    return render(request, 'reports/savings/savings_report.html')

from django.shortcuts import render
from django.db.models import Sum
from .forms import LoanOutstandingBalanceForm, StatementForm

from django.db.models import Q

from django.db.models import F
from django.db.models.functions import Now
# ...


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def generate_statement_view(request):
    branch = get_object_or_404(Branch, id=1)
    branch_date = branch.session_date.strftime('%Y-%m-%d') if branch.session_date else ''
    
    if branch.session_status == 'Closed':
        return HttpResponse("You can not post any transaction. Session is closed.") 
    else:
        if request.method == 'POST':
            user = request.user
            branch = user.branch 
            form = StatementForm(request.POST)
            if form.is_valid():
                start_date = form.cleaned_data['start_date']
                end_date = form.cleaned_data['end_date']
                gl_no = form.cleaned_data['gl_no']
                ac_no = form.cleaned_data['ac_no']

                # Retrieve transactions within the specified date range and filter by gl_no and ac_no
                transactions = Memtrans.objects.filter(
                    ses_date__range=[start_date, end_date],
                    gl_no=gl_no,
                    ac_no=ac_no
                ).exclude(error='H').order_by('ses_date', 'trx_no').annotate(current_time=Now()).order_by('ses_date')

                # Calculate opening, closing, debit, and credit
                opening_balance = Memtrans.objects.filter(
                    ses_date__lt=start_date,
                    gl_no=gl_no,
                    ac_no=ac_no
                ).exclude(error='H').aggregate(opening_balance=Sum('amount'))['opening_balance'] or 0

                closing_balance = Memtrans.objects.filter(
                    ses_date__lte=end_date,
                    gl_no=gl_no,
                    ac_no=ac_no
                ).exclude(error='H').aggregate(closing_balance=Sum('amount'))['closing_balance'] or 0

                debit_amount = transactions.filter(amount__gt=0).aggregate(debit_amount=Sum('amount'))['debit_amount'] or 0
                credit_amount = transactions.filter(amount__lt=0).aggregate(credit_amount=Sum('amount'))['credit_amount'] or 0

                # Retrieve the first transaction to get the customer's full name
                first_transaction = transactions.first()
                full_name = first_transaction.customer.get_full_name() if first_transaction and first_transaction.customer else ''

                statement_data = []
                running_balance = opening_balance

                for transaction in transactions:
                    running_balance += transaction.amount
                    entry = {
                        'date': transaction.ses_date,
                        'trx_no': transaction.trx_no,
                        'description': transaction.description,
                        'debit': transaction.amount if transaction.amount > 0 else 0,
                        'credit': abs(transaction.amount) if transaction.amount < 0 else 0,
                        'running_balance': running_balance,
                    }
                    statement_data.append(entry)

                context = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'gl_no': gl_no,
                    'ac_no': ac_no,
                    'opening_balance': opening_balance,
                    'closing_balance': closing_balance,
                    'debit_amount': debit_amount,
                    'credit_amount': credit_amount,
                    'statement_data': statement_data,
                    'form': form,
                    'full_name': full_name,
                    'branch': branch,
                    'company': branch.company,  # Assuming Branch model has a company ForeignKey
                    'branch_date': branch_date,
                }

                return render(request, 'reports/accounts/statement_of_account.html', context)

        else:
            form = StatementForm()

    return render(request, 'reports/accounts/input_form.html', {
        'form': form,
        'branch': branch,
        'company': branch.company,  # Assuming Branch model has a company ForeignKey
        'branch_date': branch_date
    })

from django.shortcuts import render
from transactions.models import Memtrans, Account
from datetime import datetime
from collections import defaultdict
from .forms import TrialBalanceForm


def generate_trial_balance(start_date, end_date, branch_code=None):
    """
    Generate a trial balance report between the specified start and end dates for a given branch code.

    Args:
        start_date (date): The start date for the report.
        end_date (date): The end date for the report.
        branch_code (str or None): The branch code to filter the transactions, or None to include all branches.

    Returns:
        tuple: Contains sorted trial balance data, subtotals for different GL number prefixes, and totals for debit, credit, and balance.
    """
    # Query all relevant Memtrans entries for the given branch
    memtrans_entries = Memtrans.objects.filter(ses_date__range=[start_date, end_date], error='A')

    # Apply branch filtering only if a specific branch code is provided
    if branch_code:
        memtrans_entries = memtrans_entries.filter(branch=branch_code)

    # Initialize a dictionary to hold GL account balances
    gl_customer_balance = defaultdict(lambda: {'debit': 0, 'credit': 0, 'balance': 0})

    # Process each entry
    for entry in memtrans_entries:
        gl_no = entry.gl_no
        amount = entry.amount

        if entry.type == 'N':
            if amount < 0:
                gl_customer_balance[gl_no]['debit'] += abs(amount)
            else:
                gl_customer_balance[gl_no]['credit'] += amount
        else:
            if amount < 0:
                gl_customer_balance[gl_no]['credit'] += abs(amount)
            else:
                gl_customer_balance[gl_no]['debit'] += amount

    # Fetch all necessary accounts in a single query to improve performance
    accounts = Account.objects.filter(gl_no__in=gl_customer_balance.keys()).values('gl_no', 'gl_name')
    account_map = {account['gl_no']: account['gl_name'] for account in accounts}

    # Sort GL numbers and prepare trial balance data
    sorted_keys = sorted(gl_customer_balance.keys())
    sorted_trial_balance_data = []
    subtotal_1 = subtotal_2 = subtotal_3 = subtotal_4 = subtotal_5 = 0

    for gl_no in sorted_keys:
        balance_data = gl_customer_balance[gl_no]
        debit = balance_data['debit']
        credit = balance_data['credit']
        balance = debit - credit
        gl_name = account_map.get(gl_no, '')  # Default to empty string if GL number not found
        balance_data.update({'gl_no': gl_no, 'gl_name': gl_name, 'balance': balance})
        sorted_trial_balance_data.append(balance_data)

        # Calculate subtotals for GL numbers starting with specific prefixes
        if gl_no.startswith("1"):
            subtotal_1 += balance
        elif gl_no.startswith("2"):
            subtotal_2 += balance
        elif gl_no.startswith("3"):
            subtotal_3 += balance
        elif gl_no.startswith("4"):
            subtotal_4 += balance
        elif gl_no.startswith("5"):
            subtotal_5 += balance

    # Calculate total debit, credit, and balance
    total_debit = sum(entry['debit'] for entry in sorted_trial_balance_data)
    total_credit = sum(entry['credit'] for entry in sorted_trial_balance_data)
    total_balance = total_debit - total_credit

    return sorted_trial_balance_data, subtotal_1, subtotal_2, subtotal_3, subtotal_4, subtotal_5, total_debit, total_credit, total_balance



def trial_balance(request):
    branches = Branch.objects.all()  # Changed from Company to Branch

    if request.method == 'POST':
        form = TrialBalanceForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            branch_id = form.cleaned_data['branch'].id if form.cleaned_data['branch'] else None

            # When branch_id is None, set branch_code to None to indicate "All Branches"
            branch_code = None
            if branch_id is not None:
                branch = get_object_or_404(Branch, id=branch_id)  # Changed from Company to Branch
                branch_code = branch.branch_code

            # Generate trial balance data
            trial_balance_data, subtotal_1, subtotal_2, subtotal_3, subtotal_4, subtotal_5, total_debit, total_credit, total_balance = generate_trial_balance(start_date, end_date, branch_code)
            
            return render(request, 'reports/financials/trial_balance.html', {
                'form': form,
                'branches': branches,  # Changed from companies to branches
                'trial_balance_data': trial_balance_data,
                'subtotal_1': subtotal_1,
                'subtotal_2': subtotal_2,
                'subtotal_3': subtotal_3,
                'subtotal_4': subtotal_4,
                'subtotal_5': subtotal_5,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'total_balance': total_balance,
                'start_date': start_date,
                'end_date': end_date,
                'selected_branch': branch_id,
                'branch': branches.first() if branches.exists() else None,  # Changed from company to branch
            })
    else:
        form = TrialBalanceForm()

    return render(request, 'reports/financials/trial_balance.html', {
        'form': form,
        'branches': branches,  # Changed from companies to branches
        'selected_branch': None,
    })

from django.shortcuts import render, get_object_or_404
from transactions.models import Memtrans
from company.models import Branch
from customers.models import Customer
from .forms import TransactionForm
from django.db.models import Subquery, OuterRef, Value, CharField, Sum
from django.db.models.functions import Concat
from django.utils import timezone
from accounts.models import User

from django.contrib.auth.decorators import login_required



@login_required
def transaction_sequence_by_ses_date(request):
    current_datetime = timezone.now()
    report_data = None
    selected_branch = None
    start_date = None
    end_date = None
    session_date = None
    total_debit = 0
    total_credit = 0

    # Get the logged-in user's branch to determine their company_name
    try:
        user_branch = Branch.objects.get(user=request.user)
        user_company_name = user_branch.company_name

        # ✅ Filter branches with same company_name
        branches = Branch.objects.filter(company_name=user_company_name)

        # ✅ Get user IDs from those branches
        branch_users = User.objects.filter(branches__company_name=user_company_name).distinct()
    except Branch.DoesNotExist:
        branches = Branch.objects.none()
        branch_users = User.objects.none()
        user_company_name = None

    form = TransactionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        branch_id = form.cleaned_data['branch'].id if form.cleaned_data['branch'] else None
        user_id = form.cleaned_data['user'].id if form.cleaned_data['user'] else None
        code = form.cleaned_data['code'] if form.cleaned_data['code'] else None

        report_data = Memtrans.objects.filter(ses_date__range=(start_date, end_date)).select_related('user').order_by('ses_date')

        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id)
            report_data = report_data.filter(branch=selected_branch.branch_code)
            session_date = selected_branch.session_date
        else:
            selected_branch = None
            session_date = None

            if user_id:
                user = get_object_or_404(User, id=user_id)
                company_branches = Branch.objects.filter(company=user.company).values_list('branch_code', flat=True)
                report_data = report_data.filter(branch__in=company_branches)

        if user_id:
            report_data = report_data.filter(user_id=user_id)

        if code:
            report_data = report_data.filter(code=code)

        report_data = report_data.annotate(
            customer_name=Subquery(
                Customer.objects.filter(
                    gl_no=OuterRef('gl_no'),
                    ac_no=OuterRef('ac_no')
                ).annotate(
                    full_name=Concat(
                        'first_name',
                        Value(' '),
                        'middle_name',
                        Value(' '),
                        'last_name',
                        output_field=CharField()
                    )
                ).values('full_name')[:1]
            )
        )

        total_debit = report_data.filter(amount__lt=0).aggregate(total_debit=Sum('amount'))['total_debit'] or 0
        total_credit = report_data.filter(amount__gte=0).aggregate(total_credit=Sum('amount'))['total_credit'] or 0

    return render(request, 'reports/savings/transaction_sequence_by_ses_date.html', {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'report_data': report_data,
        'branches': branches,
        'users': branch_users,  # ✅ Only users under same company_name
        'selected_branch': selected_branch,
        'session_date': session_date,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'current_datetime': current_datetime,
    })




from django.shortcuts import render, get_object_or_404
from transactions.models import Memtrans
from company.models import Branch
from customers.models import Customer
from .forms import TransactionForm
from django.db.models import Subquery, OuterRef, Value, CharField, Sum
from django.db.models.functions import Concat
from django.utils import timezone
from accounts.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Subquery, OuterRef, Value, CharField
from django.db.models.functions import Concat

@login_required
def transaction_sequence_by_trx_date(request):
    current_datetime = timezone.now()
    report_data = None
    selected_branch = None
    start_date = None
    end_date = None
    session_date = None
    total_debit = 0
    total_credit = 0

    # ✅ Determine branches and users under the same company as current user
    try:
        user_branch = Branch.objects.get(user=request.user)
        user_company = user_branch.company_name

        branches = Branch.objects.filter(company_name=user_company)
        users = User.objects.filter(branches__company_name=user_company).distinct()
    except Branch.DoesNotExist:
        branches = Branch.objects.none()
        users = User.objects.none()

    form = TransactionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        branch_id = form.cleaned_data['branch'].id if form.cleaned_data['branch'] else None
        user_id = form.cleaned_data['user'].id if form.cleaned_data['user'] else None
        code = form.cleaned_data['code'] if form.cleaned_data['code'] else None

        # Base Query - Using sys_date instead of trx_date
        report_data = Memtrans.objects.filter(sys_date__range=(start_date, end_date)).select_related('user', 'branch').order_by('sys_date')

        # Branch Filtering
        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id)
            report_data = report_data.filter(branch=selected_branch)
            session_date = selected_branch.session_date
        else:
            selected_branch = None
            session_date = None

            if user_id:
                user = get_object_or_404(User, id=user_id)
                company_branches = Branch.objects.filter(company=user.company)
                report_data = report_data.filter(branch__in=company_branches)

        # User Filtering
        if user_id:
            report_data = report_data.filter(user_id=user_id)

        # Code Filtering
        if code:
            report_data = report_data.filter(code=code)

        # Annotate Customer Name
        report_data = report_data.annotate(
            customer_name=Subquery(
                Customer.objects.filter(
                    gl_no=OuterRef('gl_no'),
                    ac_no=OuterRef('ac_no')
                ).annotate(
                    full_name=Concat(
                        'first_name',
                        Value(' '),
                        'middle_name',
                        Value(' '),
                        'last_name',
                        output_field=CharField()
                    )
                ).values('full_name')[:1]
            )
        )

        # Calculate Totals
        total_debit = report_data.filter(amount__lt=0).aggregate(total_debit=Sum('amount'))['total_debit'] or 0
        total_credit = report_data.filter(amount__gte=0).aggregate(total_credit=Sum('amount'))['total_credit'] or 0

    return render(request, 'reports/savings/transaction_sequence_by_trx_date.html', {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'report_data': report_data,
        'branches': branches,
        'users': users,
        'selected_branch': selected_branch,
        'session_date': session_date,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'current_datetime': current_datetime,
    })
from django.contrib.auth.decorators import login_required
from django.db.models import Subquery, OuterRef, Value, CharField
from django.db.models.functions import Concat

@login_required
def transaction_sequence_by_trx_date(request):
    current_datetime = timezone.now()
    report_data = None
    selected_branch = None
    start_date = None
    end_date = None
    session_date = None
    total_debit = 0
    total_credit = 0

    # ✅ Determine branches and users under the same company as current user
    try:
        user_branch = Branch.objects.get(user=request.user)
        user_company = user_branch.company_name

        branches = Branch.objects.filter(company_name=user_company)
        users = User.objects.filter(branches__company_name=user_company).distinct()
    except Branch.DoesNotExist:
        branches = Branch.objects.none()
        users = User.objects.none()

    form = TransactionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        branch_id = form.cleaned_data['branch'].id if form.cleaned_data['branch'] else None
        user_id = form.cleaned_data['user'].id if form.cleaned_data['user'] else None
        code = form.cleaned_data['code'] if form.cleaned_data['code'] else None

        # Base Query - Using sys_date instead of trx_date
        report_data = Memtrans.objects.filter(sys_date__range=(start_date, end_date)).select_related('user', 'branch').order_by('sys_date')

        # Branch Filtering
        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id)
            report_data = report_data.filter(branch=selected_branch)
            session_date = selected_branch.session_date
        else:
            selected_branch = None
            session_date = None

            if user_id:
                user = get_object_or_404(User, id=user_id)
                company_branches = Branch.objects.filter(company=user.company)
                report_data = report_data.filter(branch__in=company_branches)

        # User Filtering
        if user_id:
            report_data = report_data.filter(user_id=user_id)

        # Code Filtering
        if code:
            report_data = report_data.filter(code=code)

        # Annotate Customer Name
        report_data = report_data.annotate(
            customer_name=Subquery(
                Customer.objects.filter(
                    gl_no=OuterRef('gl_no'),
                    ac_no=OuterRef('ac_no')
                ).annotate(
                    full_name=Concat(
                        'first_name',
                        Value(' '),
                        'middle_name',
                        Value(' '),
                        'last_name',
                        output_field=CharField()
                    )
                ).values('full_name')[:1]
            )
        )

        # Calculate Totals
        total_debit = report_data.filter(amount__lt=0).aggregate(total_debit=Sum('amount'))['total_debit'] or 0
        total_credit = report_data.filter(amount__gte=0).aggregate(total_credit=Sum('amount'))['total_credit'] or 0

    return render(request, 'reports/savings/transaction_sequence_by_trx_date.html', {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'report_data': report_data,
        'branches': branches,
        'users': users,
        'selected_branch': selected_branch,
        'session_date': session_date,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'current_datetime': current_datetime,
    })


from accounts.models import User

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Subquery, OuterRef, Value, CharField
from django.db.models.functions import Concat

@login_required
def transaction_journal_listing_by_ses_date(request):
    current_datetime = timezone.now()
    report_data = None
    selected_branch = None
    start_date = None
    end_date = None
    session_date = None
    total_debit = 0
    total_credit = 0

    # ✅ Filter branches and users based on the logged-in user's company
    try:
        user_branch = Branch.objects.get(user=request.user)
        user_company = user_branch.company_name

        branches = Branch.objects.filter(company_name=user_company)
        users = User.objects.filter(branches__company_name=user_company).distinct()
    except Branch.DoesNotExist:
        branches = Branch.objects.none()
        users = User.objects.none()

    form = TransactionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        branch_id = form.cleaned_data['branch'].id if form.cleaned_data['branch'] else None
        user_id = form.cleaned_data['user'].id if form.cleaned_data['user'] else None
        code = form.cleaned_data['code'] if form.cleaned_data['code'] else None

        # Base queryset
        report_data = Memtrans.objects.all()

        # Date filtering
        if start_date and end_date:
            report_data = report_data.filter(ses_date__range=(start_date, end_date))

        # Branch filtering
        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id)
            report_data = report_data.filter(branch=selected_branch)
            session_date = selected_branch.session_date

        # User filtering
        if user_id:
            report_data = report_data.filter(user_id=user_id)

        # Code filtering
        if code:
            report_data = report_data.filter(code=code)

        # Optimize and order
        report_data = report_data.select_related('user', 'branch').order_by('ses_date')

        # Annotate customer name
        report_data = report_data.annotate(
            customer_name=Subquery(
                Customer.objects.filter(
                    gl_no=OuterRef('gl_no'),
                    ac_no=OuterRef('ac_no')
                ).annotate(
                    full_name=Concat(
                        'first_name',
                        Value(' '),
                        'middle_name',
                        Value(' '),
                        'last_name',
                        output_field=CharField()
                    )
                ).values('full_name')[:1]
            )
        )

        # Calculate totals
        total_debit = report_data.filter(type='D').aggregate(total=Sum('amount'))['total'] or 0
        total_credit = report_data.filter(type='C').aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'reports/savings/transaction_journal_listing_by_ses_date.html', {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'report_data': report_data,
        'branches': branches,
        'users': users,
        'selected_branch': selected_branch,
        'session_date': session_date,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'current_datetime': current_datetime,
    })


from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Q, Value, OuterRef, Subquery, CharField
from django.db.models.functions import Concat
from .forms import TransactionForm

from django.contrib.auth.models import User


def transaction_journal_listing_by_trx_date(request):
    user_company_name = request.user.branches.first().company_name if request.user.branches.exists() else None

    # Filter branches under the same company_name
    branches = Branch.objects.filter(company_name=user_company_name)

    # Filter users who have branches with the same company_name
    users = User.objects.filter(
        branches__company_name=user_company_name
    ).distinct().only('id', 'username', 'first_name')

    current_datetime = timezone.now()

    form = TransactionForm(request.POST or None)
    context = {
        'form': form,
        'branches': branches,
        'users': users,
        'current_datetime': current_datetime,
        'report_data': None,
        'selected_branch': None,
        'start_date': None,
        'end_date': None,
        'session_date': None,
        'total_debit': 0,
        'total_credit': 0,
    }

    if request.method == 'POST' and form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        branch_id = form.cleaned_data['branch'].id if form.cleaned_data['branch'] else None
        user_id = form.cleaned_data['user'].id if form.cleaned_data['user'] else None
        code = form.cleaned_data['code'] if form.cleaned_data['code'] else None

        report_data = Memtrans.objects.select_related(
            'user', 'branch'
        ).only(
            'app_date', 'trx_no', 'code', 'gl_no', 'ac_no',
            'amount', 'user__username', 'branch__branch_name'
        )

        if start_date and end_date:
            report_data = report_data.filter(app_date__range=(start_date, end_date))

        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id)
            report_data = report_data.filter(branch=selected_branch)
            context['selected_branch'] = selected_branch
            context['session_date'] = selected_branch.session_date

        if user_id:
            report_data = report_data.filter(user_id=user_id)

        if code:
            report_data = report_data.filter(code=code)

        report_data = report_data.annotate(
            customer_name=Subquery(
                Customer.objects.filter(
                    gl_no=OuterRef('gl_no'),
                    ac_no=OuterRef('ac_no')
                ).annotate(
                    full_name=Concat(
                        'first_name', Value(' '),
                        'middle_name', Value(' '),
                        'last_name',
                        output_field=CharField()
                    )
                ).values('full_name')[:1],
                output_field=CharField()
            )
        ).order_by('app_date')

        totals = report_data.aggregate(
            total_debit=Sum('amount', filter=Q(amount__lt=0)),
            total_credit=Sum('amount', filter=Q(amount__gte=0))
        )

        context.update({
            'report_data': report_data,
            'start_date': start_date,
            'end_date': end_date,
            'total_debit': abs(totals['total_debit'] or 0),
            'total_credit': totals['total_credit'] or 0,
        })

    return render(request, 'reports/savings/transaction_journal_listing_by_trx_date.html', context)






def transaction_day_sheet_by_session_date(request):
    user_company_name = request.user.branches.first().company_name if request.user.branches.exists() else None

    # Filter branches and users by company_name
    branches = Branch.objects.filter(company_name=user_company_name)
    users = User.objects.filter(branches__company_name=user_company_name).distinct()

    current_datetime = timezone.now()

    form = TransactionForm(request.POST or None)
    report_data = None
    selected_branch = None
    start_date = None
    end_date = None
    session_date = None
    total_debit = 0
    total_credit = 0

    if request.method == 'POST' and form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        branch_id = form.cleaned_data['branch'].id if form.cleaned_data['branch'] else None
        user_id = form.cleaned_data['user'].id if form.cleaned_data['user'] else None
        code = form.cleaned_data['code'] if form.cleaned_data['code'] else None

        report_data = Memtrans.objects.filter(
            ses_date__range=(start_date, end_date)
        ).select_related('user', 'branch').order_by('ses_date', 'app_date')

        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id, company_name=user_company_name)
            report_data = report_data.filter(branch=selected_branch)
            session_date = selected_branch.session_date

        if user_id:
            report_data = report_data.filter(user_id=user_id)

        if code:
            report_data = report_data.filter(code=code)

        # Annotate customer name
        report_data = report_data.annotate(
            customer_name=Subquery(
                Customer.objects.filter(
                    gl_no=OuterRef('gl_no'),
                    ac_no=OuterRef('ac_no')
                ).annotate(
                    full_name=Concat(
                        'first_name', Value(' '),
                        'middle_name', Value(' '),
                        'last_name',
                        output_field=CharField()
                    )
                ).values('full_name')[:1],
                output_field=CharField()
            )
        )

        totals = report_data.aggregate(
            total_debit=Sum('amount', filter=Q(type='D')),
            total_credit=Sum('amount', filter=Q(type='C'))
        )
        total_debit = totals['total_debit'] or 0
        total_credit = totals['total_credit'] or 0

    return render(request, 'reports/savings/transaction_day_sheet_by_session_date.html', {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'report_data': report_data,
        'branches': branches,
        'users': users,
        'selected_branch': selected_branch,
        'session_date': session_date,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'current_datetime': current_datetime,
    })



from django.contrib.auth import get_user_model
User = get_user_model()

def transaction_day_sheet_by_trx_date(request):
    user_company_name = request.user.branches.first().company_name if request.user.branches.exists() else None

    branches = Branch.objects.filter(company_name=user_company_name)
    users = User.objects.filter(branches__company_name=user_company_name).distinct()

    current_datetime = timezone.now()

    form = TransactionForm(request.POST or None)
    report_data = None
    selected_branch = None
    start_date = None
    end_date = None
    session_date = None
    total_debit = 0
    total_credit = 0

    if request.method == 'POST' and form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        branch_id = form.cleaned_data['branch'].id if form.cleaned_data['branch'] else None
        user_id = form.cleaned_data['user'].id if form.cleaned_data['user'] else None
        code = form.cleaned_data['code'] if form.cleaned_data['code'] else None

        report_data = Memtrans.objects.filter(
            app_date__range=(start_date, end_date)
        ).select_related('user', 'branch').order_by('app_date', 'ses_date')

        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id, company_name=user_company_name)
            report_data = report_data.filter(branch=selected_branch)
            session_date = selected_branch.session_date

        if user_id:
            report_data = report_data.filter(user_id=user_id)

        if code:
            report_data = report_data.filter(code=code)

        report_data = report_data.annotate(
            customer_name=Subquery(
                Customer.objects.filter(
                    gl_no=OuterRef('gl_no'),
                    ac_no=OuterRef('ac_no')
                ).annotate(
                    full_name=Concat(
                        'first_name', Value(' '),
                        'middle_name', Value(' '),
                        'last_name',
                        output_field=CharField()
                    )
                ).values('full_name')[:1],
                output_field=CharField()
            )
        )

        totals = report_data.aggregate(
            total_debit=Sum('amount', filter=Q(type='D')),
            total_credit=Sum('amount', filter=Q(type='C'))
        )
        total_debit = totals['total_debit'] or 0
        total_credit = totals['total_credit'] or 0

    return render(request, 'reports/savings/transaction_day_sheet_by_trx_date.html', {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'report_data': report_data,
        'branches': branches,
        'users': users,
        'selected_branch': selected_branch,
        'session_date': session_date,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'current_datetime': current_datetime,
    })


def general_trx_register_by_session_date(request):
    current_datetime = timezone.now()
    
    # Get the logged-in user's branch company
    logged_in_user = request.user
    user_branches = logged_in_user.branches.all()
    
    # If user has branches, get the company name (assuming all user's branches belong to same company)
    company_name = user_branches.first().company_name if user_branches.exists() else None
    
    # Filter branches and users based on company_name
    if company_name:
        branches = Branch.objects.filter(company_name=company_name)
        users = User.objects.filter(branches__company_name=company_name).distinct()
    else:
        branches = Branch.objects.none()
        users = User.objects.none()

    if request.method == 'POST':
        # First get the selected branch id from POST data
        branch_id = request.POST.get('branch')
        selected_branch = Branch.objects.filter(id=branch_id).first() if branch_id else None

        # Now instantiate form with POST, and override user queryset
        form = TransactionForm(request.POST)
        form.fields['branch'].queryset = branches
        form.fields['user'].queryset = users

        if form.is_valid():
            # your existing filtering and context update here
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            branch = form.cleaned_data['branch']
            user_id = form.cleaned_data['user'].id if form.cleaned_data['user'] else None
            code = form.cleaned_data['code'] if form.cleaned_data['code'] else None

            report_data = Memtrans.objects.filter(
                ses_date__range=(start_date, end_date)
                ).select_related('user', 'branch').order_by('ses_date')

            if branch:
                selected_branch = get_object_or_404(Branch, id=branch.id)
                report_data = report_data.filter(branch=selected_branch)

            if user_id:
                report_data = report_data.filter(user_id=user_id)

            if code:
                report_data = report_data.filter(code=code)

            # annotate customer_name etc...
            report_data = report_data.annotate(
                customer_name=Subquery(
                    Customer.objects.filter(
                        gl_no=OuterRef('gl_no'),
                        ac_no=OuterRef('ac_no')
                    ).annotate(
                        full_name=Concat(
                            'first_name', Value(' '),
                            'middle_name', Value(' '),
                            'last_name',
                            output_field=CharField()
                        )
                    ).values('full_name')[:1],
                    output_field=CharField()
                )
            )

            totals = report_data.aggregate(
                total_debit=Sum('amount', filter=Q(type='D')),
                total_credit=Sum('amount', filter=Q(type='C'))
            )

            context = {
                'form': form,
                'branches': branches,
                'users': users,
                'current_datetime': current_datetime,
                'report_data': report_data,
                'selected_branch': selected_branch,
                'start_date': start_date,
                'end_date': end_date,
                'session_date': selected_branch.session_date if selected_branch else None,
                'total_debit': totals['total_debit'] or 0,
                'total_credit': totals['total_credit'] or 0,
            }
            return render(request, 'reports/savings/general_trx_register_by_session_date.html', context)
    else:
        # GET request: show filtered users and branches
        form = TransactionForm()
        form.fields['branch'].queryset = branches
        form.fields['user'].queryset = users
        context = {
            'form': form,
            'branches': branches,
            'users': users,
            'current_datetime': current_datetime,
            'report_data': None,
            'selected_branch': None,
            'start_date': None,
            'end_date': None,
            'session_date': None,
            'total_debit': 0,
            'total_credit': 0,
        }
        return render(request, 'reports/savings/general_trx_register_by_session_date.html', context)

def general_trx_register_by_trx_date(request):
    current_datetime = timezone.now()
    
    # Get the logged-in user
    logged_in_user = request.user
    
    # Get all branches associated with the logged-in user
    user_branches = logged_in_user.branches.all()
    
    # Get the company_name from the first branch (assuming all user's branches belong to same company)
    company_name = user_branches.first().company_name if user_branches.exists() else None
    
    # Filter branches and users based on company_name
    if company_name:
        branches = Branch.objects.filter(company_name=company_name)
        users = User.objects.filter(branches__company_name=company_name).distinct()
    else:
        branches = Branch.objects.none()
        users = User.objects.none()

    # Initialize the form
    form = TransactionForm(request.POST or None)
    form.fields['branch'].queryset = branches
    form.fields['user'].queryset = users

    context = {
        'form': form,
        'branches': branches,
        'users': users,
        'current_datetime': current_datetime,
        'report_data': None,
        'selected_branch': None,
        'start_date': None,
        'end_date': None,
        'session_date': None,
        'total_debit': 0,
        'total_credit': 0,
    }

    if request.method == 'POST' and form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        branch_id = form.cleaned_data['branch'].id if form.cleaned_data['branch'] else None
        user_id = form.cleaned_data['user'].id if form.cleaned_data['user'] else None
        code = form.cleaned_data['code'] if form.cleaned_data['code'] else None

        # Base queryset with proper method chaining
        report_data = Memtrans.objects.filter(
            app_date__range=(start_date, end_date)
        ).select_related(
            'user', 'branch'  # Removed branch__company as Company model no longer exists
        ).order_by('app_date')

        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id)
            report_data = report_data.filter(branch=selected_branch)
            context['selected_branch'] = selected_branch
            context['session_date'] = selected_branch.session_date
        
        if user_id:
            report_data = report_data.filter(user_id=user_id)
        
        if code:
            report_data = report_data.filter(code=code)

        # Annotate customer name
        report_data = report_data.annotate(
            customer_name=Subquery(
                Customer.objects.filter(
                    gl_no=OuterRef('gl_no'),
                    ac_no=OuterRef('ac_no')
                ).annotate(
                    full_name=Concat(
                        'first_name', Value(' '),
                        'middle_name', Value(' '),
                        'last_name',
                        output_field=CharField()
                    )
                ).values('full_name')[:1],
                output_field=CharField()
            )
        )

        # Calculate totals
        totals = report_data.aggregate(
            total_debit=Sum('amount', filter=Q(type='D')),
            total_credit=Sum('amount', filter=Q(type='C'))
        )

        context.update({
            'report_data': report_data,
            'start_date': start_date,
            'end_date': end_date,
            'total_debit': totals['total_debit'] or 0,
            'total_credit': totals['total_credit'] or 0,
        })

    return render(request, 'reports/savings/general_trx_register_by_trx_date.html', context)

from django.db.models import Sum, F, ExpressionWrapper, FloatField
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models.functions import Concat
from django.db.models import Value, CharField
from django.db.models import Subquery, OuterRef
from django.core.paginator import Paginator
from django.contrib import messages
from accounts_admin.models import Account



from django.db.models import Sum, F, ExpressionWrapper, FloatField
from django.shortcuts import render
from django.utils import timezone
from django.db.models.functions import Concat
from django.db.models import Value, CharField
from django.db.models import Subquery, OuterRef
from django.core.paginator import Paginator
from django.contrib import messages

def cashier_teller_cash_status_by_session_date(request):
    # Initialize base data with company filtering
    logged_in_user = request.user
    user_branches = logged_in_user.branches.all()
    company_name = user_branches.first().company_name if user_branches.exists() else None
    
    if company_name:
        branches = Branch.objects.filter(company_name=company_name)
        users = User.objects.filter(branches__company_name=company_name).distinct()
    else:
        branches = Branch.objects.none()
        users = User.objects.none()
    
    accounts = Account.objects.filter(gl_no__isnull=False).values('gl_no').distinct().order_by('gl_no')
    current_datetime = timezone.now()
    
    # Initialize context with default values
    context = {
        'branches': branches,
        'users': users,
        'accounts': accounts,
        'account_gl_numbers': [acc['gl_no'] for acc in accounts],
        'current_datetime': current_datetime,
        'company_date': timezone.now().date(),
        'report_data': None,
        'total_debit': 0,
        'total_credit': 0,
        'start_date': None,
        'end_date': None,
    }

    if request.method == 'POST':
        try:
            # Get raw POST data first for GL number handling
            gl_no = request.POST.get('gl_no')
            if gl_no == 'custom':
                gl_no = request.POST.get('gl_no_custom', '').strip() or None
            
            # Initialize base queryset
            report_data = Memtrans.objects.all().order_by('ses_date', 'id')
            
            # Apply date filter (required)
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            
            if not start_date or not end_date:
                messages.error(request, "Both start date and end date are required")
                return render(request, 'reports/savings/cashier_teller_cash_status_by_session_date.html', context)
            
            try:
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                messages.error(request, "Invalid date format")
                return render(request, 'reports/savings/cashier_teller_cash_status_by_session_date.html', context)
            
            report_data = report_data.filter(ses_date__range=(start_date, end_date))
            
            # Apply other filters
            branch_id = request.POST.get('branch')
            if branch_id:
                # Ensure the selected branch belongs to the same company
                if company_name:
                    selected_branch = get_object_or_404(Branch, id=branch_id, company_name=company_name)
                else:
                    selected_branch = get_object_or_404(Branch, id=branch_id)
                report_data = report_data.filter(branch_id=branch_id)
                context['selected_branch_obj'] = selected_branch
            
            user_id = request.POST.get('user')
            if user_id:
                # Ensure the selected user belongs to the same company
                if company_name:
                    get_object_or_404(User, id=user_id, branches__company_name=company_name)
                report_data = report_data.filter(user_id=user_id)
            
            code = request.POST.get('code')
            if code:
                report_data = report_data.filter(code=code)
            
            if gl_no:
                report_data = report_data.filter(gl_no=gl_no)
            
            ac_no = request.POST.get('ac_no')
            if ac_no:
                report_data = report_data.filter(ac_no=ac_no)
            
            # Check if any filters resulted in no data
            if not report_data.exists():
                messages.info(request, "No transactions found matching your criteria")
                context.update({
                    'start_date': start_date,
                    'end_date': end_date,
                    'gl_no': gl_no,
                    'ac_no': ac_no,
                    'code': code,
                    'user_id': user_id,
                })
                return render(request, 'reports/savings/cashier_teller_cash_status_by_session_date.html', context)
            
            # Add customer name annotation
            report_data = report_data.annotate(
                customer_name=Subquery(
                    Customer.objects.filter(
                        gl_no=OuterRef('gl_no'),
                        ac_no=OuterRef('ac_no')
                    ).annotate(
                        full_name=Concat(
                            'first_name',
                            Value(' '),
                            'middle_name',
                            Value(' '),
                            'last_name',
                            output_field=CharField()
                        )
                    ).values('full_name')[:1]
                )
            ).select_related('user', 'branch')
            
            # Calculate running balance
            running_balance = 0
            for transaction in report_data:
                running_balance += transaction.amount
                transaction.running_balance = running_balance
            
            # Pagination
            paginator = Paginator(report_data, 50)
            page_number = request.GET.get('page', 1)
            page_obj = paginator.get_page(page_number)
            
            # Calculate totals
            total_credit = report_data.filter(amount__gt=0).aggregate(
                Sum('amount')
            )['amount__sum'] or 0
            
            total_debit = report_data.filter(amount__lt=0).aggregate(
                total_debit=Sum(ExpressionWrapper(F('amount') * -1, output_field=FloatField()))
            )['total_debit'] or 0
            
            # Update context
            context.update({
                'start_date': start_date,
                'end_date': end_date,
                'gl_no': gl_no,
                'ac_no': ac_no,
                'code': code,
                'user_id': user_id,
                'branch_id': branch_id,
                'report_data': page_obj,
                'page_obj': page_obj,
                'total_debit': abs(total_debit),
                'total_credit': abs(total_credit),
            })
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            # Log the error here if you have logging setup
    
    return render(request, 'reports/savings/cashier_teller_cash_status_by_session_date.html', context)

def cashier_teller_cash_status_by_trx_date(request):
    # Get logged-in user's company information
    logged_in_user = request.user
    user_branches = logged_in_user.branches.all()
    company_name = user_branches.first().company_name if user_branches.exists() else None

    # Filter branches and users based on company_name
    if company_name:
        branches = Branch.objects.filter(company_name=company_name)
        users = User.objects.filter(branches__company_name=company_name).distinct()
    else:
        branches = Branch.objects.none()
        users = User.objects.none()

    accounts = Account.objects.filter(gl_no__isnull=False).values('gl_no').distinct().order_by('gl_no')
    current_datetime = timezone.now()
    
    # Initialize context with default values
    context = {
        'branches': branches,
        'users': users,
        'accounts': accounts,
        'account_gl_numbers': [acc['gl_no'] for acc in accounts],
        'current_datetime': current_datetime,
        'report_data': None,
        'total_debit': 0,
        'total_credit': 0,
    }

    if request.method == 'POST':
        try:
            # Get form data
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            branch_id = request.POST.get('branch')
            user_id = request.POST.get('user')
            code = request.POST.get('code')
            
            # Handle GL number
            gl_no = request.POST.get('gl_no')
            if gl_no == 'custom':
                gl_no = request.POST.get('gl_no_custom', '').strip()
            
            ac_no = request.POST.get('ac_no')
            page = request.GET.get('page', 1)

            # Validate dates
            if not start_date or not end_date:
                messages.error(request, "Both start date and end date are required")
                return render(request, 'reports/savings/cashier_teller_cash_status_by_trx_date.html', context)

            try:
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                messages.error(request, "Invalid date format")
                return render(request, 'reports/savings/cashier_teller_cash_status_by_trx_date.html', context)

            # Base query - using app_date for transaction date
            report_data = Memtrans.objects.filter(
                app_date__range=(start_date, end_date)
            ).select_related('user', 'branch').order_by('app_date', 'id')

            # Apply filters with company validation
            if branch_id:
                # Ensure the selected branch belongs to the same company
                if company_name:
                    selected_branch = get_object_or_404(Branch, id=branch_id, company_name=company_name)
                else:
                    selected_branch = get_object_or_404(Branch, id=branch_id)
                report_data = report_data.filter(branch=selected_branch)
                context['selected_branch'] = selected_branch
                context['selected_branch_obj'] = selected_branch

            if user_id:
                # Ensure the selected user belongs to the same company
                if company_name:
                    get_object_or_404(User, id=user_id, branches__company_name=company_name)
                report_data = report_data.filter(user_id=user_id)

            if code:
                report_data = report_data.filter(code=code)

            if gl_no:
                report_data = report_data.filter(gl_no=gl_no)

            if ac_no:
                report_data = report_data.filter(ac_no=ac_no)

            # Check if any filters resulted in no data
            if not report_data.exists():
                messages.info(request, "No transactions found matching your criteria")
                context.update({
                    'start_date': start_date,
                    'end_date': end_date,
                    'gl_no': gl_no,
                    'ac_no': ac_no,
                    'code': code,
                    'user_id': user_id,
                    'branch_id': branch_id,
                })
                return render(request, 'reports/savings/cashier_teller_cash_status_by_trx_date.html', context)

            # Annotation for customer name
            report_data = report_data.annotate(
                customer_name=Subquery(
                    Customer.objects.filter(
                        gl_no=OuterRef('gl_no'),
                        ac_no=OuterRef('ac_no')
                    ).annotate(
                        full_name=Concat(
                            'first_name',
                            Value(' '),
                            'middle_name',
                            Value(' '),
                            'last_name',
                            output_field=CharField()
                        )
                    ).values('full_name')[:1]
                )
            )

            # Calculate running balance
            running_balance = 0
            for transaction in report_data:
                running_balance += transaction.amount
                transaction.running_balance = running_balance

            # Pagination
            paginator = Paginator(report_data, 50)
            page_obj = paginator.get_page(page)

            # Calculate totals
            total_credit = report_data.filter(amount__gt=0).aggregate(
                total_credit=Sum('amount')
            )['total_credit'] or 0

            total_debit = report_data.filter(amount__lt=0).aggregate(
                total_debit=Sum(ExpressionWrapper(F('amount') * -1, output_field=FloatField()))
            )['total_debit'] or 0

            context.update({
                'start_date': start_date,
                'end_date': end_date,
                'gl_no': gl_no,
                'ac_no': ac_no,
                'code': code,
                'user_id': user_id,
                'branch_id': branch_id,
                'report_data': page_obj,
                'page_obj': page_obj,
                'total_debit': abs(total_debit),
                'total_credit': abs(total_credit),
            })

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    return render(request, 'reports/savings/cashier_teller_cash_status_by_trx_date.html', context)



# views.py
# views.py

from django.shortcuts import render
from transactions.models import Memtrans
from django.utils import timezone
from datetime import datetime



from django.shortcuts import render, get_object_or_404
from company.models import Company  # Import the Company model




from django.db.models import Sum

from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from customers.models import Customer
from django.db.models import OuterRef, Subquery, CharField, Value
from django.db.models.functions import Concat


from accounts_admin.models import Account



from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Sum
from datetime import datetime
from customers.models import Customer

def account_statement(request):
    # Get logged-in user and their associated branches
    logged_in_user = request.user
    user_branches = logged_in_user.branches.all()
    
    # Get distinct company names from user's branches
    company_names = user_branches.values_list('company_name', flat=True).distinct()
    
    # Filter branches and accounts based on user's company
    branches = Branch.objects.filter(company_name__in=company_names)
    gl_data = Account.objects.filter(branch__in=user_branches).values('gl_no', 'gl_name').distinct()
    
    gl_nos = [(item['gl_no'], item['gl_name']) for item in gl_data]

    # Get form parameters
    gl_no = request.POST.get('gl_no')
    ac_no = request.POST.get('ac_no')
    start_date = request.POST.get('start_date')
    end_date = request.POST.get('end_date')
    branch_id = request.POST.get('branch')

    # Initialize variables
    transactions = []
    statement_data = []
    balance = opening_balance = total_debit = total_credit = reporting_balance = 0
    selected_branch = None
    customer = None

    # Convert dates if provided
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid start date format")
            start_date = None
            
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid end date format")
            end_date = None

    # Process statement if all required fields are provided
    if gl_no and ac_no and start_date and end_date:
        # Base transaction query with company filter
        transactions = Memtrans.objects.filter(
            gl_no=gl_no,
            ac_no=ac_no,
            app_date__range=[start_date, end_date],
            branch__in=user_branches
        )

        # Apply branch filter if provided
        if branch_id:
            # Ensure the selected branch belongs to user's branches
            selected_branch = get_object_or_404(
                Branch, 
                id=branch_id,
                company_name__in=company_names
            )
            transactions = transactions.filter(branch=selected_branch)
        else:
            selected_branch = user_branches.first()  # Default to user's first branch

        # Get customer with validation
        customer = get_object_or_404(
            Customer,
            gl_no=gl_no,
            ac_no=ac_no,
            branch__in=user_branches
        )

        # Calculate opening balance (transactions before start date)
        opening_balance = Memtrans.objects.filter(
            gl_no=gl_no,
            ac_no=ac_no,
            app_date__lt=start_date,
            branch__in=(selected_branch.branches.all() if selected_branch else user_branches)
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Process transactions
        balance = opening_balance
        previous_transaction_date = None

        # Add opening balance entry
        statement_data.append({
            'branch': selected_branch.branch_name if selected_branch else 'All Your Branches',
            'trx_date': start_date,
            'trx_no': 'Opening Balance',
            'description': 'Opening Balance',
            'debit': '',
            'credit': '',
            'balance': balance,
            'days_without_activity': '',
        })

        for transaction in transactions.order_by('app_date'):
            debit = abs(transaction.amount) if transaction.amount < 0 else 0
            credit = transaction.amount if transaction.amount > 0 else 0
            balance += (credit - debit)

            total_debit += debit
            total_credit += credit

            days_without_activity = (
                (transaction.app_date - previous_transaction_date).days 
                if previous_transaction_date 
                else 0
            )

            statement_data.append({
                'branch': transaction.branch.branch_name,
                'ses_date': transaction.ses_date,
                'trx_date': transaction.app_date,
                'trx_no': transaction.trx_no,
                'description': transaction.description,
                'debit': f"-{debit:,}" if debit else '',
                'credit': f"{credit:,}" if credit else '',
                'balance': f"{balance:,}",
                'days_without_activity': days_without_activity
            })

            previous_transaction_date = transaction.app_date

        reporting_balance = balance

    context = {
        'branches': branches,
        'gl_nos': gl_nos,
        'statement_data': statement_data,
        'gl_no': gl_no,
        'ac_no': ac_no,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
        'branch': selected_branch,
        'company': selected_branch.company_name if selected_branch else None,
        'current_datetime': timezone.now(),
        'opening_balance': f"{opening_balance:,}",
        'closing_balance': f"{reporting_balance:,}",
        'total_debit': f"{total_debit:,}",
        'total_credit': f"{total_credit:,}",
        'reporting_balance': f"{reporting_balance:,}",
        'full_name': customer.get_full_name() if customer else '',
        'customer': customer,
    }

    return render(request, 'reports/savings_report/savings_account_statement.html', context)

    
from django.shortcuts import render, get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from customers.models import Customer
from transactions.models import Memtrans
from django.db.models import Sum, Q, Min
from company.models import Company
from datetime import datetime
from accounts_admin.models import Account, Region, Account_Officer
from company.models import Company



from datetime import timedelta

from django.utils import timezone





from django.utils import timezone

import pytz  # Optional: for timezone-aware datetime

from django.shortcuts import render
from django.db.models import Sum
# from .models import Customer, Memtrans, Branch, Region, Account_Officer, Account
from django.utils import timezone
import datetime





def all_customers_account_balances(request):
    customer_data = {}
    default_reporting_date = timezone.now().date()
    current_datetime = timezone.now()

    selected_branch = None
    selected_gl_no = None
    selected_region = None
    selected_officer = None
    reporting_date = default_reporting_date
    include_non_zero = False
    exclude_ac_no_one = False
    grand_total = 0

    user_branch = None
    if request.user.is_authenticated:
        try:
            user_branch = request.user.branch  # Assumes User has ForeignKey to Branch
        except AttributeError:
            pass

    branches = []
    regions = []
    account_officers = []
    gl_accounts = []

    customers = Customer.objects.none()
    if user_branch:
        branches = [user_branch]  # Only show current user's branch
        regions = Region.objects.filter(branch=user_branch)
        account_officers = Account_Officer.objects.filter(branch=user_branch)
        gl_accounts = Account.objects.filter(branch=user_branch).distinct('gl_no')
        customers = Customer.objects.filter(branch=user_branch)

    if request.method == 'POST':
        reporting_date_str = request.POST.get('reporting_date')
        branch_id = request.POST.get('branch')
        gl_no = request.POST.get('gl_no')
        region_id = request.POST.get('region')
        officer_id = request.POST.get('credit_officer')
        include_non_zero = request.POST.get('include_non_zero') == 'on'
        exclude_ac_no_one = request.POST.get('exclude_ac_no_one') == 'on'

        if reporting_date_str:
            reporting_date = datetime.datetime.strptime(reporting_date_str, '%Y-%m-%d').date()
        else:
            reporting_date = default_reporting_date

        filtered_customers = customers

        if branch_id:
            try:
                selected_branch = Branch.objects.get(id=branch_id)
                if selected_branch != user_branch:
                    raise PermissionDenied("You do not have access to this branch.")
                filtered_customers = filtered_customers.filter(branch=selected_branch)
            except Branch.DoesNotExist:
                selected_branch = None

        if gl_no:
            filtered_customers = filtered_customers.filter(gl_no=gl_no)
            selected_gl_no = gl_no

        if region_id:
            try:
                selected_region = Region.objects.get(id=region_id, branch=user_branch)
                filtered_customers = filtered_customers.filter(region=selected_region)
            except Region.DoesNotExist:
                selected_region = None

        if officer_id:
            try:
                selected_officer = Account_Officer.objects.get(id=officer_id, branch=user_branch)
                filtered_customers = filtered_customers.filter(credit_officer=selected_officer)
            except Account_Officer.DoesNotExist:
                selected_officer = None

        customer_dict = {}
        for customer in filtered_customers:
            if exclude_ac_no_one and customer.ac_no == '1':
                continue
            customer_dict[(customer.gl_no, customer.ac_no)] = customer

        transactions = Memtrans.objects.filter(
            app_date__lte=reporting_date,
            customer__branch=user_branch
        )
        if selected_branch:
            transactions = transactions.filter(branch=selected_branch)

        gl_map = {a.gl_no: a.gl_name for a in gl_accounts}

        for (gl_no, ac_no), customer in customer_dict.items():
            customer_transactions = transactions.filter(gl_no=gl_no, ac_no=ac_no)
            account_balance = customer_transactions.aggregate(total=Sum('amount'))['total'] or 0

            if include_non_zero and account_balance == 0:
                continue

            gl_name = gl_map.get(gl_no, 'Unknown Account')

            if gl_no not in customer_data:
                customer_data[gl_no] = {
                    'gl_name': gl_name,
                    'customers': [],
                    'subtotal': 0,
                    'count': 0
                }

            customer_data[gl_no]['customers'].append({
                'first_name': customer.first_name,
                'middle_name': customer.middle_name,
                'last_name': customer.last_name,
                'address': customer.address,
                'account_balance': account_balance,
                'gl_name': gl_name,
            })

            customer_data[gl_no]['subtotal'] += account_balance
            customer_data[gl_no]['count'] += 1
            grand_total += account_balance

    company = user_branch.company_name if user_branch else "No Company Assigned"
    username = request.user.username if request.user.is_authenticated else None

    context = {
        'branches': branches,
        'regions': regions,
        'account_officers': account_officers,
        'gl_accounts': gl_accounts,
        'customer_data': customer_data,
        'selected_branch': selected_branch,
        'selected_gl_no': selected_gl_no,
        'selected_region': selected_region,
        'selected_officer': selected_officer,
        'reporting_date': reporting_date,
        'include_non_zero': include_non_zero,
        'exclude_ac_no_one': exclude_ac_no_one,
        'grand_total': grand_total,
        'current_datetime': current_datetime,
        'company': company,
        'username': username,
        'user': request.user,
    }

    return render(request, 'reports/savings_report/savings_account_balance_report.html', context)

def savings_transaction_report(request):
    user = request.user

    # Get the user's branch/company_name
    user_branch = user.branches.first()
    if not user_branch:
        return render(request, 'error.html', {'message': 'User has no branch assigned.'})
    user_company_name = user_branch.company_name

    try:
        # Initialize filter options - filtered by company_name
        branches = Branch.objects.filter(company_name=user_company_name).order_by('branch_name')
        regions = Region.objects.filter(branch__company_name=user_company_name)
        account_officers = Account_Officer.objects.filter(region__branch__company_name=user_company_name)
        gl_accounts = Account.objects.filter(
            gl_no__in=Customer.objects.filter(branch__company_name=user_company_name).values('gl_no').distinct(),
            branch__company_name=user_company_name
        )
        current_datetime = timezone.now()
        
        # Default values
        transaction_data = {}
        default_start_date = timezone.now().date()
        default_end_date = timezone.now().date()
        form_data = {
            'selected_branch': None,
            'selected_gl_no': None,
            'selected_region': None,
            'selected_officer': None,
            'start_date': default_start_date,
            'end_date': default_end_date,
            'include_non_zero': False,
            'exclude_ac_no_one': False,
        }
        grand_total_debit = 0
        grand_total_credit = 0

        if request.method == 'POST':
            # Process form data
            form_data['start_date'] = datetime.strptime(
                request.POST.get('start_date', ''),
                '%Y-%m-%d'
            ).date() if request.POST.get('start_date') else default_start_date
            
            form_data['end_date'] = datetime.strptime(
                request.POST.get('end_date', ''),
                '%Y-%m-%d'
            ).date() if request.POST.get('end_date') else default_end_date
            
            form_data['include_non_zero'] = request.POST.get('include_non_zero') == 'on'
            form_data['exclude_ac_no_one'] = request.POST.get('exclude_ac_no_one') == 'on'

            # Apply filters - start with company_name base filter
            customers = Customer.objects.filter(branch__company_name=user_company_name)
            
            # Branch filter
            if branch_id := request.POST.get('branch'):
                try:
                    branch = Branch.objects.get(id=branch_id, company_name=user_company_name)
                    customers = customers.filter(branch=branch.branch_code)
                    form_data['selected_branch'] = branch
                except Branch.DoesNotExist:
                    messages.warning(request, "Selected branch not found")
            
            # GL No filter
            if gl_no := request.POST.get('gl_no'):
                customers = customers.filter(gl_no=gl_no)
                form_data['selected_gl_no'] = gl_no
            
            # Region filter
            if region_id := request.POST.get('region'):
                try:
                    region = Region.objects.get(id=region_id, branch__company_name=user_company_name)
                    branch_codes = Branch.objects.filter(region=region, company_name=user_company_name).values_list('branch_code', flat=True)
                    customers = customers.filter(branch__in=branch_codes)
                    form_data['selected_region'] = region
                except Region.DoesNotExist:
                    messages.warning(request, "Selected region not found")

            # Account Officer filter
            if officer_id := request.POST.get('credit_officer'):
                try:
                    officer = Account_Officer.objects.get(id=officer_id, region__branch__company_name=user_company_name)
                    branch_codes = Branch.objects.filter(account_officer=officer, company_name=user_company_name).values_list('branch_code', flat=True)
                    customers = customers.filter(branch__in=branch_codes)
                    form_data['selected_officer'] = officer
                except Account_Officer.DoesNotExist:
                    messages.warning(request, "Selected account officer not found")
            
            # Process transactions
            gl_name_dict = dict(Account.objects.filter(branch__company_name=user_company_name).values_list('gl_no', 'gl_name'))
            
            # Create customer dictionary for quick lookup
            customer_dict = {
                (c.gl_no, c.ac_no): c for c in customers 
                if not (form_data['exclude_ac_no_one'] and c.ac_no == '1')
            }
            
            # Get transactions in date range for the company
            transactions = Memtrans.objects.filter(
                app_date__gte=form_data['start_date'],
                app_date__lte=form_data['end_date'],
                branch__company_name=user_company_name
            )
            
            if form_data['selected_branch']:
                transactions = transactions.filter(branch=form_data['selected_branch'].branch_code)
            
            # Process transactions by customer
            for (gl_no, ac_no), customer in customer_dict.items():
                cust_transactions = transactions.filter(gl_no=gl_no, ac_no=ac_no)
                
                if not form_data['include_non_zero']:
                    cust_transactions = cust_transactions.exclude(amount=0)
                
                if not cust_transactions.exists():
                    continue
                
                if gl_no not in transaction_data:
                    transaction_data[gl_no] = {
                        'gl_name': gl_name_dict.get(gl_no, 'Unknown'),
                        'transactions': [],
                        'subtotal_debit': 0,
                        'subtotal_credit': 0,
                        'count': 0
                    }
                
                for trx in cust_transactions:
                    debit = abs(trx.amount) if trx.amount < 0 else 0
                    credit = trx.amount if trx.amount > 0 else 0
                    
                    transaction_data[gl_no]['transactions'].append({
                        'trx_no': trx.trx_no,
                        'ses_date': trx.ses_date,
                        'app_date': trx.app_date,
                        'description': trx.description,
                        'debit': debit,
                        'credit': credit,
                        'ac_no': customer.ac_no,
                        'customer_name': f"{customer.first_name} {customer.last_name}"
                    })
                    
                    transaction_data[gl_no]['subtotal_debit'] += debit
                    transaction_data[gl_no]['subtotal_credit'] += credit
                    transaction_data[gl_no]['count'] += 1
                    
                    grand_total_debit += debit
                    grand_total_credit += credit

            # Redirect if no transactions found
            if not transaction_data:
                messages.info(request, "No transactions found matching your criteria")
                return redirect('savings_transaction_report')

        context = {
            'branches': branches,
            'regions': regions,
            'account_officers': account_officers,
            'gl_accounts': gl_accounts,
            'transaction_data': transaction_data,
            'grand_total_debit': grand_total_debit,
            'grand_total_credit': grand_total_credit,
            'current_datetime': current_datetime,
            'user_company_name': user_company_name,
            **form_data
        }

        return render(request, 'reports/savings_report/savings_transactions_report.html', context)

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in savings_transaction_report: {str(e)}", exc_info=True)
        
        # Return to form with error message and maintain filter options
        messages.error(request, f"An error occurred while generating the transaction report: {str(e)}")
        return render(request, 'reports/savings_report/savings_transactions_report.html', {
            'branches': Branch.objects.filter(company_name=user_company_name).order_by('branch_name'),
            'regions': Region.objects.filter(branch__company_name=user_company_name),
            'account_officers': Account_Officer.objects.filter(region__branch__company_name=user_company_name),
            'gl_accounts': Account.objects.filter(
                gl_no__in=Customer.objects.filter(branch__company_name=user_company_name).values('gl_no').distinct(),
                branch__company_name=user_company_name
            ),
            'current_datetime': timezone.now(),
            'user_company_name': user_company_name,
        })

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in savings_transaction_report: {str(e)}", exc_info=True)
        
        # Return to form with error message
        messages.error(request, f"An error occurred while generating the transaction report: {str(e)}")
        return render(request, 'reports/savings_report/savings_transactions_report.html', {
            'branches': Branch.objects.all().order_by('branch_name'),
            'regions': Region.objects.all(),
            'account_officers': Account_Officer.objects.all(),
            'gl_accounts': Account.objects.filter(gl_no__in=Customer.objects.values('gl_no').distinct()),
            'current_datetime': timezone.now(),
        })



from datetime import datetime
from django.db.models import Min, Max



from datetime import timedelta
from django.db.models import Sum



from django.db.models import Sum, Max
from django.shortcuts import render
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Max
from django.shortcuts import render
from django.utils import timezone
from datetime import datetime, timedelta



def savings_account_listing(request):
    # Initialize variables
    start_date = end_date = None
    selected_branch = selected_gl_no = selected_region = selected_officer = None
    include_non_zero = exclude_ac_no_one = False
    customer_data = {}
    grand_total = 0

    # Get user's company
    user_branch = request.user.branches.first()
    user_company_name = user_branch.company_name if user_branch else None

    # Default dates
    default_end_date = timezone.now().date()
    default_start_date = default_end_date

    if request.method == "POST":
        # Get form data
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        branch_id = request.POST.get('branch')
        selected_gl_no = request.POST.get('gl_no')
        region_id = request.POST.get('region')
        officer_id = request.POST.get('credit_officer')
        include_non_zero = request.POST.get('include_non_zero') == 'on'
        exclude_ac_no_one = request.POST.get('exclude_ac_no_one') == 'on'

        # Convert dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else default_start_date
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else default_end_date

        # Filter customers
        customers = Customer.objects.filter(branch__company_name=user_company_name)
        
        if branch_id:
            selected_branch = Branch.objects.filter(company_name=user_company_name, id=branch_id).first()
            customers = customers.filter(branch=selected_branch)

        if selected_gl_no:
            customers = customers.filter(gl_no=selected_gl_no)

        if region_id:
            selected_region = Region.objects.filter(id=region_id).first()
            customers = customers.filter(region=selected_region)

        if officer_id:
            selected_officer = Account_Officer.objects.filter(id=officer_id).first()
            customers = customers.filter(credit_officer=selected_officer)

        # Create customer dictionary
        customer_dict = {}
        for customer in customers:
            if exclude_ac_no_one and customer.ac_no == '1':
                continue
            customer_dict[(customer.gl_no, customer.ac_no)] = customer

        # Filter transactions
        transactions = Memtrans.objects.filter(
            branch__company_name=user_company_name,
            app_date__gte=start_date,
            app_date__lte=end_date
        )
        if branch_id and selected_branch:
            transactions = transactions.filter(branch=selected_branch)

        # Process customer data
        for (gl_no, ac_no), customer in customer_dict.items():
            customer_transactions = transactions.filter(gl_no=gl_no, ac_no=ac_no)
            total_balance = customer_transactions.aggregate(total=Sum('amount'))['total'] or 0

            if include_non_zero and total_balance == 0:
                continue

            if gl_no not in customer_data:
                customer_data[gl_no] = {
                    'gl_name': Account.objects.filter(gl_no=gl_no).first().gl_name if Account.objects.filter(gl_no=gl_no).exists() else 'Unknown',
                    'customers': [],
                    'subtotal': 0,
                    'count': 0
                }

            last_trx_date = customer_transactions.aggregate(latest_date=Max('app_date'))['latest_date']
            trx_dates = customer_transactions.values_list('sys_date', flat=True).distinct()

            days_without_activity = sum(
                1 for current_date in (
                    start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)
                if current_date not in {trx_date.date() for trx_date in trx_dates}
            ))

            customer_info = {
                'gl_no': gl_no,
                'first_name': customer.first_name,
                'middle_name': customer.middle_name,
                'last_name': customer.last_name,
                'address': customer.address,
                'account_balance': total_balance,
                'last_trx_date': last_trx_date,
                'days_without_activity': days_without_activity,
            }
            
            customer_data[gl_no]['customers'].append(customer_info)
            customer_data[gl_no]['subtotal'] += total_balance
            customer_data[gl_no]['count'] += 1
            grand_total += total_balance

    # Prepare dropdown data
    gl_accounts = Account.objects.filter(
        branch__company_name=user_company_name,
        gl_no__isnull=False
    ).exclude(gl_no='').order_by('gl_no').distinct()

    branches = Branch.objects.filter(company_name=user_company_name)
    regions = Region.objects.filter(branch__company_name=user_company_name)
    account_officers = Account_Officer.objects.filter(branch__company_name=user_company_name)

    context = {
        'customer_data': customer_data,
        'start_date': start_date,
        'end_date': end_date,
        'selected_branch': selected_branch,
        'selected_gl_no': selected_gl_no,
        'selected_region': selected_region,
        'selected_officer': selected_officer,
        'include_non_zero': include_non_zero,
        'exclude_ac_no_one': exclude_ac_no_one,
        'branches': branches,
        'gl_accounts': gl_accounts,
        'regions': regions,
        'account_officers': account_officers,
        'grand_total': grand_total,
        'current_datetime': timezone.now(),
        'company': selected_branch.company if selected_branch else user_branch.company if user_branch else None,
    }

    return render(request, 'reports/savings_report/savings_account_listing.html', context)




@login_required
def savings_account_status(request):
    user = request.user

    # Get the user's branch/company_name
    user_branch = user.branches.first()
    if not user_branch:
        return render(request, 'error.html', {'message': 'User has no branch assigned.'})
    user_company_name = user_branch.company_name

    # Get all branches for the company
    branches = Branch.objects.filter(company_name=user_company_name)
    
    # Filter all data by branch__company_name = user's company_name
    gl_accounts = Account.objects.filter(branch__company_name=user_company_name)
    customers = Customer.objects.filter(branch__company_name=user_company_name)
    memtrans = Memtrans.objects.filter(branch__company_name=user_company_name)
    regions = Region.objects.filter(branch__company_name=user_company_name)
    account_officers = Account_Officer.objects.filter(region__branch__company_name=user_company_name)

    # Optional filters from GET params
    branch_filter = request.GET.get('branch')
    region_filter = request.GET.get('region')
    officer_filter = request.GET.get('account_officer')

    if branch_filter:
        branches = branches.filter(branch_code=branch_filter)  # Add branch filtering
        gl_accounts = gl_accounts.filter(branch__branch_code=branch_filter)
        customers = customers.filter(branch__branch_code=branch_filter)
        memtrans = memtrans.filter(branch__branch_code=branch_filter)
        regions = regions.filter(branch__branch_code=branch_filter)
        account_officers = account_officers.filter(region__branch__branch_code=branch_filter)

    if region_filter:
        account_officers = account_officers.filter(region_id=region_filter)
        customers = customers.filter(region_id=region_filter)

    if officer_filter:
        customers = customers.filter(account_officer_id=officer_filter)

    # Prepare customer data
    customer_data = []
    for cust in customers:
        balance = memtrans.filter(ac_no=cust.ac_no).aggregate(total_balance=Sum('amount'))['total_balance'] or 0
        last_trx = memtrans.filter(ac_no=cust.ac_no).aggregate(last_date=Max('sys_date'))['last_date']
        days_without_activity = (now().date() - last_trx).days if last_trx else None

        customer_data.append({
            'customer': cust,
            'balance': balance,
            'last_transaction_date': last_trx,
            'days_without_activity': days_without_activity,
            'reg_date': cust.reg_date,
        })

    context = {
        'branches': branches,  # Add branches to context
        'gl_accounts': gl_accounts,
        'regions': regions,
        'account_officers': account_officers,
        'customer_data': customer_data,
        'user_company_name': user_company_name,
    }

    return render(request, 'reports/savings_report/savings_account_status.html', context)




from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import datetime
from django.db.models import Min, Max, Sum
from django.contrib import messages

def savings_account_with_zero_balance(request):
    user = request.user

    # Get the user's branch/company_name
    user_branch = user.branches.first()
    if not user_branch:
        return render(request, 'error.html', {'message': 'User has no branch assigned.'})
    user_company_name = user_branch.company_name

    # Initialize filter options - filtered by company_name
    branches = Branch.objects.filter(company_name=user_company_name)
    regions = Region.objects.filter(branch__company_name=user_company_name)
    account_officers = Account_Officer.objects.filter(region__branch__company_name=user_company_name)
    gl_accounts = Account.objects.filter(
        gl_no__in=Customer.objects.filter(branch__company_name=user_company_name).values('gl_no').distinct(),
        branch__company_name=user_company_name
    )
    current_datetime = timezone.now()
    
    try:
        # Default values
        customer_data = {}
        default_reporting_date = timezone.now().date()
        form_data = {
            'selected_branch': None,
            'selected_gl_no': None,
            'selected_region': None,
            'selected_officer': None,
            'reporting_date': default_reporting_date,
            'exclude_ac_no_one': False,
        }
        grand_total = 0

        if request.method == 'POST':
            # Process form data
            reporting_date_str = request.POST.get('reporting_date')
            form_data['reporting_date'] = datetime.strptime(
                reporting_date_str, '%Y-%m-%d'
            ).date() if reporting_date_str else default_reporting_date
            
            form_data['exclude_ac_no_one'] = request.POST.get('exclude_ac_no_one') == 'on'

            # Apply filters - start with company_name base filter
            customers = Customer.objects.filter(branch__company_name=user_company_name)
            
            # Branch filter
            if branch_id := request.POST.get('branch'):
                try:
                    branch = Branch.objects.get(id=branch_id, company_name=user_company_name)
                    customers = customers.filter(branch=branch.branch_code)
                    form_data['selected_branch'] = branch
                except Branch.DoesNotExist:
                    messages.warning(request, "Selected branch not found")
            
            # GL No filter
            if gl_no := request.POST.get('gl_no'):
                customers = customers.filter(gl_no=gl_no)
                form_data['selected_gl_no'] = gl_no
            
            # Region filter
            if region_id := request.POST.get('region'):
                try:
                    region = Region.objects.get(id=region_id, branch__company_name=user_company_name)
                    branch_codes = Branch.objects.filter(region=region, company_name=user_company_name).values_list('branch_code', flat=True)
                    customers = customers.filter(branch__in=branch_codes)
                    form_data['selected_region'] = region
                except Region.DoesNotExist:
                    messages.warning(request, "Selected region not found")

            # Account Officer filter
            if officer_id := request.POST.get('credit_officer'):
                try:
                    officer = Account_Officer.objects.get(id=officer_id, region__branch__company_name=user_company_name)
                    branch_codes = Branch.objects.filter(account_officer=officer, company_name=user_company_name).values_list('branch_code', flat=True)
                    customers = customers.filter(branch__in=branch_codes)
                    form_data['selected_officer'] = officer
                except Account_Officer.DoesNotExist:
                    messages.warning(request, "Selected account officer not found")
            
            # Process customers with zero balance
            gl_name_dict = dict(Account.objects.filter(branch__company_name=user_company_name).values_list('gl_no', 'gl_name'))
            
            for customer in customers:
                if form_data['exclude_ac_no_one'] and customer.ac_no == '1':
                    continue

                transactions = Memtrans.objects.filter(
                    gl_no=customer.gl_no,
                    ac_no=customer.ac_no,
                    app_date__lte=form_data['reporting_date'],
                    branch__company_name=user_company_name
                )
                
                # Get balance and transaction dates
                account_balance = transactions.aggregate(total=Sum('amount'))['total'] or 0
                if account_balance != 0:  # Skip non-zero balance accounts
                    continue
                    
                last_transaction_date = transactions.aggregate(max_date=Max('app_date'))['max_date'] or form_data['reporting_date']
                days_inactive = (form_data['reporting_date'] - last_transaction_date).days

                # Organize data by GL account
                if customer.gl_no not in customer_data:
                    customer_data[customer.gl_no] = {
                        'gl_name': gl_name_dict.get(customer.gl_no, 'Unknown'),
                        'customers': [],
                        'subtotal': 0,
                        'count': 0
                    }

                customer_data[customer.gl_no]['customers'].append({
                    'gl_no': customer.gl_no,
                    'ac_no': customer.ac_no,
                    'first_name': customer.first_name,
                    'middle_name': customer.middle_name,
                    'last_name': customer.last_name,
                    'address': customer.address,
                    'account_balance': account_balance,
                    'last_trx_date': last_transaction_date,
                    'days_without_activity': days_inactive,
                })

                customer_data[customer.gl_no]['subtotal'] += account_balance
                customer_data[customer.gl_no]['count'] += 1
                grand_total += account_balance

        context = {
            'branches': branches,
            'regions': regions,
            'account_officers': account_officers,
            'gl_accounts': gl_accounts,
            'customer_data': customer_data,
            'grand_total': grand_total,
            'current_datetime': current_datetime,
            'user_company_name': user_company_name,  # Added company name to context
            **form_data
        }

        return render(request, 'reports/savings_report/savings_zero_balance_report.html', context)

    except Exception as e:
        # Log the error (you should configure proper logging in your project)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in savings_account_with_zero_balance: {str(e)}", exc_info=True)
        
        # Return to form with error message
        messages.error(request, f"An error occurred while generating the report: {str(e)}")
        return redirect('savings_account_with_zero_balance')  # Make sure this matches your URL name



from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import datetime
from django.db.models import Sum, Max
from django.contrib import messages
import logging


def savings_account_overdrawn(request):
    # Initialize filter options (available even if exception occurs)
    try:
        branches = Branch.objects.all().order_by('branch_name')  # Ordered by name
        regions = Region.objects.all()
        account_officers = Account_Officer.objects.all()
        gl_accounts = Account.objects.filter(
            gl_no__in=Customer.objects.values('gl_no').distinct()
        )
        current_datetime = timezone.now()
        
        # Default values
        customer_data = {}
        default_reporting_date = timezone.now().date()
        form_data = {
            'selected_branch': None,
            'selected_gl_no': None,
            'selected_region': None,
            'selected_officer': None,
            'reporting_date': default_reporting_date,
            'exclude_ac_no_one': False,
        }
        grand_total = 0

        if request.method == 'POST':
            # Process form data
            reporting_date_str = request.POST.get('reporting_date')
            form_data['reporting_date'] = datetime.strptime(
                reporting_date_str, '%Y-%m-%d'
            ).date() if reporting_date_str else default_reporting_date
            
            form_data['exclude_ac_no_one'] = request.POST.get('exclude_ac_no_one') == 'on'

            # Apply filters
            customers = Customer.objects.all()
            
            # Branch filter
            if branch_id := request.POST.get('branch'):
                try:
                    branch = Branch.objects.get(id=branch_id)
                    customers = customers.filter(branch=branch.branch_code)
                    form_data['selected_branch'] = branch
                except Branch.DoesNotExist:
                    messages.warning(request, "Selected branch not found")
            
            # GL No filter
            if gl_no := request.POST.get('gl_no'):
                customers = customers.filter(gl_no=gl_no)
                form_data['selected_gl_no'] = gl_no
            
            # Region filter
            if region_id := request.POST.get('region'):
                try:
                    region = Region.objects.get(id=region_id)
                    branch_codes = Branch.objects.filter(region=region).values_list('branch_code', flat=True)
                    customers = customers.filter(branch__in=branch_codes)
                    form_data['selected_region'] = region
                except Region.DoesNotExist:
                    messages.warning(request, "Selected region not found")

            # Account Officer filter
            if officer_id := request.POST.get('credit_officer'):
                try:
                    officer = Account_Officer.objects.get(id=officer_id)
                    branch_codes = Branch.objects.filter(account_officer=officer).values_list('branch_code', flat=True)
                    customers = customers.filter(branch__in=branch_codes)
                    form_data['selected_officer'] = officer
                except Account_Officer.DoesNotExist:
                    messages.warning(request, "Selected account officer not found")
            
            # Process overdrawn accounts
            gl_name_dict = dict(Account.objects.values_list('gl_no', 'gl_name'))
            
            for customer in customers:
                if form_data['exclude_ac_no_one'] and customer.ac_no == '1':
                    continue

                transactions = Memtrans.objects.filter(
                    gl_no=customer.gl_no,
                    ac_no=customer.ac_no,
                    app_date__lte=form_data['reporting_date']
                )
                
                # Get balance and last transaction date
                account_balance = transactions.aggregate(total=Sum('amount'))['total'] or 0
                
                # Skip accounts with balance >= 0 (not overdrawn)
                if account_balance >= 0:
                    continue
                    
                # Get last transaction date
                last_transaction = Memtrans.objects.filter(
                    ac_no=customer.ac_no
                ).order_by('-ses_date').first()
                last_trx_date = last_transaction.ses_date if last_transaction else None

                # Organize data by GL account
                if customer.gl_no not in customer_data:
                    customer_data[customer.gl_no] = {
                        'gl_name': gl_name_dict.get(customer.gl_no, 'Unknown'),
                        'customers': [],
                        'subtotal': 0,
                        'count': 0
                    }

                customer_data[customer.gl_no]['customers'].append({
                    'gl_no': customer.gl_no,
                    'ac_no': customer.ac_no,
                    'first_name': customer.first_name,
                    'middle_name': customer.middle_name,
                    'last_name': customer.last_name,
                    'address': customer.address,
                    'account_balance': account_balance,
                    'last_trx_date': last_trx_date,
                })

                customer_data[customer.gl_no]['subtotal'] += account_balance
                customer_data[customer.gl_no]['count'] += 1
                grand_total += account_balance

        context = {
            'branches': branches,
            'regions': regions,
            'account_officers': account_officers,
            'gl_accounts': gl_accounts,
            'customer_data': customer_data,
            'grand_total': grand_total,
            'current_datetime': current_datetime,
            **form_data
        }

        return render(request, 'reports/savings_report/savings_overdrawn_account_status.html', context)

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in savings_account_overdrawn: {str(e)}", exc_info=True)
        
        # Return to form with error message and maintain branch list
        branches = Branch.objects.all().order_by('branch_name')
        messages.error(request, f"An error occurred: {str(e)}")
        return render(request, 'reports/savings_report/savings_overdrawn_account_status.html', {
            'branches': branches,
            'regions': Region.objects.all(),
            'account_officers': Account_Officer.objects.all(),
            'gl_accounts': Account.objects.filter(gl_no__in=Customer.objects.values('gl_no').distinct()),
            'current_datetime': timezone.now(),
        })


def savings_interest_paid(request):
    user = request.user

    # Get the user's branch/company_name
    user_branch = user.branches.first()
    if not user_branch:
        return render(request, 'error.html', {'message': 'User has no branch assigned.'})
    user_company_name = user_branch.company_name

    try:
        # Initialize filter options - filtered by company_name
        branches = Branch.objects.filter(company_name=user_company_name).order_by('branch_name')
        regions = Region.objects.filter(branch__company_name=user_company_name)
        account_officers = Account_Officer.objects.filter(region__branch__company_name=user_company_name)
        gl_accounts = Account.objects.filter(
            gl_no__in=Customer.objects.filter(branch__company_name=user_company_name).values('gl_no').distinct(),
            branch__company_name=user_company_name
        )
        current_datetime = timezone.now()
        
        # Default values
        customer_data = {}
        default_reporting_date = timezone.now().date()
        form_data = {
            'selected_branch': None,
            'selected_gl_no': None,
            'selected_region': None,
            'selected_officer': None,
            'reporting_date': default_reporting_date,
            'exclude_ac_no_one': False,
        }
        grand_total = 0

        if request.method == 'POST':
            # Process form data
            reporting_date_str = request.POST.get('reporting_date')
            form_data['reporting_date'] = datetime.strptime(
                reporting_date_str, '%Y-%m-%d'
            ).date() if reporting_date_str else default_reporting_date
            
            form_data['exclude_ac_no_one'] = request.POST.get('exclude_ac_no_one') == 'on'

            # Apply filters - start with company_name base filter
            customers = Customer.objects.filter(branch__company_name=user_company_name)
            
            # Branch filter
            if branch_id := request.POST.get('branch'):
                try:
                    branch = Branch.objects.get(id=branch_id, company_name=user_company_name)
                    customers = customers.filter(branch=branch.branch_code)
                    form_data['selected_branch'] = branch
                except Branch.DoesNotExist:
                    messages.warning(request, "Selected branch not found")
            
            # GL No filter
            if gl_no := request.POST.get('gl_no'):
                customers = customers.filter(gl_no=gl_no)
                form_data['selected_gl_no'] = gl_no
            
            # Region filter
            if region_id := request.POST.get('region'):
                try:
                    region = Region.objects.get(id=region_id, branch__company_name=user_company_name)
                    branch_codes = Branch.objects.filter(region=region, company_name=user_company_name).values_list('branch_code', flat=True)
                    customers = customers.filter(branch__in=branch_codes)
                    form_data['selected_region'] = region
                except Region.DoesNotExist:
                    messages.warning(request, "Selected region not found")

            # Account Officer filter
            if officer_id := request.POST.get('credit_officer'):
                try:
                    officer = Account_Officer.objects.get(id=officer_id, region__branch__company_name=user_company_name)
                    branch_codes = Branch.objects.filter(account_officer=officer, company_name=user_company_name).values_list('branch_code', flat=True)
                    customers = customers.filter(branch__in=branch_codes)
                    form_data['selected_officer'] = officer
                except Account_Officer.DoesNotExist:
                    messages.warning(request, "Selected account officer not found")
            
            # Process interest payments (transactions with code 'MSI')
            gl_name_dict = dict(Account.objects.filter(branch__company_name=user_company_name).values_list('gl_no', 'gl_name'))
            
            for customer in customers:
                if form_data['exclude_ac_no_one'] and customer.ac_no == '1':
                    continue

                # Get all MSI transactions for this customer
                transactions = Memtrans.objects.filter(
                    gl_no=customer.gl_no,
                    ac_no=customer.ac_no,
                    code='MSI',  # Interest payment transactions
                    app_date__lte=form_data['reporting_date'],
                    branch__company_name=user_company_name
                )
                
                # Calculate total interest paid
                interest_paid = transactions.aggregate(total=Sum('amount'))['total'] or 0
                
                # Skip accounts with no interest payments
                if interest_paid == 0:
                    continue
                    
                # Get last interest payment date
                last_transaction = transactions.order_by('-ses_date').first()
                last_trx_date = last_transaction.ses_date if last_transaction else None
                days_since_last = (form_data['reporting_date'] - last_trx_date).days if last_trx_date else None

                # Organize data by GL account
                if customer.gl_no not in customer_data:
                    customer_data[customer.gl_no] = {
                        'gl_name': gl_name_dict.get(customer.gl_no, 'Unknown'),
                        'customers': [],
                        'subtotal': 0,
                        'count': 0
                    }

                customer_data[customer.gl_no]['customers'].append({
                    'gl_no': customer.gl_no,
                    'ac_no': customer.ac_no,
                    'first_name': customer.first_name,
                    'middle_name': customer.middle_name,
                    'last_name': customer.last_name,
                    'address': customer.address,
                    'interest_paid': interest_paid,
                    'last_interest_date': last_trx_date,
                    'days_since_last_interest': days_since_last,
                })

                customer_data[customer.gl_no]['subtotal'] += interest_paid
                customer_data[customer.gl_no]['count'] += 1
                grand_total += interest_paid

        context = {
            'branches': branches,
            'regions': regions,
            'account_officers': account_officers,
            'gl_accounts': gl_accounts,
            'customer_data': customer_data,
            'grand_total': grand_total,
            'current_datetime': current_datetime,
            'user_company_name': user_company_name,
            **form_data
        }

        return render(request, 'reports/savings_report/savings_interest_paid.html', context)

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in savings_interest_paid: {str(e)}", exc_info=True)
        
        # Return to form with error message and maintain filter options
        messages.error(request, f"An error occurred while generating the interest paid report: {str(e)}")
        return render(request, 'reports/savings_report/savings_interest_paid.html', {
            'branches': Branch.objects.filter(company_name=user_company_name).order_by('branch_name'),
            'regions': Region.objects.filter(branch__company_name=user_company_name),
            'account_officers': Account_Officer.objects.filter(region__branch__company_name=user_company_name),
            'gl_accounts': Account.objects.filter(
                gl_no__in=Customer.objects.filter(branch__company_name=user_company_name).values('gl_no').distinct(),
                branch__company_name=user_company_name
            ),
            'current_datetime': timezone.now(),
            'user_company_name': user_company_name,
        })


def savings_account_credit_balance(request):
    user = request.user

    # Get the user's branch/company_name
    user_branch = user.branches.first()
    if not user_branch:
        return render(request, 'error.html', {'message': 'User has no branch assigned.'})
    user_company_name = user_branch.company_name

    try:
        # Initialize filter options - filtered by company_name
        branches = Branch.objects.filter(company_name=user_company_name).order_by('branch_name')
        regions = Region.objects.filter(branch__company_name=user_company_name)
        account_officers = Account_Officer.objects.filter(region__branch__company_name=user_company_name)
        gl_accounts = Account.objects.filter(
            gl_no__in=Customer.objects.filter(branch__company_name=user_company_name).values('gl_no').distinct(),
            branch__company_name=user_company_name
        )
        current_datetime = timezone.now()
        
        # Default values
        customer_data = {}
        default_reporting_date = timezone.now().date()
        form_data = {
            'selected_branch': None,
            'selected_gl_no': None,
            'selected_region': None,
            'selected_officer': None,
            'reporting_date': default_reporting_date,
            'exclude_ac_no_one': False,
        }
        grand_total = 0

        if request.method == 'POST':
            # Process form data
            reporting_date_str = request.POST.get('reporting_date')
            form_data['reporting_date'] = datetime.strptime(
                reporting_date_str, '%Y-%m-%d'
            ).date() if reporting_date_str else default_reporting_date
            
            form_data['exclude_ac_no_one'] = request.POST.get('exclude_ac_no_one') == 'on'

            # Apply filters - start with company_name base filter
            customers = Customer.objects.filter(branch__company_name=user_company_name)
            
            # Branch filter
            if branch_id := request.POST.get('branch'):
                try:
                    branch = Branch.objects.get(id=branch_id, company_name=user_company_name)
                    customers = customers.filter(branch=branch.branch_code)
                    form_data['selected_branch'] = branch
                except Branch.DoesNotExist:
                    messages.warning(request, "Selected branch not found")
            
            # GL No filter
            if gl_no := request.POST.get('gl_no'):
                customers = customers.filter(gl_no=gl_no)
                form_data['selected_gl_no'] = gl_no
            
            # Region filter
            if region_id := request.POST.get('region'):
                try:
                    region = Region.objects.get(id=region_id, branch__company_name=user_company_name)
                    branch_codes = Branch.objects.filter(region=region, company_name=user_company_name).values_list('branch_code', flat=True)
                    customers = customers.filter(branch__in=branch_codes)
                    form_data['selected_region'] = region
                except Region.DoesNotExist:
                    messages.warning(request, "Selected region not found")

            # Account Officer filter
            if officer_id := request.POST.get('credit_officer'):
                try:
                    officer = Account_Officer.objects.get(id=officer_id, region__branch__company_name=user_company_name)
                    branch_codes = Branch.objects.filter(account_officer=officer, company_name=user_company_name).values_list('branch_code', flat=True)
                    customers = customers.filter(branch__in=branch_codes)
                    form_data['selected_officer'] = officer
                except Account_Officer.DoesNotExist:
                    messages.warning(request, "Selected account officer not found")
            
            # Process accounts with credit balance (> 0)
            gl_name_dict = dict(Account.objects.filter(branch__company_name=user_company_name).values_list('gl_no', 'gl_name'))
            
            for customer in customers:
                if form_data['exclude_ac_no_one'] and customer.ac_no == '1':
                    continue

                transactions = Memtrans.objects.filter(
                    gl_no=customer.gl_no,
                    ac_no=customer.ac_no,
                    app_date__lte=form_data['reporting_date'],
                    branch__company_name=user_company_name
                )
                
                # Calculate account balance
                account_balance = transactions.aggregate(total=Sum('amount'))['total'] or 0
                
                # Skip accounts with balance <= 0 (only show credit balances)
                if account_balance <= 0:
                    continue
                    
                # Get last transaction date
                last_transaction = transactions.order_by('-ses_date').first()
                last_trx_date = last_transaction.ses_date if last_transaction else None

                # Organize data by GL account
                if customer.gl_no not in customer_data:
                    customer_data[customer.gl_no] = {
                        'gl_name': gl_name_dict.get(customer.gl_no, 'Unknown'),
                        'customers': [],
                        'subtotal': 0,
                        'count': 0
                    }

                customer_data[customer.gl_no]['customers'].append({
                    'gl_no': customer.gl_no,
                    'ac_no': customer.ac_no,
                    'first_name': customer.first_name,
                    'middle_name': customer.middle_name,
                    'last_name': customer.last_name,
                    'address': customer.address,
                    'account_balance': account_balance,
                    'last_trx_date': last_trx_date,
                })

                customer_data[customer.gl_no]['subtotal'] += account_balance
                customer_data[customer.gl_no]['count'] += 1
                grand_total += account_balance

        context = {
            'branches': branches,
            'regions': regions,
            'account_officers': account_officers,
            'gl_accounts': gl_accounts,
            'customer_data': customer_data,
            'grand_total': grand_total,
            'current_datetime': current_datetime,
            'user_company_name': user_company_name,
            **form_data
        }

        return render(request, 'reports/savings_report/savings_account_with_credit_balance_report.html', context)

    except Exception as e:
        # Log the error
        logger = logging.getLogger(__name__)
        logger.error(f"Error in savings_account_credit_balance: {str(e)}", exc_info=True)
        
        # Return to form with error message and maintain company filtering
        messages.error(request, f"An error occurred while generating the credit balance report: {str(e)}")
        return render(request, 'reports/savings_report/savings_account_with_credit_balance_report.html', {
            'branches': Branch.objects.filter(company_name=user_company_name).order_by('branch_name'),
            'regions': Region.objects.filter(branch__company_name=user_company_name),
            'account_officers': Account_Officer.objects.filter(region__branch__company_name=user_company_name),
            'gl_accounts': Account.objects.filter(
                gl_no__in=Customer.objects.filter(branch__company_name=user_company_name).values('gl_no').distinct(),
                branch__company_name=user_company_name
            ),
            'current_datetime': timezone.now(),
            'user_company_name': user_company_name,
        })

def savings_overdrawn_account_status(request):
    user = request.user

    # Get the user's branch/company_name
    user_branch = user.branches.first()
    if not user_branch:
        return render(request, 'error.html', {'message': 'User has no branch assigned.'})
    user_company_name = user_branch.company_name

    # Initialize variables - filtered by company_name
    branches = Branch.objects.filter(company_name=user_company_name)  # Changed from Company to Branch
    regions = Region.objects.filter(branch__company_name=user_company_name)
    account_officers = Account_Officer.objects.filter(region__branch__company_name=user_company_name)
    gl_accounts = Account.objects.filter(
        gl_no__in=Customer.objects.filter(branch__company_name=user_company_name).values('gl_no').distinct(),
        branch__company_name=user_company_name
    )
    
    # Default reporting date is the current date
    default_reporting_date = timezone.now().date()
    current_datetime = timezone.now()
    
    # Initialize form selections
    selected_branch = None
    selected_gl_no = None
    selected_region = None
    selected_officer = None
    reporting_date = default_reporting_date
    exclude_ac_no_one = False
    grand_total = 0
    customer_data = {}

    if request.method == 'POST':
        # Get filters from the form
        reporting_date_str = request.POST.get('reporting_date')
        branch_id = request.POST.get('branch')
        gl_no = request.POST.get('gl_no')
        region_id = request.POST.get('region')
        officer_id = request.POST.get('credit_officer')
        exclude_ac_no_one = request.POST.get('exclude_ac_no_one') == 'on'

        if reporting_date_str:
            reporting_date = datetime.strptime(reporting_date_str, '%Y-%m-%d').date()
        else:
            reporting_date = default_reporting_date

        # Start with company_name base filter
        customers = Customer.objects.filter(branch__company_name=user_company_name)
        
        if branch_id:
            try:
                selected_branch = Branch.objects.get(id=branch_id, company_name=user_company_name)  # Changed to Branch
                customers = customers.filter(branch=selected_branch.branch_code)
            except Branch.DoesNotExist:
                messages.warning(request, "Selected branch not found")
        
        if gl_no:
            customers = customers.filter(gl_no=gl_no)
            selected_gl_no = gl_no
        
        if region_id:
            try:
                selected_region = Region.objects.get(id=region_id, branch__company_name=user_company_name)
                branch_codes = Branch.objects.filter(
                    region=selected_region, 
                    company_name=user_company_name
                ).values_list('branch_code', flat=True)
                customers = customers.filter(branch__in=branch_codes)
            except Region.DoesNotExist:
                messages.warning(request, "Selected region not found")

        if officer_id:
            try:
                selected_officer = Account_Officer.objects.get(
                    id=officer_id, 
                    region__branch__company_name=user_company_name
                )
                branch_codes = Branch.objects.filter(
                    account_officer=selected_officer,
                    company_name=user_company_name
                ).values_list('branch_code', flat=True)
                customers = customers.filter(branch__in=branch_codes)
            except Account_Officer.DoesNotExist:
                messages.warning(request, "Selected account officer not found")
        
        # Get GL names for the company
        gl_name_dict = dict(
            Account.objects.filter(branch__company_name=user_company_name)
            .values_list('gl_no', 'gl_name')
        )
        
        grand_total = 0
        for customer in customers:
            if exclude_ac_no_one and customer.ac_no == '1':
                continue

            transactions = Memtrans.objects.filter(
                gl_no=customer.gl_no,
                ac_no=customer.ac_no,
                branch__company_name=user_company_name
            )

            # Get the earliest transaction date for the account
            earliest_transaction_date = transactions.aggregate(min_date=Min('app_date'))['min_date']

            if not earliest_transaction_date:
                earliest_transaction_date = timezone.now().date()

            # Filter transactions up to the reporting date
            transactions = transactions.filter(app_date__lte=reporting_date)

            account_balance = transactions.aggregate(total=Sum('amount'))['total'] or 0

            # Only include accounts with a negative balance
            if account_balance >= 0:
                continue

            if customer.gl_no not in customer_data:
                customer_data[customer.gl_no] = {
                    'gl_name': gl_name_dict.get(customer.gl_no, 'Unknown'),
                    'customers': [],
                    'subtotal': 0,
                    'count': 0
                }

            customer_data[customer.gl_no]['customers'].append({
                'gl_no': customer.gl_no,
                'first_name': customer.first_name,
                'middle_name': customer.middle_name,
                'last_name': customer.last_name,
                'address': customer.address,
                'account_balance': account_balance,
            })

            customer_data[customer.gl_no]['subtotal'] += account_balance
            customer_data[customer.gl_no]['count'] += 1
            grand_total += account_balance

    context = {
        'branches': branches,
        'regions': regions,
        'account_officers': account_officers,
        'gl_accounts': gl_accounts,
        'customer_data': customer_data,
        'selected_branch': selected_branch,
        'selected_gl_no': selected_gl_no,
        'selected_region': selected_region,
        'selected_officer': selected_officer,
        'reporting_date': reporting_date,
        'exclude_ac_no_one': exclude_ac_no_one,
        'grand_total': grand_total,
        'current_datetime': current_datetime,
        'user_company_name': user_company_name,
    }

    return render(request, 'reports/savings_report/savings_overdrawn_account_status.html', context)




from django.shortcuts import render
from transactions.models import Memtrans
from accounts.models import Account
from company.models import Company
from datetime import datetime
from collections import defaultdict
from django.http import JsonResponse


from collections import defaultdict
from django.shortcuts import render, get_object_or_404

from .forms import TrialBalanceForm

def generate_balance_sheet(start_date, end_date, branch_code=None):
    """
    Generate balance sheet data for a given date range and optionally filter by branch.
    """
    # Query all relevant Memtrans entries for the given branch
    memtrans_entries = Memtrans.objects.filter(ses_date__range=[start_date, end_date], error='A')

    # Apply branch filtering only if a specific branch code is provided
    if branch_code:
        memtrans_entries = memtrans_entries.filter(branch=branch_code)

    # Initialize a dictionary to hold GL account balances
    gl_customer_balance = defaultdict(lambda: {'debit': 0, 'credit': 0, 'balance': 0})

    # Process each entry
    for entry in memtrans_entries:
        gl_no = entry.gl_no
        amount = entry.amount

        if entry.type == 'N':
            if amount < 0:
                gl_customer_balance[gl_no]['debit'] += abs(amount)
            else:
                gl_customer_balance[gl_no]['credit'] += amount
        else:
            if amount < 0:
                gl_customer_balance[gl_no]['credit'] += abs(amount)
            else:
                gl_customer_balance[gl_no]['debit'] += amount

    # Fetch all necessary accounts in a single query to improve performance
    accounts = Account.objects.filter(gl_no__in=gl_customer_balance.keys()).values('gl_no', 'gl_name')
    account_map = {account['gl_no']: account['gl_name'] for account in accounts}

    # Sort GL numbers and prepare balance sheet data
    sorted_keys = sorted(gl_customer_balance.keys())
    sorted_balance_sheet_data = []
    subtotal_4 = subtotal_5 = 0

    for gl_no in sorted_keys:
        if gl_no.startswith("4") or gl_no.startswith("5"):
            amount = gl_customer_balance[gl_no]['debit'] - gl_customer_balance[gl_no]['credit']
            if gl_no.startswith("4"):
                subtotal_4 += amount
            else:
                subtotal_5 += amount
        else:
            balance_data = gl_customer_balance[gl_no]
            debit = balance_data['debit']
            credit = balance_data['credit']
            balance = debit - credit
            gl_name = account_map.get(gl_no, '')  # Default to empty string if GL number not found
            balance_data.update({'gl_no': gl_no, 'gl_name': gl_name, 'balance': balance})
            sorted_balance_sheet_data.append(balance_data)

    # Calculate net income, total debit, credit, and balance
    net_income = subtotal_4 + subtotal_5
    total_debit = sum(entry['debit'] for entry in sorted_balance_sheet_data)
    total_credit = sum(entry['credit'] for entry in sorted_balance_sheet_data)
    total_balance = total_credit - total_debit

    return sorted_balance_sheet_data, subtotal_4, subtotal_5, total_debit, total_credit, total_balance, net_income



def balance_sheet(request):
    branches = Branch.objects.all()  # Changed from Company to Branch

    if request.method == 'POST':
        form = TrialBalanceForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            branch_id = form.cleaned_data['branch'].id if form.cleaned_data['branch'] else None

            # When branch_id is None, set branch_code to None to indicate "All Branches"
            branch_code = None
            if branch_id is not None:
                branch = get_object_or_404(Branch, id=branch_id)  # Changed from Company to Branch
                branch_code = branch.branch_code

            # Generate balance sheet data
            balance_sheet_data, subtotal_4, subtotal_5, total_debit, total_credit, total_balance, net_income = generate_balance_sheet(start_date, end_date, branch_code)
            
            return render(request, 'reports/financials/balance_sheet.html', {
                'form': form,
                'branches': branches,  # Changed from companies to branches
                'balance_sheet_data': balance_sheet_data,
                'subtotal_4': subtotal_4,
                'subtotal_5': subtotal_5,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'total_balance': total_balance,
                'net_income': net_income,
                'start_date': start_date,
                'end_date': end_date,
                'selected_branch': branch_id,
                'branch': branches.first() if branches.exists() else None,  # Changed from company to branch
            })
    else:
        form = TrialBalanceForm()

    return render(request, 'reports/financials/balance_sheet.html', {
        'form': form,
        'branches': branches,  # Changed from companies to branches
        'selected_branch': None,
    })




from django.shortcuts import render, get_object_or_404
from collections import defaultdict
from .forms import TrialBalanceForm
from transactions.models import Memtrans
from accounts.models import Account
from company.models import Company

def generate_profit_and_loss(start_date, end_date, branch_code=None):
    """
    Generate profit and loss statement data for a given date range and optionally filter by branch.
    Only include GL numbers starting with 4 (revenue) or 5 (expenses).
    """
    # Query all relevant Memtrans entries for the given date range and branch
    memtrans_entries = Memtrans.objects.filter(ses_date__range=[start_date, end_date], error='A')

    # Apply branch filtering only if a specific branch code is provided
    if branch_code:
        memtrans_entries = memtrans_entries.filter(branch=branch_code)

    # Initialize a dictionary to hold GL account balances
    gl_customer_balance = defaultdict(lambda: {'debit': 0, 'credit': 0, 'balance': 0})

    # Process each entry
    for entry in memtrans_entries:
        gl_no = entry.gl_no

        # Filter GL numbers starting with 4 or 5
        if gl_no.startswith('4') or gl_no.startswith('5'):
            amount = entry.amount

            # Determine the type of entry and update the balances accordingly
            if entry.type == 'N':
                if amount < 0:
                    gl_customer_balance[gl_no]['debit'] += amount  # Use amount directly to retain sign
                else:
                    gl_customer_balance[gl_no]['credit'] += amount
            else:
                if amount < 0:
                    gl_customer_balance[gl_no]['credit'] += amount  # Use amount directly to retain sign
                else:
                    gl_customer_balance[gl_no]['debit'] += amount

    # Fetch all necessary accounts in a single query to improve performance
    accounts = Account.objects.filter(gl_no__in=gl_customer_balance.keys()).values('gl_no', 'gl_name')
    account_map = {account['gl_no']: account['gl_name'] for account in accounts}

    # Prepare profit and loss data
    sorted_profit_and_loss_data = []
    subtotal_4 = subtotal_5 = 0

    for gl_no, balance_data in gl_customer_balance.items():
        debit = balance_data['debit']
        credit = balance_data['credit']
        # Calculate balance by adding debit and credit
        balance = debit + credit
        gl_name = account_map.get(gl_no, '')  # Default to empty string if GL number not found
        balance_data.update({'gl_no': gl_no, 'gl_name': gl_name, 'balance': balance})

        # Calculate subtotals for revenues and expenses
        if gl_no.startswith("4"):
            subtotal_4 += balance
        elif gl_no.startswith("5"):
            subtotal_5 += balance

        sorted_profit_and_loss_data.append(balance_data)

    # Calculate total debit, credit, and net income
    total_debit = sum(entry['debit'] for entry in sorted_profit_and_loss_data)
    total_credit = sum(entry['credit'] for entry in sorted_profit_and_loss_data)
    net_income = subtotal_4 + subtotal_5

    return sorted_profit_and_loss_data, subtotal_4, subtotal_5, total_debit, total_credit, net_income

def profit_and_loss(request):
    branches = Branch.objects.all()  # Changed from Company to Branch

    if request.method == 'POST':
        form = TrialBalanceForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            branch_id = form.cleaned_data['branch'].id if form.cleaned_data['branch'] else None

            # Determine branch code if a specific branch is selected
            branch_code = None
            if branch_id is not None:
                branch = get_object_or_404(Branch, id=branch_id)  # Changed from Company to Branch
                branch_code = branch.branch_code

            # Generate profit and loss data
            profit_and_loss_data, subtotal_4, subtotal_5, total_debit, total_credit, net_income = generate_profit_and_loss(
                start_date, end_date, branch_code
            )

            return render(request, 'reports/financials/profit_and_loss.html', {
                'form': form,
                'branches': branches,  # Changed from companies to branches
                'balance_sheet_data': profit_and_loss_data,
                'subtotal_4': subtotal_4,
                'subtotal_5': subtotal_5,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'net_income': net_income,
                'start_date': start_date,
                'end_date': end_date,
                'selected_branch': branch_id,
                'branch': branch if branch_id else branches.first(),  # Changed from company to branch
            })
    else:
        form = TrialBalanceForm()

    return render(request, 'reports/financials/profit_and_loss.html', {
        'form': form,
        'branches': branches,  # Changed from companies to branches
        'selected_branch': None,
    })

    
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from loans.models import LoanHist

def loan_hist(request):
    if request.method == "POST":
        id = request.POST.get('id')
        loanhist_entry = get_object_or_404(LoanHist, id=id)
        loanhist_entry.delete()
        messages.success(request, 'LoanHist entry deleted successfully!')
        return redirect('loan_hist')  # Assuming 'loan_hist' is the name of the URL pattern for this view

    gl_no = request.GET.get('gl_no')
    ac_no = request.GET.get('ac_no')
    cycle = request.GET.get('cycle')

    loan_hist = LoanHist.objects.all()

    if gl_no:
        loan_hist = loan_hist.filter(gl_no=gl_no)
    if ac_no:
        loan_hist = loan_hist.filter(ac_no=ac_no)
    if cycle:
        loan_hist = loan_hist.filter(cycle=cycle)

    return render(request, 'reports/loans/loan_hist.html', {
        'loan_hist': loan_hist,
        'gl_no': gl_no,
        'ac_no': ac_no,
        'cycle': cycle,
    })




@login_required(login_url='login')
@user_passes_test(check_role_admin)
def loan_report(request):
    return render(request, 'reports/loans/loan_report.html')





from django.shortcuts import render, get_object_or_404
from company.models import Company
from reports.forms import LoanLedgerCardForm  # Ensure this form is correctly defined

from django.shortcuts import render
from django.db.models import Sum



def loan_ledger_card_view(request):
    # Get the current user's company (Branch) first
    user_branch = request.user.branch  # Assuming the User model has a ForeignKey to Branch
    
    # Filter all querysets by the user's branch/company
    branches = Branch.objects.filter(id=user_branch.id)  # Only show user's branch
    accounts = Account.objects.filter(branch=user_branch)  # Only accounts from user's branch
    error_message = None

    if request.method == 'POST':
        form = LoanLedgerCardForm(request.POST, user_branch=user_branch)  # Pass user_branch to form
        if form.is_valid():
            branch = form.cleaned_data['branch']
            account = form.cleaned_data['account']
            ac_no = form.cleaned_data.get('ac_no')
            cycle = form.cleaned_data.get('cycle')

            try:
                # Retrieve the loan information - add branch filter
                loan = Loans.objects.get(branch=branch, gl_no=account.gl_no, ac_no=ac_no, cycle=cycle)
                disbursement_amount = loan.loan_amount
                total_interest = LoanHist.objects.filter(
                    branch=branch, gl_no=account.gl_no, ac_no=ac_no, cycle=cycle, trx_type='LD'
                ).aggregate(Sum('interest'))['interest__sum'] or 0
                disbursement_date = loan.disbursement_date
                num_installments = loan.num_install
                loan_officer = loan.loan_officer
                annual_interest_rate = loan.interest_rate

                # Retrieve the customer information - add branch filter
                customer = Customer.objects.get(branch=branch, gl_no=account.gl_no, ac_no=ac_no)

                # Rest of your existing code remains the same...
                principal_balance = disbursement_amount
                interest_balance = total_interest

                ledger_card = LoanHist.objects.filter(
                    branch=branch, gl_no=account.gl_no, ac_no=ac_no, cycle=cycle
                ).order_by('trx_date')

                total_payment = 0
                penalty_balance = 0

                for entry in ledger_card:
                    total_payment += entry.principal + entry.interest + entry.penalty

                    if entry.trx_type == 'LP':
                        principal_balance += entry.principal
                        interest_balance += entry.interest
                    
                    penalty_balance += entry.penalty
                    total_balance = principal_balance + interest_balance + penalty_balance

                    entry.total_payment = total_payment
                    entry.principal_balance = principal_balance
                    entry.interest_balance = interest_balance
                    entry.penalty_balance = penalty_balance
                    entry.total_balance = total_balance

                return render(request, 'reports/loans/loan_ledger_card.html', {
                    'form': form, 
                    'ledger_card': ledger_card,
                    'total_payment': total_payment,
                    'principal_balance': principal_balance,
                    'interest_balance': interest_balance,
                    'penalty_balance': penalty_balance,
                    'total_balance': total_balance,
                    'customer': customer,
                    'loan': loan,
                    'disbursement_amount': disbursement_amount,
                    'disbursement_date': disbursement_date,
                    'num_installments': num_installments,
                    'loan_officer': loan_officer,
                    'annual_interest_rate': annual_interest_rate,
                    'branches': branches,
                    'accounts': accounts,
                    'branch': branch,
                    'form_submitted': True
                })

            except Loans.DoesNotExist:
                error_message = 'No loan record found for the provided criteria.'
            except Customer.DoesNotExist:
                error_message = 'No customer record found for the provided criteria.'
            
            return render(request, 'reports/loans/loan_ledger_card.html', {
                'form': form,
                'branches': branches,
                'accounts': accounts,
                'form_submitted': True,
                'error_message': error_message
            })
    else:
        form = LoanLedgerCardForm(user_branch=user_branch)  # Pass user_branch to form

    return render(request, 'reports/loans/loan_ledger_card.html', {
        'form': form,
        'branches': branches,
        'accounts': accounts,
        'form_submitted': False,
        'error_message': error_message
    })



def loan_repayment_schedule(request):
    # Get the user's company from their branch
    user_branch = request.user.branch  # Assuming User has a ForeignKey to Branch
    if not user_branch:
        return render(request, 'reports/loans/loan_repayment_schedule.html', {
            'form': LoanLedgerCardForm(),
            'branches': [],
            'accounts': [],
            'form_submitted': False,
            'error_message': 'You are not associated with any branch.',
        })

    # Filter branches and accounts by user's branch
    branches = Branch.objects.filter(id=user_branch.id)
    accounts = Account.objects.filter(branch=user_branch)

    if request.method == 'POST':
        form = LoanLedgerCardForm(request.POST, user_branch=user_branch)
        if form.is_valid():
            branch = form.cleaned_data['branch']
            account = form.cleaned_data['account']
            ac_no = form.cleaned_data.get('ac_no')
            cycle = form.cleaned_data.get('cycle')

            try:
                # Retrieve the loan information
                loan = Loans.objects.get(
                    branch=branch,
                    gl_no=account.gl_no, 
                    ac_no=ac_no, 
                    cycle=cycle
                )
                
                # Get customer
                customer = Customer.objects.get(
                    branch=branch,
                    gl_no=account.gl_no, 
                    ac_no=ac_no
                )

                # Calculate balances and ledger entries
                disbursement_amount = loan.loan_amount
                disbursement_date = loan.disbursement_date
                
                # Get all loan transactions (not just LD)
                ledger_entries = LoanHist.objects.filter(
                    branch=branch,
                    gl_no=account.gl_no, 
                    ac_no=ac_no, 
                    cycle=cycle
                ).order_by('trx_date')
                
                # Initialize balances
                principal_balance = disbursement_amount
                interest_balance = sum(
                    entry.interest for entry in ledger_entries.filter(trx_type='LD')
                )
                penalty_balance = 0
                total_payment = 0
                
                # Process each entry
                ledger_card = []
                for entry in ledger_entries:
                    if entry.trx_type == 'LP':  # Loan Payment
                        principal_balance -= entry.principal
                        interest_balance -= entry.interest
                        total_payment += entry.principal + entry.interest
                    
                    penalty_balance += entry.penalty
                    total_balance = principal_balance + interest_balance + penalty_balance
                    
                    # Add calculated fields to entry
                    entry.principal_balance = principal_balance
                    entry.interest_balance = interest_balance
                    entry.penalty_balance = penalty_balance
                    entry.total_balance = total_balance
                    entry.total_payment = total_payment
                    
                    ledger_card.append(entry)

                return render(request, 'reports/loans/loan_repayment_schedule.html', {
                    'form': form,
                    'ledger_card': ledger_card,
                    'customer': customer,
                    'loan': loan,
                    'disbursement_amount': disbursement_amount,
                    'disbursement_date': disbursement_date,
                    'num_installments': loan.num_install,
                    'loan_officer': loan.loan_officer,
                    'annual_interest_rate': loan.interest_rate,
                    'branches': branches,
                    'accounts': accounts,
                    'form_submitted': True,
                    'error_message': None
                })

            except (Loans.DoesNotExist, Customer.DoesNotExist) as e:
                error_message = 'No loan or customer record found.' if isinstance(e, Loans.DoesNotExist) else 'Customer record not found.'
                return render(request, 'reports/loans/loan_repayment_schedule.html', {
                    'form': form,
                    'branches': branches,
                    'accounts': accounts,
                    'form_submitted': True,
                    'error_message': error_message,
                })
        
        else:
            # Form is invalid - show errors
            return render(request, 'reports/loans/loan_repayment_schedule.html', {
                'form': form,
                'branches': branches,
                'accounts': accounts,
                'form_submitted': False,
                'error_message': 'Please correct the errors below.',
            })

    else:
        # GET request - initialize form with filtered data
        form = LoanLedgerCardForm(user_branch=user_branch)
    
    return render(request, 'reports/loans/loan_repayment_schedule.html', {
        'form': form,
        'branches': branches,
        'accounts': accounts,
        'form_submitted': False,
        'error_message': None
    })


from .forms import LoanDisbursementReportForm

from django.shortcuts import render

from django.shortcuts import render
from django.db.models import Sum
from .forms import LoanDisbursementReportForm
from loans.models import Loans
from company.models import Company

from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from .forms import LoanDisbursementReportForm
from loans.models import Loans
from company.models import Branch

@login_required



def loan_disbursement_report(request):
    # Get current user's branch
    user_branch = request.user.branch
    
    # Initialize form with user's branch
    form = LoanDisbursementReportForm(
        request.POST or None,
        user_branch=user_branch,
        initial={'reporting_date': date.today()}  # Set default date to today
    )
    
    # Initialize context
    context = {
        'form': form,
        'expected_repayments': [],
        'branches': Branch.objects.filter(id=user_branch.id),
        'gl_accounts': Account.objects.filter(branch=user_branch),
        'current_date': timezone.now().strftime('%d/%m/%Y'),
        'reporting_date': None,
        'selected_branch': None,
        'selected_gl_no': None,
        'grand_total_loan_amount': 0,
        'grand_total_interest': 0,
        'grand_total_principal_paid': 0,
        'grand_total_interest_paid': 0,
        'grand_total_repayment': 0,
    }

    if request.method == 'POST':
        if form.is_valid():
            reporting_date = form.cleaned_data['reporting_date']
            branch = form.cleaned_data.get('branch') or user_branch
            gl_no = form.cleaned_data.get('gl_no')

            # Base query - always filter by user's branch
            loans = Loans.objects.filter(
                branch=user_branch,
                disbursement_date__lte=reporting_date
            ).select_related('customer')

            # Apply additional filters
            if gl_no:
                loans = loans.filter(gl_no=gl_no.gl_no)

            expected_repayments = []
            grand_totals = {
                'loan_amount': 0,
                'total_interest': 0,
                'total_principal_paid': 0,
                'total_interest_paid': 0,
                'expected_principal_repayment': 0,
                'expected_interest_repayment': 0,
            }

            for loan in loans:
                # Calculate expected repayments (simplified example)
                # You should implement proper calculation based on your business logic
                expected_principal = loan.loan_amount / loan.num_install if loan.num_install else 0
                expected_interest = (loan.loan_amount * loan.interest_rate / 100) / 12  # Monthly interest example
                
                # Calculate actual payments
                payments = LoanHist.objects.filter(
                    gl_no=loan.gl_no,
                    ac_no=loan.ac_no,
                    cycle=loan.cycle,
                    trx_type='LP',  # Loan Payment
                    trx_date__lte=reporting_date
                ).aggregate(
                    total_principal=Sum('principal'),
                    total_interest=Sum('interest')
                )
                
                principal_paid = payments['total_principal'] or 0
                interest_paid = payments['total_interest'] or 0
                
                # Calculate due amounts
                principal_due = max(0, expected_principal - principal_paid)
                interest_due = max(0, expected_interest - interest_paid)
                
                repayment_data = {
                    'gl_no': loan.gl_no,
                    'ac_no': loan.ac_no,
                    'customer_name': loan.customer.get_full_name() if loan.customer else "No Customer",
                    'loan_amount': loan.loan_amount,
                    'total_interest': expected_interest,
                    'total_principal_paid': principal_paid,
                    'total_interest_paid': interest_paid,
                    'expected_principal_repayment': principal_due,
                    'expected_interest_repayment': interest_due,
                }
                
                expected_repayments.append(repayment_data)
                
                # Update grand totals
                grand_totals['loan_amount'] += loan.loan_amount
                grand_totals['total_interest'] += expected_interest
                grand_totals['total_principal_paid'] += principal_paid
                grand_totals['total_interest_paid'] += interest_paid
                grand_totals['expected_principal_repayment'] += principal_due
                grand_totals['expected_interest_repayment'] += interest_due

            context.update({
                'expected_repayments': expected_repayments,
                'reporting_date': reporting_date,
                'selected_branch': branch.branch_code if branch != user_branch else None,
                'selected_gl_no': gl_no.gl_no if gl_no else None,
                'grand_totals': grand_totals,
                'grand_total_loan_amount': grand_totals['loan_amount'],
                'grand_total_interest': grand_totals['total_interest'],
                'grand_total_principal_paid': grand_totals['total_principal_paid'],
                'grand_total_interest_paid': grand_totals['total_interest_paid'],
                'grand_total_repayment': grand_totals['expected_principal_repayment'],
            })
        else:
            # Form is invalid - add error to context
            context['error_message'] = "Please correct the errors below."

    return render(request, 'reports/loans/loan_disbursement_report.html', context)



@login_required
def loan_repayment_report(request, loan_id=None):
    # Get current user's branch and company name
    user_branch = request.user.branch
    user_company_name = user_branch.company_name if user_branch else None
    
    # Initialize variables
    form = LoanRepaymentReportForm(request.POST or None, user_branch=user_branch)
    repayments = LoanHist.objects.none()
    disbursements = LoanHist.objects.none()
    loan = None
    
    context = {
        'form': form,
        'repayments': repayments,
        'disbursements': disbursements,
        'loan': loan,
        'selected_branch': None,
        'company_name': user_company_name,
        'branch_name': user_branch.branch_name if user_branch else None,
        'grand_total_principal': 0,
        'grand_total_interest': 0,
        'grand_total_penalty': 0,
        'total_paid_sum': 0,
        'subtotals': [],
        'current_date': timezone.now().strftime('%d/%m/%Y'),
        'start_date': None,
        'end_date': None,
        'grand_total_disbursed': 0,
        'outstanding_amount': 0,
    }

    # Get loan if ID is provided (only if loan belongs to user's company)
    if loan_id:
        try:
            loan = Loans.objects.select_related(
                'customer', 'branch', 'loan_officer', 'business_sector'
            ).get(
                pk=loan_id,
                branch__company_name=user_company_name
            )
            context['loan'] = loan
        except Loans.DoesNotExist:
            messages.error(request, "Loan not found or not accessible")

    if request.method == 'POST' and form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        branch = form.cleaned_data.get('branch')
        gl_no = form.cleaned_data.get('gl_no')
        cycle = form.cleaned_data.get('cycle')

        # Base query for repayments - filtered by user's company with prefetch
        repayments = LoanHist.objects.filter(
            trx_date__range=[start_date, end_date],
            trx_type='LP',  # Loan Payment
            branch__company_name=user_company_name
        ).select_related(
            'branch',
            'loan',  # Make sure this is the correct related_name
            'loan__customer'  # Add this to prefetch customer data
        )

        # If viewing specific loan, filter by loan details
        if loan:
            repayments = repayments.filter(
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle
            )
            # Get disbursements for this loan
            disbursements = LoanHist.objects.filter(
                trx_type='LD',  # Loan Disbursement
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle,
                branch__company_name=user_company_name
            )
        elif branch:
            repayments = repayments.filter(branch=branch)
        if gl_no:
            repayments = repayments.filter(gl_no=gl_no.gl_no)
        if cycle:
            repayments = repayments.filter(cycle=cycle)

        # Calculate aggregates
        repayment_aggregates = repayments.aggregate(
            total_principal=Sum('principal'),
            total_interest=Sum('interest'),
            total_penalty=Sum('penalty'),
            total_paid=Sum(F('principal') + F('interest'))
        )

        # Calculate disbursement total if viewing loan
        disbursed_total = 0
        if loan:
            disbursement_agg = disbursements.aggregate(
                total_disbursed=Sum('principal')
            )
            disbursed_total = disbursement_agg['total_disbursed'] or 0

        # Calculate subtotals with cycle included
        subtotals = repayments.values(
            'gl_no',
            'cycle',
            'branch__branch_name'
        ).annotate(
            subtotal_principal=Sum('principal'),
            subtotal_interest=Sum('interest'),
            subtotal_penalty=Sum('penalty'),
            subtotal_paid=Sum(F('principal') + F('interest'))
        ).order_by('branch__branch_name', 'gl_no', 'cycle')

        # Calculate outstanding amount if loan exists
        outstanding_amount = 0
        if loan:
            grand_total_principal = repayment_aggregates.get('total_principal') or 0
            outstanding_amount = loan.loan_amount - grand_total_principal

        # Update context
        context.update({
            'repayments': repayments,
            'disbursements': disbursements if loan else [],
            'loan': loan,
            'outstanding_amount': outstanding_amount,
            'grand_total_principal': repayment_aggregates.get('total_principal', 0) or 0,
            'grand_total_interest': repayment_aggregates.get('total_interest', 0) or 0,
            'grand_total_penalty': repayment_aggregates.get('total_penalty', 0) or 0,
            'total_paid_sum': repayment_aggregates.get('total_paid', 0) or 0,
            'grand_total_disbursed': disbursed_total,
            'selected_branch': branch,
            'start_date': start_date,
            'end_date': end_date,
            'subtotals': subtotals,
        })

    return render(request, 'reports/loans/loan_repayment_report.html', context)

# views.py
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, F
from .forms import LoanRepaymentReportForm
from loans.models import LoanHist, Loans  # Make sure Loans is imported
from company.models import Branch  # Import Branch if not already
from accounts.models import Account
from django.contrib.auth.decorators import login_required

@login_required


def repayment_since_disbursement_report(request):
    # Initialize default context values
    context = {
        'report_title': 'Repayment Since Disbursement',
        'repayments': [],
        'grand_total_principal': 0,
        'grand_total_interest': 0,
        'grand_total_penalty': 0,
        'total_paid_sum': 0,
        'total_loan_amount': 0,
        'total_loan_interest': 0,
        'total_percentage_paid': 0,
        'current_date': timezone.now().strftime('%Y-%m-%d'),
        'start_date': '',
        'end_date': '',
        'branches': Branch.objects.all(),
        'gl_accounts': Account.objects.all(),
        'selected_branch': '',
        'selected_gl_no': '',
        'company_name': 'All Companies',
        'branch_name': 'All Branches'
    }

    if request.method == 'POST':
        start_date = request.POST.get('start_date', '')
        end_date = request.POST.get('end_date', '')
        selected_branch = request.POST.get('branch', '')
        selected_gl_no = request.POST.get('gl_no', '')

        if start_date and end_date:
            try:
                # Convert to date objects for comparison
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

                # Fetch loans disbursed before or on the end date
                loans = Loans.objects.filter(
                    disbursement_date__lte=end_date_obj
                ).select_related('customer', 'branch', 'branch__company')

                # Apply filters if provided
                if selected_branch:
                    loans = loans.filter(branch_id=selected_branch)
                    branch = Branch.objects.filter(id=selected_branch).first()
                    if branch:
                        context['company_name'] = branch.company.company_name
                        context['branch_name'] = branch.branch_name

                if selected_gl_no:
                    loans = loans.filter(gl_no=selected_gl_no)

                # Filter loan repayments
                repayments = LoanHist.objects.filter(
                    trx_date__range=[start_date_obj, end_date_obj],
                    trx_type='LP',
                    gl_no__in=loans.values_list('gl_no', flat=True)
                )

                # Aggregate repayments by customer
                repayment_summaries = repayments.values('gl_no', 'ac_no', 'cycle').annotate(
                    total_principal=Sum('principal'),
                    total_interest=Sum('interest'),
                    total_penalty=Sum('penalty'),
                    total_paid=Sum(F('principal') + F('interest') + F('penalty'))
                )

                # Calculate grand totals
                grand_total_principal = repayment_summaries.aggregate(Sum('total_principal'))['total_principal__sum'] or 0
                grand_total_interest = repayment_summaries.aggregate(Sum('total_interest'))['total_interest__sum'] or 0
                grand_total_penalty = repayment_summaries.aggregate(Sum('total_penalty'))['total_penalty__sum'] or 0

                # Process each repayment
                repayments_with_percentage = []
                total_loan_amount = 0
                total_loan_interest = 0
                
                for summary in repayment_summaries:
                    loan = loans.filter(
                        gl_no=summary['gl_no'],
                        ac_no=summary['ac_no'],
                        cycle=summary['cycle']
                    ).first()
                    
                    if loan:
                        loan_amount = loan.loan_amount
                        loan_interest = loan.total_interest
                        customer = loan.customer
                        customer_name = customer.get_full_name() if customer else 'Unknown'
                        branch_name = loan.branch.branch_name if loan.branch else 'N/A'
                    else:
                        loan_amount = 0
                        loan_interest = 0
                        customer_name = 'Unknown'
                        branch_name = 'N/A'

                    total_loan_amount += loan_amount
                    total_loan_interest += loan_interest
                    percentage_paid = (summary['total_principal'] / loan_amount) * 100 if loan_amount > 0 else 0

                    repayments_with_percentage.append({
                        'gl_no': summary['gl_no'],
                        'ac_no': summary['ac_no'],
                        'cycle': summary['cycle'],
                        'customer_name': customer_name,
                        'branch_name': branch_name,
                        'total_principal': summary['total_principal'],
                        'total_interest': summary['total_interest'],
                        'total_penalty': summary['total_penalty'],
                        'total_paid': summary['total_paid'],
                        'loan_amount': loan_amount,
                        'total_loan_interest': loan_interest,
                        'percentage_paid': round(percentage_paid, 2)
                    })

                # Final calculations
                total_paid_sum = sum(item['total_paid'] for item in repayments_with_percentage)
                total_percentage_paid = (grand_total_principal / total_loan_amount) * 100 if total_loan_amount > 0 else 0

                # Update context with results
                context.update({
                    'repayments': repayments_with_percentage,
                    'grand_total_principal': grand_total_principal,
                    'grand_total_interest': grand_total_interest,
                    'grand_total_penalty': grand_total_penalty,
                    'total_paid_sum': total_paid_sum,
                    'total_loan_amount': total_loan_amount,
                    'total_loan_interest': total_loan_interest,
                    'total_percentage_paid': total_percentage_paid,
                    'start_date': start_date,
                    'end_date': end_date,
                    'selected_branch': selected_branch,
                    'selected_gl_no': selected_gl_no
                })

            except ValueError:
                messages.error(request, "Invalid date format. Please use YYYY-MM-DD format.")

    return render(request, 'reports/loans/repayment_since_disbursement_report.html', context)


def loan_outstanding_balance(request):
    # Initialize variables
    outstanding_loans = []
    grand_total_outstanding_principal = 0
    grand_total_outstanding_interest = 0
    grand_total_outstanding_amount = 0
    grand_total_loan_disbursement = 0
    reporting_date = ''
    selected_branch = ''
    selected_gl_no = ''

    # Fetch all branches and GL accounts for dropdowns
    branches = Branch.objects.all()  # Changed from Company to Branch
    gl_accounts = Account.objects.all()

    if request.method == 'POST':
        reporting_date = request.POST.get('reporting_date', '')
        selected_branch = request.POST.get('branch', '')
        selected_gl_no = request.POST.get('gl_no', '')

        if reporting_date:
            # Fetch outstanding loans, filtered by branch and gl_no if selected
            loans = Loans.objects.filter(disbursement_date__lte=reporting_date)
            
            if selected_branch:
                loans = loans.filter(branch_id=selected_branch)  # Using branch_id for filtering
                
            if selected_gl_no:
                loans = loans.filter(gl_no=selected_gl_no)

            # Prepare list for output
            for loan in loans:
                # Get the latest transaction of type 'LD' for the loan
                latest_transaction = LoanHist.objects.filter(
                    gl_no=loan.gl_no,
                    ac_no=loan.ac_no,
                    cycle=loan.cycle,
                    trx_type='LD'
                ).order_by('-trx_date').first()

                # Get expiry_date from the latest transaction
                expiry_date = latest_transaction.trx_date if latest_transaction else None

                # Calculate total principal paid
                total_principal_paid = LoanHist.objects.filter(
                    gl_no=loan.gl_no,
                    ac_no=loan.ac_no,
                    cycle=loan.cycle,
                    trx_type='LP'
                ).aggregate(
                    total_principal_paid=Sum('principal')
                )['total_principal_paid'] or 0

                # Calculate total interest paid
                total_interest_paid = LoanHist.objects.filter(
                    gl_no=loan.gl_no,
                    ac_no=loan.ac_no,
                    cycle=loan.cycle,
                    trx_type='LP'
                ).aggregate(
                    total_interest_paid=Sum('interest')
                )['total_interest_paid'] or 0

                # Fetch customer name
                if loan.customer:
                    customer_name = f"{loan.customer.first_name} {loan.customer.middle_name or ''} {loan.customer.last_name}"
                else:
                    customer_name = 'N/A'

                # Add loan data to the list
                outstanding_loans.append({
                    'gl_no': loan.gl_no,
                    'ac_no': loan.ac_no,
                    'customer_name': customer_name,
                    'loan_amount': loan.loan_amount,
                    'total_interest': loan.total_interest,
                    'disbursement_date': loan.disbursement_date,
                    'total_principal_paid': total_principal_paid,
                    'total_interest_paid': total_interest_paid,
                    'outstanding_principal': loan.loan_amount + total_principal_paid,  # Fixed calculation
                    'outstanding_interest': loan.total_interest + total_interest_paid,  # Fixed calculation
                    'outstanding_amount': (loan.loan_amount + total_principal_paid) + (loan.total_interest + total_interest_paid),  # Fixed calculation
                    'expiry_date': expiry_date
                })

                # Update totals
                grand_total_loan_disbursement += loan.loan_amount
                grand_total_outstanding_principal += (loan.loan_amount + total_principal_paid)
                grand_total_outstanding_interest += (loan.total_interest + total_interest_paid)
                grand_total_outstanding_amount += (loan.loan_amount + total_principal_paid) + (loan.total_interest + total_interest_paid)

    context = {
        'report_title': 'Loan Outstanding Balance Report',
        'outstanding_loans': outstanding_loans,
        'grand_total_loan_disbursement': grand_total_loan_disbursement,
        'grand_total_outstanding_principal': grand_total_outstanding_principal,
        'grand_total_outstanding_interest': grand_total_outstanding_interest,
        'grand_total_outstanding_amount': grand_total_outstanding_amount,
        'current_date': timezone.now(),
        'reporting_date': reporting_date,
        'branches': branches,  # Changed variable name to match the model
        'gl_accounts': gl_accounts,
        'selected_branch': selected_branch,
        'selected_gl_no': selected_gl_no
    }

    return render(request, 'reports/loans/loan_outstanding_balance_report.html', context)



from django.core.exceptions import ValidationError

from django.shortcuts import render
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum
 # Update with the actual import path
from django.http import HttpResponseBadRequest

def expected_repayment(request):
    # Initialize variables
    expected_repayments = []
    grand_total_repayment = 0
    grand_total_interest = 0
    grand_total_principal_paid = 0
    grand_total_interest_paid = 0
    reporting_date = ''
    selected_branch = ''
    selected_gl_no = ''

    # Fetch all branches and GL accounts for dropdowns
    branches = Branch.objects.all()  # Changed from Company to Branch
    gl_accounts = Account.objects.all()

    if request.method == 'POST':
        # Get form data
        reporting_date = request.POST.get('reporting_date', '')
        selected_branch = request.POST.get('branch', '')
        selected_gl_no = request.POST.get('gl_no', '')

        # Validate reporting_date
        if reporting_date:
            try:
                reporting_date = timezone.datetime.strptime(reporting_date, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
                return redirect('expected_repayment')
        else:
            reporting_date = timezone.now().date()

        # Initialize queryset
        loans = Loans.objects.filter(disbursement_date__lte=reporting_date)

        # Apply additional filters if provided
        if selected_branch:
            loans = loans.filter(branch_id=selected_branch)  # Using branch_id for filtering
        if selected_gl_no:
            loans = loans.filter(gl_no=selected_gl_no)

        # Prepare list for output
        for loan in loans:
            total_disbursements = LoanHist.objects.filter(
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle,
                trx_type='LD',
                trx_date__lte=reporting_date
            ).aggregate(total_disbursements=Sum('principal'))['total_disbursements'] or 0

            total_principal_paid = LoanHist.objects.filter(
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle,
                trx_type='LP',
                trx_date__lte=reporting_date
            ).aggregate(total_principal_paid=Sum('principal'))['total_principal_paid'] or 0

            total_interest_paid = LoanHist.objects.filter(
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle,
                trx_type='LP',
                trx_date__lte=reporting_date
            ).aggregate(total_interest_paid=Sum('interest'))['total_interest_paid'] or 0

            total_interest = LoanHist.objects.filter(
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle,
                trx_type='LD',
                trx_date__lte=reporting_date
            ).aggregate(total_interest=Sum('interest'))['total_interest'] or 0

            expected_principal_repayment = total_disbursements - total_principal_paid  # Fixed calculation
            expected_interest_repayment = total_interest - total_interest_paid  # Fixed calculation

            # Fetch customer name
            if loan.customer:
                customer_name = f"{loan.customer.first_name} {loan.customer.middle_name or ''} {loan.customer.last_name}"
            else:
                customer_name = 'N/A'

            expected_repayments.append({
                'gl_no': loan.gl_no,
                'ac_no': loan.ac_no,
                'customer_name': customer_name,
                'loan_amount': loan.loan_amount,
                'total_disbursements': total_disbursements,
                'total_principal_paid': total_principal_paid,
                'total_interest_paid': total_interest_paid,
                'total_interest': total_interest,
                'expected_principal_repayment': expected_principal_repayment,
                'expected_interest_repayment': expected_interest_repayment,
                'expected_total_repayment': expected_principal_repayment + expected_interest_repayment,
            })

            # Update totals
            grand_total_repayment += expected_principal_repayment
            grand_total_interest += total_interest
            grand_total_principal_paid += total_principal_paid
            grand_total_interest_paid += total_interest_paid

    context = {
        'report_title': 'Expected Repayment Report',
        'expected_repayments': expected_repayments,
        'grand_total_repayment': grand_total_repayment,
        'grand_total_interest': grand_total_interest,
        'grand_total_principal_paid': grand_total_principal_paid,
        'grand_total_interest_paid': grand_total_interest_paid,
        'grand_total_expected': grand_total_repayment + grand_total_interest_paid,
        'current_date': timezone.now(),
        'reporting_date': reporting_date,
        'branches': branches,
        'gl_accounts': gl_accounts,
        'selected_branch': selected_branch,
        'selected_gl_no': selected_gl_no
    }

    return render(request, 'reports/loans/expected_repayment_report.html', context)

def active_loans_by_officer(request):
    # Initialize variables
    active_loans_by_officer = {}
    grand_total_loans = 0
    grand_total_amount = 0
    selected_officer = ''
    selected_branch = ''
    selected_gl_no = ''  # Changed from selected_product
    reporting_date = ''

    # Fetch all options for dropdowns
    officers = Account_Officer.objects.all()
    branches = Branch.objects.all()
    gl_accounts = Account.objects.all()  # Changed from products

    if request.method == 'POST':
        # Get form data
        selected_officer = request.POST.get('officer', '')
        selected_branch = request.POST.get('branch', '')
        selected_gl_no = request.POST.get('gl_no', '')  # Changed from product
        reporting_date = request.POST.get('reporting_date', '')

        # Initialize queryset
        loans = Loans.objects.filter(loan_amount__gt=0)  # Changed to gt 0 for active loans

        # Apply filters
        if selected_officer:
            loans = loans.filter(loan_officer__user=selected_officer)
        if selected_branch:
            loans = loans.filter(branch_id=selected_branch)
        if selected_gl_no:  # Changed from product filter
            loans = loans.filter(gl_no=selected_gl_no)  # Using the gl_no field directly
        if reporting_date:
            try:
                reporting_date = timezone.datetime.strptime(reporting_date, '%Y-%m-%d').date()
                loans = loans.filter(disbursement_date__lte=reporting_date)
            except ValueError:
                messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
                return redirect('active_loans_by_officer')

        # Group loans by loan officer and calculate totals
        for loan in loans:
            officer_name = loan.loan_officer.user if loan.loan_officer else 'Unassigned'
            
            if officer_name not in active_loans_by_officer:
                active_loans_by_officer[officer_name] = {
                    'loans': [],
                    'total_loans': 0,
                    'total_amount': 0,
                    'branch': loan.branch.branch_name if loan.branch else 'N/A'
                }

            customer_name = ''
            if loan.customer:
                customer_name = f"{loan.customer.first_name} {loan.customer.middle_name or ''} {loan.customer.last_name}".strip()

            active_loans_by_officer[officer_name]['loans'].append({
                'gl_no': loan.gl_no,
                'ac_no': loan.ac_no,
                'customer_name': customer_name or 'N/A',
                'loan_amount': loan.loan_amount,
                'disbursement_date': loan.disbursement_date,
                'account_name': loan.cust_gl_no  # Using available GL information
            })

            # Update totals
            active_loans_by_officer[officer_name]['total_loans'] += 1
            active_loans_by_officer[officer_name]['total_amount'] += loan.loan_amount
            grand_total_loans += 1
            grand_total_amount += loan.loan_amount

    context = {
        'report_title': 'Active Loans by Loan Officer',
        'active_loans_by_officer': dict(sorted(active_loans_by_officer.items())),
        'officers': officers,
        'branches': branches,
        'gl_accounts': gl_accounts,  # Changed from products
        'selected_officer': selected_officer,
        'selected_branch': selected_branch,
        'selected_gl_no': selected_gl_no,  # Changed from selected_product
        'reporting_date': reporting_date,
        'grand_total_loans': grand_total_loans,
        'grand_total_amount': grand_total_amount,
        'current_date': timezone.now(),
    }
    return render(request, 'reports/loans/active_loans_by_officer.html', context)

from .forms import LoanTillSheetForm





def loan_till_sheet(request):
    # Initialize variables
    repayments_with_percentage = []
    grand_total_principal = grand_total_interest = grand_total_penalty = total_paid_sum = 0
    start_date = end_date = None
    selected_branch = None
    selected_gl_no = None

    # Initialize form
    form = LoanTillSheetForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        try:
            # Get cleaned form data
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            selected_branch = form.cleaned_data.get('branch')
            selected_gl_no = form.cleaned_data.get('gl_no')

            # Fetch loans disbursed before or on the end date
            loans = Loans.objects.filter(disbursement_date__lte=end_date) if end_date else Loans.objects.all()
            
            if selected_gl_no:
                loans = loans.filter(gl_no=selected_gl_no.gl_no)

            # Filter loan repayments
            repayments = LoanHist.objects.filter(
                trx_date__range=[start_date, end_date],
                trx_type='LP',
                gl_no__in=loans.values_list('gl_no', flat=True)
            )

            # Apply branch filter if selected
            if selected_branch:
                repayments = repayments.filter(branch=selected_branch.branch_code)

            # Aggregate repayments
            repayment_summaries = repayments.values('gl_no', 'ac_no', 'cycle').annotate(
                total_principal=Sum('principal'),
                total_interest=Sum('interest'),
                total_penalty=Sum('penalty'),
                total_paid=Sum(F('principal') + F('interest') + F('penalty'))
            )

            # Calculate grand totals
            grand_total_principal = repayment_summaries.aggregate(Sum('total_principal'))['total_principal__sum'] or 0
            grand_total_interest = repayment_summaries.aggregate(Sum('total_interest'))['total_interest__sum'] or 0
            grand_total_penalty = repayment_summaries.aggregate(Sum('total_penalty'))['total_penalty__sum'] or 0

            # Process repayment data
            for summary in repayment_summaries:
                loan = loans.filter(
                    gl_no=summary['gl_no'],
                    ac_no=summary['ac_no'],
                    cycle=summary['cycle']
                ).first()
                
                if loan:
                    loan_amount = loan.loan_amount
                    total_loan_interest = loan.total_interest
                    customer = Customer.objects.filter(gl_no=loan.gl_no, ac_no=loan.ac_no).first()
                    customer_name = customer.get_full_name() if customer else 'Unknown'
                else:
                    loan_amount = total_loan_interest = 0
                    customer_name = 'Unknown'

                percentage_paid = (summary['total_principal'] / loan_amount * 100) if loan_amount > 0 else 0

                repayments_with_percentage.append({
                    'gl_no': summary['gl_no'],
                    'ac_no': summary['ac_no'],
                    'cycle': summary['cycle'],
                    'total_principal': summary['total_principal'],
                    'total_interest': summary['total_interest'],
                    'total_penalty': summary['total_penalty'],
                    'total_paid': summary['total_paid'],
                    'loan_amount': loan_amount,
                    'total_loan_interest': total_loan_interest,
                    'customer_name': customer_name,
                    'percentage_paid': round(percentage_paid, 2)
                })

            total_paid_sum = sum(item['total_paid'] for item in repayments_with_percentage)

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('loan_till_sheet')

    context = {
        'form': form,
        'report_title': 'Loan Repayment Till Sheet',
        'repayments': repayments_with_percentage,
        'selected_branch': selected_branch,
        'selected_gl_no': selected_gl_no,
        'grand_total_principal': grand_total_principal,
        'grand_total_interest': grand_total_interest,
        'grand_total_penalty': grand_total_penalty,
        'total_paid_sum': total_paid_sum,
        'current_date': timezone.now(),
    }
    return render(request, 'reports/loans/loan_till_sheet.html', context)



def loan_due_vs_repayment_report(request):
    # Initialize variables
    expected_repayments = []
    grand_totals = {
        'loan_amount': 0,
        'total_interest': 0,
        'total_principal_paid': 0,
        'total_interest_paid': 0,
        'expected_principal_repayment': 0,
        'expected_interest_repayment': 0,
    }
    
    reporting_date = timezone.now().date()
    selected_branch = ''
    selected_gl_no = ''

    if request.method == 'POST':
        # Get form data
        reporting_date_str = request.POST.get('reporting_date', '')
        selected_branch = request.POST.get('branch', '')
        selected_gl_no = request.POST.get('gl_no', '')

        # Validate reporting_date
        if reporting_date_str:
            try:
                reporting_date = timezone.datetime.strptime(reporting_date_str, '%Y-%m-%d').date()
            except ValueError:
                return HttpResponseBadRequest("Invalid date format. Please use YYYY-MM-DD.")

        # Initialize queryset with filters
        loans = Loans.objects.filter(disbursement_date__lte=reporting_date)
        
        # Apply branch filter if provided
        if selected_branch:
            loans = loans.filter(
                Q(branch_id=selected_branch) | 
                Q(branch__branch_code=selected_branch)
            )
        
        # Apply GL filter if provided
        if selected_gl_no:
            loans = loans.filter(gl_no=selected_gl_no)

        # Prepare report data
        for loan in loans:
            # Get all disbursements
            disbursements = LoanHist.objects.filter(
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle,
                trx_type='LD',
                trx_date__lte=reporting_date
            ).aggregate(
                total_principal=Sum('principal'),
                total_interest=Sum('interest')
            )
            
            # Get all repayments
            repayments = LoanHist.objects.filter(
                gl_no=loan.gl_no,
                ac_no=loan.ac_no,
                cycle=loan.cycle,
                trx_type='LP',
                trx_date__lte=reporting_date
            ).aggregate(
                total_principal_paid=Sum('principal'),
                total_interest_paid=Sum('interest')
            )

            # Calculate values (handle None cases)
            total_disbursements = disbursements['total_principal'] or 0
            total_interest = disbursements['total_interest'] or 0
            total_principal_paid = repayments['total_principal_paid'] or 0
            total_interest_paid = repayments['total_interest_paid'] or 0
            
            expected_principal_repayment = total_disbursements + total_principal_paid
            expected_interest_repayment = total_interest + total_interest_paid

            # Update grand totals
            grand_totals['loan_amount'] += loan.loan_amount
            grand_totals['total_interest'] += total_interest
            grand_totals['total_principal_paid'] += total_principal_paid
            grand_totals['total_interest_paid'] += total_interest_paid
            grand_totals['expected_principal_repayment'] += expected_principal_repayment
            grand_totals['expected_interest_repayment'] += expected_interest_repayment

            expected_repayments.append({
                'gl_no': loan.gl_no,
                'ac_no': loan.ac_no,
                'customer_name': f"{loan.customer.first_name} {loan.customer.middle_name or ''} {loan.customer.last_name}" if loan.customer else 'N/A',
                'loan_amount': loan.loan_amount,
                'total_disbursements': total_disbursements,
                'total_interest': total_interest,
                'total_principal_paid': total_principal_paid,
                'total_interest_paid': total_interest_paid,
                'expected_principal_repayment': expected_principal_repayment,
                'expected_interest_repayment': expected_interest_repayment,
            })

    context = {
        'report_title': 'Loan Dues vs Repayment Report',
        'expected_repayments': expected_repayments if request.method == 'POST' else None,
        'grand_totals': grand_totals,
        'current_date': timezone.now(),
        'reporting_date': reporting_date,
        'branches': Branch.objects.all(),
        'gl_accounts': Account.objects.all(),
        'selected_branch': selected_branch,
        'selected_gl_no': selected_gl_no
    }

    return render(request, 'reports/loans/loan_due_vs_repayment_report.html', context)


from django.shortcuts import render
from datetime import date
from accounts_admin.models import LoanProvision
from django.db.models import Sum
from django.utils.dateparse import parse_date  # Helper to parse date from string

def portfolio_at_risk_report_view(request):
    # Fetch the user's branch to get the associated Company
    user_branch = request.user.branch

    # Get the reporting_date from the user input, default to None if not supplied
    reporting_date_str = request.GET.get('reporting_date')  # Get date as string from query parameters
    reporting_date = None

    if reporting_date_str:
        try:
            # Try to parse the user-supplied date
            reporting_date = parse_date(reporting_date_str)
            if not reporting_date:
                reporting_date = date.today()  # Fallback to today if parsing fails
        except ValueError:
            reporting_date = date.today()  # Handle invalid date input gracefully

    # Initialize the report structure
    report = {
        "total_loans": 0,
        "total_outstanding": 0,
        "loans": [],
        "gl_nos": Account.objects.all(),
        "account_officers": Account_Officer.objects.all(),
    }

    # Fetch loans and apply filters only if the form is submitted (i.e., reporting_date is provided)
    if reporting_date:
        selected_product = request.GET.get('product')
        selected_officer = request.GET.get('account_officer')
        exclude_ac_no_one = request.GET.get('exclude_ac_no_one') == 'on'

        # Fetch loans disbursed before or on the reporting date
        loans = Loans.objects.filter(disb_status='T', disbursement_date__lte=reporting_date)  # Filter by reporting date

        if selected_product:
            loans = loans.filter(gl_no=selected_product)
        if selected_officer:
            loans = loans.filter(loan_officer_id=selected_officer)
        if exclude_ac_no_one:
            # Exclude internal accounts based on specific criteria
            non_financial_gl_nos = Account.objects.filter(is_non_financial=True).values_list('gl_no', flat=True)
            loans = loans.exclude(gl_no__in=non_financial_gl_nos)

        for loan in loans:
            # Loan expected repayment (LD) and actual payment (LP) till reporting date
            loan_hist_ld = LoanHist.objects.filter(
                gl_no=loan.gl_no, ac_no=loan.ac_no, cycle=loan.cycle, trx_type='LD', trx_date__lte=reporting_date
            ).aggregate(total_expected=Sum('principal'))['total_expected'] or 0

            loan_hist_lp = LoanHist.objects.filter(
                gl_no=loan.gl_no, ac_no=loan.ac_no, cycle=loan.cycle, trx_type='LP', trx_date__lte=reporting_date
            ).aggregate(total_paid=Sum('principal'))['total_paid'] or 0

            outstanding_balance = loan_hist_ld - loan_hist_lp  # Total expected minus total paid

            if outstanding_balance > 0:
                # Find the most recent LP transaction date for days in arrears calculation
                last_payment = LoanHist.objects.filter(
                    gl_no=loan.gl_no, ac_no=loan.ac_no, cycle=loan.cycle, trx_type='LP', trx_date__lte=reporting_date
                ).order_by('-trx_date').first()

                if last_payment:
                    last_payment_date = last_payment.trx_date

                    # Calculate days in arrears using the reporting date
                    days_in_arrears = (reporting_date - last_payment_date).days

                    # Find the appropriate provision category based on days in arrears
                    provision_category = LoanProvision.objects.filter(
                        min_days__lte=days_in_arrears, max_days__gte=days_in_arrears
                    ).first()

                    if provision_category:
                        category_name = provision_category.name
                        provision_amount = (provision_category.rate / 100) * outstanding_balance  # Calculate provision amount

                        # Add loan details and category to the report
                        report["loans"].append({
                            "gl_no": loan.gl_no,
                            "ac_no": loan.ac_no,
                            "cycle": loan.cycle,
                            "branch": loan.branch,
                            "outstanding_balance": outstanding_balance,
                            "days_in_arrears": days_in_arrears,
                            "category": category_name,
                            "provision_amount": provision_amount
                        })

                        # Update totals
                        report["total_loans"] += 1
                        report["total_outstanding"] += outstanding_balance

    # Render the report in the template
    return render(request, 'reports/loan_provision/par_report.html', {
        'report': report,
        'reporting_date': reporting_date  # Pass reporting date to template for display
    })






