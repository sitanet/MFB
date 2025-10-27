# ninepsb/forms.py
from django import forms

class BankFetchForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        label="Confirm you want to fetch the latest bank list from 9PSB"
    )





from django import forms
from ninepsb.models import PsbBank


class AccountValidationForm(forms.Form):
    bank_code = forms.ChoiceField(
        label="Bank Name",
        choices=[],  # choices will be loaded dynamically in __init__
        widget=forms.Select(attrs={"class": "form-control"})
    )
    account_number = forms.CharField(
        max_length=15,
        label="Account Number",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically load all active banks from DB
        self.fields['bank_code'].choices = [
            (b.bank_code, b.bank_name) for b in PsbBank.objects.filter(active=True).order_by('bank_name')
        ]





from django import forms

class FundTransferForm(forms.Form):
    sender_account = forms.CharField(max_length=20, label="Sender Account Number")
    sender_name = forms.CharField(max_length=100, label="Sender Name")
    recipient_account = forms.CharField(max_length=20, label="Recipient Account Number")
    recipient_name = forms.CharField(max_length=100, label="Recipient Name")
    bank_code = forms.CharField(max_length=10, label="Bank Code")
    amount = forms.DecimalField(max_digits=12, decimal_places=2)
    description = forms.CharField(max_length=255, required=False)