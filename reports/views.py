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

def transaction_sequence_by_ses_date(request):
    branches = Branch.objects.all()
    users = User.objects.all()
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

        print(f"Start Date: {start_date}, End Date: {end_date}, Branch ID: {branch_id}, User ID: {user_id}, Code: {code}")

        # Base Query (Filter transactions within date range)
        report_data = Memtrans.objects.filter(ses_date__range=(start_date, end_date)).select_related('user').order_by('ses_date')

        # ✅ Fix: Branch Filtering (Use branch_code instead of ID)
        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id)
            report_data = report_data.filter(branch=selected_branch.branch_code)  # ✅ Correct filtering
            session_date = selected_branch.session_date
        else:
            selected_branch = None
            session_date = None

            if user_id:
                user = get_object_or_404(User, id=user_id)
                company_branches = Branch.objects.filter(company=user.company).values_list('branch_code', flat=True)
                report_data = report_data.filter(branch__in=company_branches)  # ✅ Filter using branch_code

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

        print(f"Total Debit: {total_debit}, Total Credit: {total_credit}")
        print(report_data.query)  # Debugging: Print the generated SQL query

    return render(request, 'reports/savings/transaction_sequence_by_ses_date.html', {
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
from transactions.models import Memtrans
from company.models import Branch
from customers.models import Customer
from .forms import TransactionForm
from django.db.models import Subquery, OuterRef, Value, CharField, Sum
from django.db.models.functions import Concat
from django.utils import timezone
from accounts.models import User

def transaction_sequence_by_trx_date(request):
    branches = Branch.objects.all()
    users = User.objects.all()
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

        # Base Query - Using sys_date instead of trx_date
        report_data = Memtrans.objects.filter(sys_date__range=(start_date, end_date)).select_related('user', 'branch').order_by('sys_date')

        # Branch Filtering - Updated to use the ForeignKey relationship
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


def transaction_journal_listing_by_ses_date(request):
    branches = Branch.objects.all()
    users = User.objects.all()
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

        # Initialize base queryset
        report_data = Memtrans.objects.all()

        # Apply date filtering
        if start_date and end_date:
            report_data = report_data.filter(ses_date__range=(start_date, end_date))

        # Apply branch filtering
        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id)
            report_data = report_data.filter(branch=selected_branch)
            session_date = selected_branch.session_date

        # Apply user filtering
        if user_id:
            report_data = report_data.filter(user_id=user_id)

        # Apply code filtering
        if code:
            report_data = report_data.filter(code=code)

        # Optimize queryset
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
        total_debit = report_data.filter(type='D').aggregate(
            total=Sum('amount'))['total'] or 0
        total_credit = report_data.filter(type='C').aggregate(
            total=Sum('amount'))['total'] or 0

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
from django.db.models import Sum, OuterRef, Subquery, CharField, Value, Q
from django.db.models.functions import Concat
from django.utils import timezone
from transactions.models import Memtrans
from customers.models import Customer 
from company.models import Branch
from accounts.models import User
from .forms import TransactionForm

def transaction_journal_listing_by_trx_date(request):
    branches = Branch.objects.select_related('company').all()
    users = User.objects.all().only('id', 'username', 'first_name')
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

        # Modified queryset - removed 'particulars' from only() clause
        report_data = Memtrans.objects.select_related(
            'user', 'branch', 'branch__company'
        ).only(
            'app_date', 'trx_no', 'code', 'gl_no', 'ac_no', 
            'amount', 'user__username',
            'branch__branch_name', 'branch__company__company_name'
        )

        # Apply filters
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

        # Rest of your view remains the same...
        report_data = report_data.annotate(
            customer_name=Subquery(
                Customer.objects.filter(
                    gl_no=OuterRef('gl_no'),
                    ac_no=OuterRef('ac_no')
                ).only('first_name', 'middle_name', 'last_name')
                .annotate(
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



from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, OuterRef, Subquery, CharField, Value, Q
from django.db.models.functions import Concat
from django.utils import timezone
from transactions.models import Memtrans
from customers.models import Customer
from company.models import Branch
from accounts.models import User
from .forms import TransactionForm

def transaction_day_sheet_by_session_date(request):
    branches = Branch.objects.select_related('company').all()
    users = User.objects.all()
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

        # Get transactions filtered by session date range
        report_data = Memtrans.objects.filter(
            ses_date__range=(start_date, end_date)
        ).select_related('user', 'branch').order_by('ses_date', 'app_date')

        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id)
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

        # Calculate totals
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

from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, OuterRef, Subquery, CharField, Value, Q
from django.db.models.functions import Concat
from django.utils import timezone
from transactions.models import Memtrans
from customers.models import Customer
from company.models import Branch
from accounts.models import User
from .forms import TransactionForm

def transaction_day_sheet_by_trx_date(request):
    branches = Branch.objects.select_related('company').all()
    users = User.objects.all()
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

        # Get transactions filtered by transaction date range
        report_data = Memtrans.objects.filter(
            app_date__range=(start_date, end_date)
        ).select_related('user', 'branch').order_by('app_date', 'ses_date')

        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id)
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

        # Calculate totals
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
    # Initial data setup with optimized queries
    branches = Branch.objects.select_related('company').all()
    users = User.objects.all()
    current_datetime = timezone.now()

    form = TransactionForm(request.POST or None)
    form.fields['branch'].queryset = branches  # Set the branch queryset

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

        # Corrected queryset construction with proper method chaining
        report_data = Memtrans.objects.filter(
            ses_date__range=(start_date, end_date)
        ).select_related(
            'user', 'branch', 'branch__company'
        ).order_by('ses_date')

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
        )

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

    return render(request, 'reports/savings/general_trx_register_by_session_date.html', context)

def general_trx_register_by_trx_date(request):
    # Fetch all branch and user records
    branches = Branch.objects.select_related('company').all()
    users = User.objects.all()
    current_datetime = timezone.now()
    
    # Initialize the form
    form = TransactionForm(request.POST or None)
    form.fields['branch'].queryset = branches  # Set the branch queryset

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
            'user', 'branch', 'branch__company'
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
    # Initialize base data
    branches = Branch.objects.all()
    users = User.objects.all()
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
                report_data = report_data.filter(branch_id=branch_id)
                context['selected_branch_obj'] = Branch.objects.get(id=branch_id)
            
            user_id = request.POST.get('user')
            if user_id:
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
    # Initialize variables with Branch instead of Company
    branches = Branch.objects.all()
    users = User.objects.all()
    accounts = Account.objects.filter(gl_no__isnull=False).values('gl_no').distinct().order_by('gl_no')
    current_datetime = timezone.now()
    
    # Initialize context with default values
    context = {
        'branches': branches,  # Changed from companies to branches
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

            # Apply filters - using Branch instead of Company
            if branch_id:
                selected_branch = get_object_or_404(Branch, id=branch_id)
                report_data = report_data.filter(branch=selected_branch)
                context['selected_branch'] = selected_branch
                context['selected_branch_obj'] = selected_branch  # For template compatibility

            if user_id:
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
    branches = Branch.objects.all()
    gl_data = Account.objects.all().values('gl_no', 'gl_name')
    gl_nos = [(item['gl_no'], item['gl_name']) for item in gl_data]

    gl_no = request.POST.get('gl_no')
    ac_no = request.POST.get('ac_no')
    start_date = request.POST.get('start_date')
    end_date = request.POST.get('end_date')
    branch_id = request.POST.get('branch')

    # Convert start_date and end_date to date objects if provided
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    transactions = []
    statement_data = []
    balance = 0
    opening_balance = 0
    total_debit = 0
    total_credit = 0
    reporting_balance = 0
    selected_branch = None
    customer = None

    if gl_no and ac_no and start_date and end_date:
        transactions = Memtrans.objects.filter(
            gl_no=gl_no,
            ac_no=ac_no,
            app_date__range=[start_date, end_date]
        )

        if branch_id:
            selected_branch = get_object_or_404(Branch, id=branch_id)
            transactions = transactions.filter(branch=selected_branch)
        else:
            selected_branch = branches.first()  # Default to the first branch if no branch is selected

        # Get customer details
        customer = get_object_or_404(Customer, gl_no=gl_no, ac_no=ac_no)

        # Calculate the opening balance (sum of all transactions before the start date)
        opening_balance_query = Memtrans.objects.filter(
            gl_no=gl_no,
            ac_no=ac_no,
            app_date__lt=start_date
        )

        if branch_id:
            opening_balance_query = opening_balance_query.filter(branch=selected_branch)

        opening_balance = opening_balance_query.aggregate(total=Sum('amount'))['total'] or 0

        transactions = transactions.order_by('app_date')

        # Start the running balance with the opening balance
        balance = opening_balance

        previous_transaction_date = None

        # Add the opening balance as the first entry in the report
        statement_data.append({
            'branch': selected_branch.branch_name if selected_branch else 'All Branches',
            'trx_date': start_date,
            'trx_no': 'Opening Balance',
            'description': 'Opening Balance',
            'debit': '',
            'credit': '',
            'balance': balance,
            'days_without_activity': '',
        })

        for transaction in transactions:
            debit = transaction.amount if transaction.amount < 0 else 0
            credit = transaction.amount if transaction.amount >= 0 else 0
            balance += credit - abs(debit)

            total_debit += abs(debit)
            total_credit += credit

            days_without_activity = 0
            if previous_transaction_date:
                days_without_activity = (transaction.app_date - previous_transaction_date).days

            statement_data.append({
                'branch': transaction.branch.branch_name if transaction.branch else '',
                'ses_date': transaction.ses_date,
                'trx_date': transaction.app_date,
                'trx_no': transaction.trx_no,
                'description': transaction.description,
                'debit': debit,
                'credit': credit,
                'balance': balance,
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
        'start_date': start_date,
        'end_date': end_date,
        'branch': selected_branch,
        'company': selected_branch.company if selected_branch else None,  # Include company through branch
        'current_datetime': timezone.now(),
        'opening_balance': opening_balance,
        'closing_balance': reporting_balance,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'reporting_balance': reporting_balance,
        'full_name': f"{customer.first_name} {customer.middle_name} {customer.last_name}" if customer else '',
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

def all_customers_account_balances(request):
    # Initialize variables
    customer_data = {}
    branches = Branch.objects.all()
    regions = Region.objects.all()
    account_officers = Account_Officer.objects.all()
    gl_accounts = Account.objects.filter(gl_no__in=Customer.objects.values('gl_no').distinct())

    # Default reporting date is the current date
    default_reporting_date = timezone.now().date()
    current_datetime = timezone.now()

    # Initialize form selections
    selected_branch = None
    selected_gl_no = None
    selected_region = None
    selected_officer = None
    reporting_date = default_reporting_date
    include_non_zero = False
    exclude_ac_no_one = False
    grand_total = 0

    if request.method == 'POST':
        # Get filters from the form
        reporting_date_str = request.POST.get('reporting_date')
        branch_id = request.POST.get('branch')
        gl_no = request.POST.get('gl_no')
        region_id = request.POST.get('region')
        officer_id = request.POST.get('credit_officer')
        include_non_zero = request.POST.get('include_non_zero') == 'on'
        exclude_ac_no_one = request.POST.get('exclude_ac_no_one') == 'on'

        if reporting_date_str:
            reporting_date = datetime.strptime(reporting_date_str, '%Y-%m-%d').date()
        else:
            reporting_date = default_reporting_date

        # Filter customers based on form input
        customers = Customer.objects.all()
        if branch_id:
            selected_branch = Branch.objects.get(id=branch_id)
            customers = customers.filter(branch=selected_branch)
        
        if gl_no:
            customers = customers.filter(gl_no=gl_no)
            selected_gl_no = gl_no
        
        if region_id:
            selected_region = Region.objects.get(id=region_id)
            customers = customers.filter(region=selected_region)
        
        if officer_id:
            selected_officer = Account_Officer.objects.get(id=officer_id)
            customers = customers.filter(credit_officer=selected_officer)

        # Create a dictionary to map GL numbers and account numbers to customer details
        customer_dict = {}
        for customer in customers:
            if exclude_ac_no_one and customer.ac_no == '1':
                continue
            customer_dict[(customer.gl_no, customer.ac_no)] = customer

        # Filter Memtrans records based on the reporting date and branch
        transactions = Memtrans.objects.filter(app_date__lte=reporting_date)
        if branch_id:
            transactions = transactions.filter(branch=selected_branch)

        gl_names = Account.objects.values_list('gl_no', 'gl_name')
        gl_name_dict = dict(gl_names)

        grand_total = 0
        for (gl_no, ac_no), customer in customer_dict.items():
            # Filter transactions for this specific customer
            customer_transactions = transactions.filter(gl_no=gl_no, ac_no=ac_no)
            account_balance = customer_transactions.aggregate(total=Sum('amount'))['total'] or 0

            if include_non_zero and account_balance == 0:
                continue

            if gl_no not in customer_data:
                customer_data[gl_no] = {
                    'gl_name': gl_name_dict.get(gl_no, 'Unknown'),
                    'customers': [],
                    'subtotal': 0,
                    'count': 0
                }

            customer_data[gl_no]['customers'].append({
                'gl_no': gl_no,
                'first_name': customer.first_name,
                'middle_name': customer.middle_name,
                'last_name': customer.last_name,
                'address': customer.address,
                'account_balance': account_balance,
            })

            customer_data[gl_no]['subtotal'] += account_balance
            customer_data[gl_no]['count'] += 1
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
        'include_non_zero': include_non_zero,
        'exclude_ac_no_one': exclude_ac_no_one,
        'grand_total': grand_total,
        'current_datetime': current_datetime,
        'company': selected_branch.company if selected_branch else None,
    }

    return render(request, 'reports/savings_report/savings_account_balance_report.html', context)




def savings_transaction_report(request):
    # Initialize filter options (available even if exception occurs)
    try:
        branches = Branch.objects.all().order_by('branch_name')
        regions = Region.objects.all()
        account_officers = Account_Officer.objects.all()
        gl_accounts = Account.objects.filter(
            gl_no__in=Customer.objects.values('gl_no').distinct()
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
            
            # Process transactions
            gl_name_dict = dict(Account.objects.values_list('gl_no', 'gl_name'))
            
            # Create customer dictionary for quick lookup
            customer_dict = {
                (c.gl_no, c.ac_no): c for c in customers 
                if not (form_data['exclude_ac_no_one'] and c.ac_no == '1')
            }
            
            # Get transactions in date range
            transactions = Memtrans.objects.filter(
                app_date__gte=form_data['start_date'],
                app_date__lte=form_data['end_date']
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
            **form_data
        }

        return render(request, 'reports/savings_report/savings_transactions_report.html', context)

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

def savings_account_listing(request):
    # Initialize variables
    start_date = end_date = None
    selected_branch = selected_gl_no = selected_region = selected_officer = None
    include_non_zero = exclude_ac_no_one = False
    customer_data = {}
    grand_total = 0

    # Default to current date if dates are not provided
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

        # Convert start_date and end_date to datetime objects
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = default_start_date

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = default_end_date

        # Filter customers based on form input
        customers = Customer.objects.all()
        if branch_id:
            selected_branch = Branch.objects.get(id=branch_id)
            customers = customers.filter(branch=selected_branch)
        else:
            selected_branch = None

        if selected_gl_no:
            customers = customers.filter(gl_no=selected_gl_no)

        if region_id:
            selected_region = Region.objects.get(id=region_id)
            customers = customers.filter(region=selected_region)

        if officer_id:
            selected_officer = Account_Officer.objects.get(id=officer_id)
            customers = customers.filter(credit_officer=selected_officer)

        # Create a dictionary to map GL numbers and account numbers to customer details
        customer_dict = {}
        for customer in customers:
            if exclude_ac_no_one and customer.ac_no == '1':
                continue
            customer_dict[(customer.gl_no, customer.ac_no)] = customer

        # Filter Memtrans records based on the date range and branch
        transactions = Memtrans.objects.filter(app_date__gte=start_date, app_date__lte=end_date)
        if branch_id:
            transactions = transactions.filter(branch=selected_branch)

        # Aggregate data by GL No and AC No
        gl_names = Account.objects.values_list('gl_no', 'gl_name')
        gl_name_dict = dict(gl_names)

        for (gl_no, ac_no), customer in customer_dict.items():
            # Filter transactions for this specific customer
            customer_transactions = transactions.filter(gl_no=gl_no, ac_no=ac_no)

            # Calculate total balance for the customer
            total_balance = customer_transactions.aggregate(total=Sum('amount'))['total'] or 0

            if include_non_zero and total_balance == 0:
                continue

            if gl_no not in customer_data:
                customer_data[gl_no] = {
                    'gl_name': gl_name_dict.get(gl_no, 'Unknown'),
                    'customers': [],
                    'subtotal': 0,
                    'count': 0
                }

            last_trx_date = customer_transactions.aggregate(latest_date=Max('app_date'))['latest_date']
            trx_dates = customer_transactions.values_list('sys_date', flat=True).distinct()

            # Calculate days without activity
            days_without_activity = 0
            current_date = start_date

            while current_date <= end_date:
                if current_date not in [trx_date.date() for trx_date in trx_dates]:
                    days_without_activity += 1
                current_date += timedelta(days=1)

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
        'branches': Branch.objects.all(),
        'gl_accounts': Account.objects.filter(gl_no__in=Customer.objects.values('gl_no').distinct()),
        'regions': Region.objects.all(),
        'account_officers': Account_Officer.objects.all(),
        'grand_total': grand_total,
        'current_datetime': timezone.now(),
        'company': selected_branch.company if selected_branch else None,
    }

    return render(request, 'reports/savings_report/savings_account_listing.html', context)

def savings_account_status(request):
    # Initialize variables
    start_date = end_date = None
    branches = Branch.objects.all()
    selected_branch = selected_gl_no = selected_region = selected_officer = None
    include_non_zero = exclude_ac_no_one = False
    account_status_data = {}
    current_datetime = timezone.now()

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

        # Convert start_date and end_date to datetime objects
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = current_datetime.date()

        # Filter transactions based on the selected criteria
        transactions = Memtrans.objects.all()

        # Filter by branch
        if branch_id:
            selected_branch = Branch.objects.get(id=branch_id)
            transactions = transactions.filter(branch=selected_branch)

        # Apply other filters
        if selected_gl_no:
            transactions = transactions.filter(gl_no=selected_gl_no)
        if region_id:
            selected_region = Region.objects.get(id=region_id)
            transactions = transactions.filter(customer__region=selected_region)
        if officer_id:
            selected_officer = Account_Officer.objects.get(id=officer_id)
            transactions = transactions.filter(customer__credit_officer=selected_officer)
        if exclude_ac_no_one:
            transactions = transactions.exclude(ac_no='1')
        if start_date:
            transactions = transactions.filter(app_date__gte=start_date)
        if end_date:
            transactions = transactions.filter(app_date__lte=end_date)

        # Aggregate data by GL No and AC No
        gl_accounts = transactions.values('gl_no').distinct()
        
        for gl in gl_accounts:
            gl_no = gl['gl_no']
            try:
                gl_name = Account.objects.get(gl_no=gl_no).gl_name
            except Account.DoesNotExist:
                gl_name = "Unknown GL"
                
            customer_transactions = transactions.filter(gl_no=gl_no)
            accounts = []
            
            for ac_no in customer_transactions.values('ac_no').distinct():
                ac_no = ac_no['ac_no']
                try:
                    customer = Customer.objects.get(gl_no=gl_no, ac_no=ac_no)
                except Customer.DoesNotExist:
                    continue
                    
                account_balance = customer_transactions.filter(ac_no=ac_no).aggregate(
                    total_balance=Sum('amount')
                )['total_balance'] or 0

                if include_non_zero and account_balance == 0:
                    continue

                last_trx = customer_transactions.filter(ac_no=ac_no).order_by('-sys_date').first()
                last_trx_date = last_trx.sys_date if last_trx else customer.reg_date
                
                days_without_activity = (current_datetime.date() - last_trx_date.date()).days
                
                accounts.append({
                    'gl_no': gl_no,
                    'ac_no': ac_no,
                    'first_name': customer.first_name,
                    'middle_name': customer.middle_name,
                    'last_name': customer.last_name,
                    'address': customer.address,
                    'account_balance': account_balance,
                    'last_trx_date': last_trx_date,
                    'days_without_activity': days_without_activity,
                    'reg_date': customer.reg_date,
                    'status': customer.get_status_display(),
                })

            if accounts:
                account_status_data[gl_no] = {
                    'gl_name': gl_name,
                    'accounts': accounts,
                    'count': len(accounts),
                    'subtotal': sum(acc['account_balance'] for acc in accounts),
                }

    context = {
        'account_status_data': account_status_data,
        'start_date': start_date,
        'end_date': end_date,
        'branches': branches,
        'selected_branch': selected_branch,
        'selected_gl_no': selected_gl_no,
        'selected_region': selected_region,
        'selected_officer': selected_officer,
        'include_non_zero': include_non_zero,
        'exclude_ac_no_one': exclude_ac_no_one,
        'gl_accounts': Account.objects.all(),
        'regions': Region.objects.all(),
        'account_officers': Account_Officer.objects.all(),
        'current_datetime': current_datetime,
        'company': selected_branch.company if selected_branch else None,
        'grand_total': sum(data['subtotal'] for data in account_status_data.values()),
    }

    return render(request, 'reports/savings_report/savings_account_status.html', context)





from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import datetime
from django.db.models import Min, Max, Sum
from django.contrib import messages


def savings_account_with_zero_balance(request):
    # Initialize filter options (available even if exception occurs)
    branches = Branch.objects.all()
    regions = Region.objects.all()
    account_officers = Account_Officer.objects.all()
    gl_accounts = Account.objects.filter(gl_no__in=Customer.objects.values('gl_no').distinct())
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
            
            # Process customers with zero balance
            gl_name_dict = dict(Account.objects.values_list('gl_no', 'gl_name'))
            
            for customer in customers:
                if form_data['exclude_ac_no_one'] and customer.ac_no == '1':
                    continue

                transactions = Memtrans.objects.filter(
                    gl_no=customer.gl_no,
                    ac_no=customer.ac_no,
                    app_date__lte=form_data['reporting_date']
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
    # Initialize filter options (available even if exception occurs)
    try:
        branches = Branch.objects.all().order_by('branch_name')
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
            
            # Process interest payments (transactions with code 'MSI')
            gl_name_dict = dict(Account.objects.values_list('gl_no', 'gl_name'))
            
            for customer in customers:
                if form_data['exclude_ac_no_one'] and customer.ac_no == '1':
                    continue

                # Get all MSI transactions for this customer
                transactions = Memtrans.objects.filter(
                    gl_no=customer.gl_no,
                    ac_no=customer.ac_no,
                    code='MSI',  # Interest payment transactions
                    app_date__lte=form_data['reporting_date']
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
            **form_data
        }

        return render(request, 'reports/savings_report/savings_interest_paid.html', context)

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in savings_interest_paid: {str(e)}", exc_info=True)
        
        # Return to form with error message and maintain filter options
        messages.error(request, f"An error occurred while generating the interest paid report: {str(e)}")
        return render(request, 'reports/savings_report/savings_interest_paid.html', {
            'branches': Branch.objects.all().order_by('branch_name'),
            'regions': Region.objects.all(),
            'account_officers': Account_Officer.objects.all(),
            'gl_accounts': Account.objects.filter(gl_no__in=Customer.objects.values('gl_no').distinct()),
            'current_datetime': timezone.now(),
        })




def savings_account_credit_balance(request):
    # Initialize filter options (available even if exception occurs)
    try:
        branches = Branch.objects.all().order_by('branch_name')
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
            
            # Process accounts with credit balance (> 0)
            gl_name_dict = dict(Account.objects.values_list('gl_no', 'gl_name'))
            
            for customer in customers:
                if form_data['exclude_ac_no_one'] and customer.ac_no == '1':
                    continue

                transactions = Memtrans.objects.filter(
                    gl_no=customer.gl_no,
                    ac_no=customer.ac_no,
                    app_date__lte=form_data['reporting_date']
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
            **form_data
        }

        return render(request, 'reports/savings_report/savings_account_with_credit_balance_report.html', context)

    except Exception as e:
        # Log the error
        logger = logging.getLogger(__name__)
        logger.error(f"Error in savings_account_credit_balance: {str(e)}", exc_info=True)
        
        # Return to form with error message
        messages.error(request, f"An error occurred while generating the credit balance report: {str(e)}")
        return render(request, 'reports/savings_report/savings_account_with_credit_balance_report.html', {
            'branches': Branch.objects.all().order_by('branch_name'),
            'regions': Region.objects.all(),
            'account_officers': Account_Officer.objects.all(),
            'gl_accounts': Account.objects.filter(gl_no__in=Customer.objects.values('gl_no').distinct()),
            'current_datetime': timezone.now(),
        })





def savings_overdrawn_account_status(request):
    # Initialize variables
    customer_data = {}
    branches = Company.objects.all()
    regions = Region.objects.all()
    account_officers = Account_Officer.objects.all()
    gl_accounts = Account.objects.filter(gl_no__in=Customer.objects.values('gl_no').distinct())
    
    # Default reporting date is the current date
    default_reporting_date = timezone.now().date()
    current_datetime = timezone.now()  # Get the current date and time
    
    # Initialize form selections
    selected_branch = None
    selected_gl_no = None
    selected_region = None
    selected_officer = None
    reporting_date = default_reporting_date
    exclude_ac_no_one = False
    grand_total = 0

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

        customers = Customer.objects.all()
        if branch_id:
            customers = customers.filter(branch=branch_id)
            selected_branch = Company.objects.get(id=branch_id)
        
        if gl_no:
            customers = customers.filter(gl_no=gl_no)
            selected_gl_no = gl_no
        
        if region_id:
            customers = customers.filter(region_id=region_id)
            selected_region = Region.objects.get(id=region_id)

        if officer_id:
            customers = customers.filter(credit_officer_id=officer_id)
            selected_officer = Account_Officer.objects.get(id=officer_id)
        
        gl_names = Account.objects.values_list('gl_no', 'gl_name')
        gl_name_dict = dict(gl_names)
        
        grand_total = 0
        for customer in customers:
            if exclude_ac_no_one and customer.ac_no == '1':
                continue

            transactions = Memtrans.objects.filter(
                gl_no=customer.gl_no,
                ac_no=customer.ac_no
            )

            # Get the earliest transaction date for the account
            earliest_transaction_date = transactions.aggregate(min_date=Min('app_date'))['min_date']

            if not earliest_transaction_date:
                earliest_transaction_date = timezone.now().date()  # Use today's date if no transactions exist

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
        'current_datetime': current_datetime,  # Add current datetime to the context
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
    branches = Branch.objects.all()
    accounts = Account.objects.all()
    error_message = None

    if request.method == 'POST':
        form = LoanLedgerCardForm(request.POST)
        if form.is_valid():
            branch = form.cleaned_data['branch']
            account = form.cleaned_data['account']
            ac_no = form.cleaned_data.get('ac_no')
            cycle = form.cleaned_data.get('cycle')

            try:
                # Retrieve the loan information
                loan = Loans.objects.get(gl_no=account.gl_no, ac_no=ac_no, cycle=cycle)
                disbursement_amount = loan.loan_amount
                total_interest = LoanHist.objects.filter(
                    branch=branch, gl_no=account.gl_no, ac_no=ac_no, cycle=cycle, trx_type='LD'
                ).aggregate(Sum('interest'))['interest__sum'] or 0
                disbursement_date = loan.disbursement_date
                num_installments = loan.num_install
                loan_officer = loan.loan_officer
                annual_interest_rate = loan.interest_rate

                # Retrieve the customer information
                customer = Customer.objects.get(gl_no=account.gl_no, ac_no=ac_no)

                # Initialize the principal and interest balances
                principal_balance = disbursement_amount
                interest_balance = total_interest

                # Query the LoanHist model to get the ledger card details
                ledger_card = LoanHist.objects.filter(
                    branch=branch, gl_no=account.gl_no, ac_no=ac_no, cycle=cycle
                ).order_by('trx_date')

                # Initialize totals
                total_payment = 0
                penalty_balance = 0

                # Iterate over ledger card entries to calculate the balances
                for entry in ledger_card:
                    total_payment += entry.principal + entry.interest + entry.penalty

                    if entry.trx_type == 'LP':
                        principal_balance += entry.principal  # Reduce principal balance by the principal payment
                        interest_balance += entry.interest  # Reduce interest balance by the interest payment
                    
                    penalty_balance += entry.penalty

                    # Calculate the total balance
                    total_balance = principal_balance + interest_balance + penalty_balance

                    # Update each entry with the calculated balances
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
                    'branches': branches,   # Pass all branches
                    'accounts': accounts,   # Pass all accounts
                    'branch': branch,       # Pass the specific branch
                    'form_submitted': True  # Flag to indicate form submission
                })

            except Loans.DoesNotExist:
                return render(request, 'reports/loans/loan_ledger_card.html', {
                    'form': form,
                    'branches': branches,
                    'accounts': accounts,
                    'form_submitted': True,
                    'error_message': 'No loan record found for the provided criteria.'
                })
            except Customer.DoesNotExist:
                return render(request, 'reports/loans/loan_ledger_card.html', {
                    'form': form,
                    'branches': branches,
                    'accounts': accounts,
                    'form_submitted': True,
                    'error_message': 'No customer record found for the provided criteria.'
                })
    else:
        form = LoanLedgerCardForm()

    return render(request, 'reports/loans/loan_ledger_card.html', {
        'form': form,
        'branches': branches,   # Pass all branches
        'accounts': accounts,   # Pass all accounts
        'form_submitted': False, # Flag to indicate form not yet submitted
        'error_message': error_message  # Pass error message to template
    })

from django.shortcuts import render
from .forms import LoanLedgerCardForm
from accounts_admin.models import Account
from loans.models import Loans, LoanHist
from customers.models import Customer
from datetime import timedelta  # Import timedelta to adjust the date


def loan_repayment_schedule(request):
    branches = Branch.objects.all()
    accounts = Account.objects.all()

    if request.method == 'POST':
        form = LoanLedgerCardForm(request.POST)
        if form.is_valid():
            branch = form.cleaned_data['branch']
            account = form.cleaned_data['account']
            ac_no = form.cleaned_data.get('ac_no')
            cycle = form.cleaned_data.get('cycle')

            try:
                # Retrieve the loan information
                loan = Loans.objects.get(gl_no=account.gl_no, ac_no=ac_no, cycle=cycle)
            except Loans.DoesNotExist:
                # If no loan is found, return an error message to the template
                return render(request, 'reports/loans/loan_repayment_schedule.html', {
                    'form': form,
                    'branches': branches,
                    'accounts': accounts,
                    'form_submitted': True,
                    'error_message': 'No loan record found for the provided details.',  # Pass error message
                })

            # Proceed with loan details if found
            disbursement_amount = loan.loan_amount
            disbursement_date = loan.disbursement_date
            num_installments = loan.num_install
            loan_officer = loan.loan_officer
            annual_interest_rate = loan.interest_rate

            # Retrieve the customer information
            customer = Customer.objects.get(gl_no=account.gl_no, ac_no=ac_no)

            # Initialize the principal balance with the disbursement amount
            principal_balance = disbursement_amount

            # Calculate total interest from entries with trx_type='LD'
            total_interest = sum(entry.interest for entry in LoanHist.objects.filter(
                branch=branch, gl_no=account.gl_no, ac_no=ac_no, cycle=cycle, trx_type='LD'
            ))

            # Initialize interest balance
            interest_balance = total_interest

            # Create an initial entry for the loan disbursement
            initial_entry = LoanHist(
                trx_date=disbursement_date - timedelta(days=1),
                trx_naration='Loan Disbursement',
                principal='0.00',
                interest=0,
                penalty=0,
                trx_type='LD',
                gl_no=account.gl_no,
                ac_no=ac_no,
                cycle=cycle,
                branch=branch,
            )

            # Query the LoanHist model to get the ledger card details
            ledger_card = list(LoanHist.objects.filter(
                branch=branch, gl_no=account.gl_no, ac_no=ac_no, cycle=cycle, trx_type='LD'
            ).order_by('trx_date'))

            # Insert the initial disbursement entry at the beginning of the ledger card
            ledger_card.insert(0, initial_entry)

            # Initialize totals
            total_payment = 0
            penalty_balance = 0
            total_balance = 0

            # Iterate over ledger card entries to calculate the balances
            for entry in ledger_card:
                if entry == initial_entry:
                    entry.principal_balance = disbursement_amount
                    entry.interest_balance = interest_balance
                    entry.penalty_balance = 0
                    entry.total_balance = disbursement_amount + interest_balance
                    entry.total_payment = 0
                else:
                    if entry.trx_type == 'LD':
                        principal_balance -= entry.principal
                        interest_balance -= entry.interest
                        if interest_balance < 0:
                            interest_balance = 0
                        if principal_balance < 0:
                            principal_balance = 0

                    penalty_balance += entry.penalty
                    total_payment += entry.principal + entry.interest + entry.penalty
                    total_balance = principal_balance + interest_balance + penalty_balance
                    entry.total_payment = total_payment
                    entry.principal_balance = principal_balance
                    entry.interest_balance = interest_balance
                    entry.penalty_balance = penalty_balance
                    entry.total_balance = total_balance

            # Pass the specific branch object to the template
            return render(request, 'reports/loans/loan_repayment_schedule.html', {
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
                'form_submitted': True  # Flag to indicate form submission
            })
    else:
        form = LoanLedgerCardForm()

    return render(request, 'reports/loans/loan_repayment_schedule.html', {
        'form': form,
        'branches': branches,
        'accounts': accounts,
        'form_submitted': False  # Flag to indicate form not yet submitted
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
    # Initialize variables
    form = LoanDisbursementReportForm(request.POST or None)
    loans = Loans.objects.none()
    context = {
        'form': form,
        'loans': loans,
        'selected_branch': None,
        'total_loan_amount': 0,
        'total_interest': 0,
        'grand_total_loan_amount': 0,
        'grand_total_interest': 0,
        'current_date': timezone.now().strftime('%d/%m/%Y'),
        'start_date': None,
        'end_date': None,
    }

    if request.method == 'POST' and form.is_valid():
        # Get cleaned form data
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        branch = form.cleaned_data.get('branch')  # Branch instance or None
        gl_no = form.cleaned_data.get('gl_no')   # GL instance or None

        # Base query with date range and select_related for performance
        loans = Loans.objects.filter(
            disbursement_date__range=[start_date, end_date]
        ).select_related('branch', 'customer', 'loan_officer')

        # Apply additional filters if provided
        if branch:
            loans = loans.filter(branch=branch)
        if gl_no:
            loans = loans.filter(gl_no=gl_no)

        # Calculate totals in a single query
        aggregates = loans.aggregate(
            total_loan=Sum('loan_amount'),
            total_interest=Sum('total_interest')
        )

        # Update context with results
        context.update({
            'loans': loans,
            'selected_branch': branch,
            'start_date': start_date,
            'end_date': end_date,
            'total_loan_amount': aggregates['total_loan'] or 0,
            'total_interest': aggregates['total_interest'] or 0,
            'grand_total_loan_amount': aggregates['total_loan'] or 0,
            'grand_total_interest': aggregates['total_interest'] or 0,
        })

    return render(request, 'reports/loans/loan_disbursement_report.html', context)

from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, F
from .forms import LoanRepaymentReportForm
from loans.models import LoanHist
from company.models import Company
from accounts.models import Account  # Assuming Account model is in accounts app
from django.contrib.auth.decorators import login_required

@login_required
def loan_repayment_report(request, loan_id=None):
    # Initialize variables
    form = LoanRepaymentReportForm(request.POST or None)
    repayments = LoanHist.objects.none()
    disbursements = LoanHist.objects.none()
    loan = None
    
    context = {
        'form': form,
        'repayments': repayments,
        'disbursements': disbursements,
        'loan': loan,
        'selected_branch': None,
        'company_name': None,
        'branch_name': None,
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

    # Get loan if ID is provided
    if loan_id:
        try:
            loan = Loans.objects.select_related(
                'customer', 'branch', 'branch__company',
                'loan_officer', 'business_sector'
            ).get(pk=loan_id)
            context['loan'] = loan
        except Loans.DoesNotExist:
            messages.error(request, "Loan not found")

    if request.method == 'POST' and form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        branch = form.cleaned_data.get('branch')
        gl_no = form.cleaned_data.get('gl_no')
        cycle = form.cleaned_data.get('cycle')

        # Base query for repayments
        repayments = LoanHist.objects.filter(
            trx_date__range=[start_date, end_date],
            trx_type='LP'  # Loan Payment
        ).select_related('branch', 'branch__company')

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
                cycle=loan.cycle
            )
        elif branch:
            repayments = repayments.filter(branch=branch)
        if gl_no:
            repayments = repayments.filter(gl_no=gl_no.gl_no)
        if cycle:
            repayments = repayments.filter(cycle=cycle)

        # Get company/branch names
        company_name = "All Companies"
        branch_name = "All Branches"
        
        if loan and loan.branch:
            company_name = loan.branch.company.company_name or "No Company"
            branch_name = loan.branch.branch_name
        elif branch:
            company_name = branch.company.company_name or "No Company"
            branch_name = branch.branch_name
        elif repayments.exists():
            first_repayment = repayments.first()
            if first_repayment.branch:
                company_name = first_repayment.branch.company.company_name or "No Company"
                branch_name = first_repayment.branch.branch_name

        # Calculate aggregates
        repayment_aggregates = repayments.aggregate(
            total_principal=Sum('principal'),
            total_interest=Sum('interest'),
            total_penalty=Sum('penalty'),
            total_paid=Sum(F('principal') + F('interest'))
        )

        # Calculate disbursement total if viewing loan
        disbursed_total = 0
        disbursement_agg = {'total_disbursed': 0}
        if loan:
            disbursement_agg = disbursements.aggregate(
                total_disbursed=Sum('principal')
            )
            disbursed_total = disbursement_agg['total_disbursed'] or 0

        # Calculate subtotals with cycle included
        subtotals = repayments.values(
            'gl_no',
            'cycle',
            'branch__company__company_name',
            'branch__branch_name'
        ).annotate(
            subtotal_principal=Sum('principal'),
            subtotal_interest=Sum('interest'),
            subtotal_penalty=Sum('penalty'),
            subtotal_paid=Sum(F('principal') + F('interest'))
        ).order_by('branch__company__company_name', 'branch__branch_name', 'gl_no', 'cycle')

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
            'company_name': company_name,
            'branch_name': branch_name,
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
