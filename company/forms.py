from django import forms
from .models import Company, Branch

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = '__all__'




import random
from django import forms
from .models import Branch

class BranchForm(forms.ModelForm):
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        empty_label="-- Select Company --"
    )
    session_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    system_date_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )

    max_customers = forms.IntegerField(
        min_value=0,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0 = Unlimited'}),
        help_text="Maximum customers allowed. 0 = unlimited."
    )

    # Feature flags
    can_fixed_deposit = forms.BooleanField(
        required=False, initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Enable Fixed Deposit feature"
    )
    can_loans = forms.BooleanField(
        required=False, initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Enable Loans feature"
    )
    can_transfers = forms.BooleanField(
        required=False, initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Enable Fund Transfers feature"
    )
    can_fixed_assets = forms.BooleanField(
        required=False, initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Enable Fixed Assets feature"
    )
    can_mobile_banking = forms.BooleanField(
        required=False, initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Enable Mobile Banking feature"
    )
    can_sms_alerts = forms.BooleanField(
        required=False, initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Enable SMS Alerts feature"
    )

    class Meta:
        model = Branch
        fields = [
            'company', 'branch_code', 'branch_name', 'logo', 'address',
            'cac_number', 'license_number', 'company_type', 'bvn_number', 'plan',
            'session_date', 'system_date_date', 'session_status', 'phone_number',
            'max_customers',
            'can_fixed_deposit', 'can_loans', 'can_transfers', 
            'can_fixed_assets', 'can_mobile_banking', 'can_sms_alerts'
        ]
        widgets = {
            'branch_name': forms.TextInput(attrs={'placeholder': 'e.g. Akobo Branch'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Full branch address'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['branch_code'].initial = self.generate_branch_code()

        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control')

    def generate_branch_code(self):
        existing_codes = Branch.objects.values_list('branch_code', flat=True)
        while True:
            code = str(random.randint(1000, 9999))
            if code not in existing_codes:
                return code




from django import forms
from .models import Company, Branch

class EndSession(forms.ModelForm):
    class Meta:
        model = Branch  # Change this to the Branch model
        fields = ['session_date', 'session_status']

    SESSION_STATUS_CHOICES = (
        ('Open', 'Open'),
        ('Closed', 'Closed'),
    )
    session_status = forms.ChoiceField(choices=SESSION_STATUS_CHOICES, widget=forms.Select)
