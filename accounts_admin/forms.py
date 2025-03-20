# chartofaccounts/forms.py
from django import forms

from accounts.models import User
from .models import Account, Account_Officer, Business_Sector, Category, Id_card_type, Product_type, Region


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['gl_name','gl_no','currency','account_type','double_entry_type','header','is_non_financial']


class CreditOfficerForm(forms.ModelForm):
    class Meta:
        model = Account_Officer
        fields = '__all__'


class RegionForm(forms.ModelForm):
    class Meta:
        model = Region
        fields = '__all__'


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = '__all__'


class IdcardTypeForm(forms.ModelForm):
    
    class Meta:
        model = Id_card_type
        fields = '__all__'

class BusinessSectorForm(forms.ModelForm):
    class Meta:
        model = Business_Sector
        fields = '__all__'


# forms.py

# forms.py
from django import forms
from .models import Product_type

class ProductTypeForm(forms.ModelForm):
    class Meta:
        model = Product_type
        fields = ['internal_type','branch']


# forms.py
from django import forms
from .models import Account

class UpdateProductTypeForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['account', 'product_type','branch']
    
    account = forms.ModelChoiceField(queryset=Account.objects.all(), label="Select Account", required=False)



class loanProductSettingsForm(forms.ModelForm):


    class Meta:
        model = Account
        
        fields = [
             
            'interest_gl',
            'interest_ac',
            'pen_gl_no',
            'pen_ac_no',
            'prov_cr_gl_no',
            'prov_cr_ac_no',
            'prov_dr_gl_no',
            'prov_dr_ac_no',
            'writ_off_dr_gl_no',
            'writ_off_dr_ac_no',
            'writ_off_cr_gl_no',
            'writ_off_cr_ac_no',
            'loan_com_gl_no',
            'loan_com_ac_no',
            'int_to_recev_gl_dr',
            'int_to_recev_ac_dr',
            'unearned_int_inc_gl',
            'unearned_int_inc_ac',
            'loan_com_gl_vat',
            'loan_com_ac_vat',
            'loan_proc_gl_vat',
            'loan_proc_ac_vat',
            'loan_appl_gl_vat',
            'loan_appl_ac_vat',
            'loan_commit_gl_vat',
            'loan_commit_ac_vat',
            'fixed_dep_int_gl_no',
            'fixed_dep_int_ac_no',
            'branch',
        ]
        

    


from django import forms
from transactions.models import InterestRate

class InterestRateForm(forms.ModelForm):
    class Meta:
        model = InterestRate
        fields = ['gl_no', 'rate', 'glno_debit_account', 'acno_debit_account','branch']
        widgets = {
             'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),  # Allows decimal input
            'gl_no': forms.TextInput(attrs={'class': 'form-control'}),
            'glno_debit_account': forms.TextInput(attrs={'class': 'form-control'}),
            'acno_debit_account': forms.TextInput(attrs={'class': 'form-control'}),
        }


# loans/forms.py

from django import forms
from .models import LoanProvision

class LoanProvisionForm(forms.ModelForm):
    class Meta:
        model = LoanProvision
        fields = ['name', 'min_days', 'max_days', 'rate','branch']

LoanProvisionFormSet = forms.modelformset_factory(
    LoanProvision,
    form=LoanProvisionForm,
    extra=1  # Initially, only one form is displayed
)
