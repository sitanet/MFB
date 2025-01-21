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
    