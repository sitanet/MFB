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
    branch = forms.ModelChoiceField(queryset=Branch.objects.all(), required=False)



from django import forms
from company.models import Company

class BalanceSheetForm(forms.Form):
    start_date = forms.DateField()
    end_date = forms.DateField()
    branch = forms.ModelChoiceField(queryset=Company.objects.all(), required=False)


from django import forms
from company.models import Branch
from accounts.models import User
from accounts_admin.models import Account

class TransactionForm(forms.Form):
    start_date = forms.DateField(
        required=True, widget=forms.TextInput(attrs={'type': 'date'})
    )
    end_date = forms.DateField(
        required=True, widget=forms.TextInput(attrs={'type': 'date'})
    )

    branch = forms.ModelChoiceField(
        queryset=Branch.objects.none(),
        required=False
    )
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False
    )
    
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

    def __init__(self, *args, **kwargs):
        branches = kwargs.pop('branches', Branch.objects.none())
        users = kwargs.pop('users', User.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = branches
        self.fields['branch'].empty_label = "All Branches"

        self.fields['user'].queryset = users
        self.fields['user'].empty_label = "All Users"




# reports/forms.py
from django import forms
from django.utils import timezone
from company.models import Branch
from accounts.models import User

class TransactionSequenceReportForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now().replace(day=1)
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now()
    )
    branches = forms.ModelMultipleChoiceField(
        queryset=Branch.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )
    TRANSACTION_TYPES = [
        ('', 'All Types'),
        ('N', 'Normal'),
        ('S', 'Savings'),
        ('L', 'Loan'),
        ('D', 'Deposit'),
        ('W', 'Withdrawal'),
    ]
    transaction_type = forms.ChoiceField(
        choices=TRANSACTION_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
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
from company.models import Branch
from accounts_admin.models import Account

from django import forms
from company.models import Branch
from accounts_admin.models import Account

class LoanLedgerCardForm(forms.Form):
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),  
        label='Branch',
        empty_label='Select a Branch',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(gl_no__startswith="104"),  # ✅ Only GL starting with 104
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
        # ✅ Make account labels more descriptive
        self.fields['account'].label_from_instance = (
            lambda obj: f"{obj.gl_no} - {obj.gl_name}"
        )



from django.utils import timezone
from django import forms
from accounts_admin.models import Company, Region, Account_Officer, Business_Sector

from django import forms
from company.models import Company
from accounts_admin.models import Account



from django import forms
from company.models import Branch
from accounts_admin.models import Account
from django.db.models import Q


from django import forms
from company.models import Branch
from accounts_admin.models import Account
class LoanDisbursementReportForm(forms.Form):
    reporting_date = forms.DateField(
        label='Reporting Date',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=True
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.none(),
        label='Branch',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="All Branches"
    )
    gl_no = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        label='GL Account',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="All GL Accounts"
    )

    def __init__(self, *args, user_branch=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user_branch:
            # 🔹 Restrict to user's branch and GL accounts that start with 104
            self.fields['branch'].queryset = Branch.objects.filter(id=user_branch.id)
            self.fields['gl_no'].queryset = Account.objects.filter(
                branch=user_branch,
                gl_no__startswith="104"
            ).order_by('gl_no')
        else:
            # 🔹 Show all branches and only GLs that start with 104
            self.fields['branch'].queryset = Branch.objects.all().order_by('branch_name')
            self.fields['gl_no'].queryset = Account.objects.filter(
                gl_no__startswith="104"
            ).order_by('gl_no')

        # Format GL account display
        self.fields['gl_no'].label_from_instance = lambda obj: f"{obj.gl_no} - {obj.gl_name}"



from django import forms

class LoanRepaymentReportForm(forms.Form):
    start_date = forms.DateField(
        label='Start Date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.none(),
        label='Branch',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    gl_no = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        label='GL Account',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cycle = forms.IntegerField(
        label='Cycle',
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, user_branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if user_branch:
            # Filter branches by the same company as the user's branch
            self.fields['branch'].queryset = Branch.objects.filter(
                company_name=user_branch.company_name
            ).order_by('branch_name')
            
            # Filter GL accounts by the same company
            self.fields['gl_no'].queryset = Account.objects.filter(
                branch__company_name=user_branch.company_name
            ).order_by('gl_no')


class LoanTillSheetForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Start Date'
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='End Date'
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all().order_by('branch_name'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label='Branch',
        empty_label="All Branches"
    )
    gl_no = forms.ModelChoiceField(
        queryset=Account.objects.all().order_by('gl_name'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label='GL Account',
        empty_label="All Accounts"
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date must be after start date")
        
        return cleaned_data
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
