from django import forms

from accounts_admin.models import Account
from .models import Customer


class CustomerForm(forms.ModelForm):
    sms = forms.BooleanField(required=False, label="Send SMS Notification", initial=False)
    class Meta:
        model = Customer
        fields = '__all__'
        widgets = {
            'photo': forms.FileInput(attrs={'accept': 'image/*'}),
            'sign': forms.FileInput(attrs={'accept': 'image/*'}),
            'gl_no': forms.TextInput(attrs={'readonly': 'readonly'}),
            'ac_no': forms.TextInput(attrs={'readonly': 'readonly'}),
        }



class InternalAccountForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'
    





    # forms.py
from django import forms
from .models import FixedDepositAccount
from customers.models import Customer
from company.models import Branch

class FixedDepositAccountForm(forms.ModelForm):
    class Meta:
        model = FixedDepositAccount
        fields = ['customer', 'fixed_gl_no', 'fixed_ac_no', 'branch']








# forms.py

from django import forms
from .models import Group, Customer

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['group_name', 'group_code', 'description']


# groups/forms.py

from django import forms
from .models import Group, Customer

class AssignCustomerForm(forms.Form):
    group = forms.ModelChoiceField(queryset=Group.objects.all(), label='Select Group')
    customer = forms.ModelChoiceField(queryset=Customer.objects.all(), label='Select Customer')
