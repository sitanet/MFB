from django import forms

from transactions.models import Memtrans

class MemtransForm(forms.ModelForm):
    gl_no_cashier = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    ac_no_cashier = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    gl_no = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    ac_no = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    
    disbursement_date = forms.DateField(required=False)

    label_select = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    label_there = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    class Meta:
        model = Memtrans
        fields = ['branch', 'gl_no', 'ac_no', 'cycle','app_date', 'ses_date', 'amount', 'gl_no_cashier', 'ac_no_cashier', 'description','label_select','label_there','disbursement_date']

# forms.py
from django import forms

class SeekAndUpdateForm(forms.Form):
    trx_no = forms.CharField(label='Transaction Number', max_length=100)
   


# forms.py

from django import forms
from .models import Memtrans

from django import forms
from .models import Memtrans

class UploadFileForm(forms.Form):
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control-file',
        })
    )

class MemtransPreviewForm(forms.ModelForm):
    customer_name = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Customer Name',
        })
    )

    class Meta:
        model = Memtrans
        fields = ['branch', 'gl_no', 'ac_no', 'trx_no', 'ses_date', 'app_date', 'amount', 'description', 'error', 'type', 'customer_name']
        widgets = {
            'branch': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Branch'}),
            'gl_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GL No'}),
            'ac_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account No'}),
            'trx_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction No'}),
            'ses_date': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'Session Date'}),
            'app_date': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'Application Date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description'}),
            'error': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Error'}),
            'type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Type'}),
        }



# forms.py
from django import forms
from .models import InterestRate

class InterestRateForm(forms.ModelForm):
    class Meta:
        model = InterestRate
        fields = ['gl_no', 'rate', 'glno_debit_account', 'acno_debit_account','ses_date']
        widgets = {
             'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),  # Allows decimal input
            'gl_no': forms.TextInput(attrs={'class': 'form-control'}),
            'glno_debit_account': forms.TextInput(attrs={'class': 'form-control'}),
            'acno_debit_account': forms.TextInput(attrs={'class': 'form-control'}),
        }



