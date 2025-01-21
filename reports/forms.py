from datetime import timezone
from django import forms

class StatementForm(forms.Form):
    start_date = forms.DateField(label='Start Date', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(label='End Date', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    gl_no = forms.CharField(label='GL Number', max_length=6, required=False)
    ac_no = forms.CharField(label='Account Number', max_length=6, required=False)



from django import forms
from company.models import Company, Branch

class TrialBalanceForm(forms.Form):
    start_date = forms.DateField()
    end_date = forms.DateField()
    branch = forms.ModelChoiceField(queryset=Company.objects.all(), required=False)



from django import forms
from company.models import Company

class BalanceSheetForm(forms.Form):
    start_date = forms.DateField()
    end_date = forms.DateField()
    branch = forms.ModelChoiceField(queryset=Company.objects.all(), required=False)





from django import forms
from company.models import Company
from accounts.models import User
from accounts_admin.models import Account

class TransactionForm(forms.Form):
    start_date = forms.DateField(required=True, widget=forms.TextInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=True, widget=forms.TextInput(attrs={'type': 'date'}))
    branch = forms.ModelChoiceField(queryset=Company.objects.all(), required=False)
    user = forms.ModelChoiceField(queryset=User.objects.all(), required=False)
    code = forms.ChoiceField(
        choices=[
            ('DP', 'Deposit'),
            ('WD', 'Withdrawal'),
            ('GL', 'General Journal'),
            ('LD', 'Loan Disbursement')
        ],
        required=False,
        widget=forms.Select(attrs={'placeholder': 'Select Code'})
    )
    gl_no = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        required=False,
        widget=forms.Select(attrs={'placeholder': 'Select GL Number'})
    )
    ac_no = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'number', 'placeholder': 'Enter Account Number'})
    )




from django import forms
from customers.models import Customer

# forms.py

from django import forms
from accounts_admin.models import Account
from loans.models import Loans

# forms.py

from django import forms
from accounts_admin.models import Account

# forms.py

from django import forms
from company.models import Company
from accounts_admin.models import  Account



class LoanLedgerCardForm(forms.Form):
    branch = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        label='Branch',
        empty_label='Select a Branch',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        label='Account',
        empty_label='Select an Account',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    ac_no = forms.CharField(
        max_length=20, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    cycle = forms.CharField(
        max_length=20, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the account field to display gl_no and gl_name in the dropdown
        self.fields['account'].label_from_instance = lambda obj: f"{obj.gl_no} - {obj.gl_name}"





from django.utils import timezone
from django import forms
from accounts_admin.models import Company, Region, Account_Officer, Business_Sector

from django import forms
from company.models import Company
from accounts_admin.models import Account





class LoanDisbursementReportForm(forms.Form):
    start_date = forms.DateField(widget=forms.TextInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.TextInput(attrs={'type': 'date'}))
    
    # Filtering branches from the Company model
    branch = forms.ModelChoiceField(queryset=Company.objects.all(), required=False, label="Branch")
    
    # Filtering GL numbers from the Account model
    gl_no = forms.ModelChoiceField(queryset=Account.objects.all(), required=False, label="GL Number")





from django import forms

class LoanRepaymentReportForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    branch = forms.ModelChoiceField(queryset=Company.objects.all(), required=False, empty_label="All Branches")
    gl_no = forms.ModelChoiceField(queryset=Account.objects.all(), required=False, empty_label="All Products")





# forms.py



# class LoanOutstandingBalanceForm(forms.Form):
#     reporting_date = forms.DateField(
#         label='Reporting Date',
#         widget=forms.TextInput(attrs={'type': 'date'}),
#         required=True
#     )
#     branch = forms.ChoiceField(
#         choices=[('', 'All')] + [(branch.branch_code, branch.branch_name) for branch in Branch.objects.all()],
#         required=False,
#         label='Branch'
#     )
#     gl_no = forms.ChoiceField(
#         choices=[('', 'All')] + [(account.gl_no, account.gl_no) for account in Account.objects.all()],
#         required=False,
#         label='Product (GL No)'
#     )

class LoanOutstandingBalanceForm(forms.Form):
    reporting_date = forms.DateField(
        label='Reporting Date',
        widget=forms.TextInput(attrs={'type': 'date'}),
        required=True
    )
    branch = forms.ChoiceField(
        choices=[],  # Initialize with empty choices
        required=False,
        label='Branch'
    )
    gl_no = forms.ChoiceField(
        choices=[],  # Initialize with empty choices
        required=False,
        label='Product (GL No)'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].choices = [('', 'All')] + [
            (branch.branch_code, branch.branch_name) for branch in Branch.objects.all()
        ]
        self.fields['gl_no'].choices = [('', 'All')] + [
            (account.gl_no, account.gl_no) for account in Account.objects.all()
        ]



# forms.py
from django import forms
from datetime import date

class ReportingDateForm(forms.Form):
    reporting_date = forms.DateField(
        widget=forms.SelectDateWidget,
        label='Reporting Date',
        required=True,
        initial=date.today  # Use datetime.date.today instead of forms.fields.today
    )
