from django import forms
from django.core.validators import MinValueValidator
from decimal import Decimal

from .models import Merchant, MerchantServiceConfig


class MerchantRegistrationForm(forms.ModelForm):
    """Form for registering a new merchant (admin side)"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
        help_text="Minimum 8 characters"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    transaction_pin = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=4,
        max_length=6,
        help_text="4-6 digit PIN"
    )
    confirm_pin = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    gl_account = forms.ChoiceField(
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='GL Account',
        help_text='Select the GL account for this merchant'
    )
    
    float_gl_account = forms.ChoiceField(
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Float GL Account',
        help_text='Select the Float GL account for 9PSB wallet transactions'
    )
    
    class Meta:
        model = Merchant
        fields = [
            'merchant_name', 'merchant_type', 'business_name',
            'business_address', 'business_phone', 'business_email',
            'contact_person_name', 'contact_person_phone', 'contact_person_email',
            'state', 'lga', 'city', 'address',
            'bvn', 'nin', 'date_of_birth', 'gender',
            'daily_transaction_limit', 'single_transaction_limit', 'commission_rate'
        ]
        widgets = {
            'merchant_name': forms.TextInput(attrs={'class': 'form-control'}),
            'merchant_type': forms.Select(attrs={'class': 'form-select'}),
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'business_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'business_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_person_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'lga': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'bvn': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '11', 'placeholder': '11-digit BVN'}),
            'nin': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '11', 'placeholder': '11-digit NIN'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'daily_transaction_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'single_transaction_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts_admin.models import Account
        
        # Get GL accounts for merchant - liability accounts (current and savings)
        # Filter: GL starts with '20', exclude GLs ending with 0
        if branch:
            accounts = Account.objects.filter(
                branch=branch,
                gl_no__startswith='20'
            ).exclude(
                gl_no__endswith='0'
            ).order_by('gl_no')
        else:
            accounts = Account.all_objects.filter(
                gl_no__startswith='20'
            ).exclude(
                gl_no__endswith='0'
            ).order_by('gl_no')
        
        choices = [('', '-- Select GL Account --')]
        for acc in accounts:
            label = f"{acc.gl_no} - {acc.gl_name}"
            choices.append((acc.gl_no, label))
        
        self.fields['gl_account'].choices = choices
        self.fields['float_gl_account'].choices = choices

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        pin = cleaned_data.get('transaction_pin')
        confirm_pin = cleaned_data.get('confirm_pin')
        bvn = cleaned_data.get('bvn')
        nin = cleaned_data.get('nin')
        date_of_birth = cleaned_data.get('date_of_birth')
        gender = cleaned_data.get('gender')
        business_phone = cleaned_data.get('business_phone')
        address = cleaned_data.get('address')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        if pin and confirm_pin and pin != confirm_pin:
            raise forms.ValidationError("Transaction PINs do not match")
        
        if pin and not pin.isdigit():
            raise forms.ValidationError("Transaction PIN must be numeric")
        
        # Validate BVN/NIN - at least one is required for 9PSB wallet
        if not bvn and not nin:
            raise forms.ValidationError("Either BVN or NIN is required for wallet creation")
        
        if bvn and (len(bvn) != 11 or not bvn.isdigit()):
            raise forms.ValidationError("BVN must be exactly 11 digits")
        
        if nin and (len(nin) != 11 or not nin.isdigit()):
            raise forms.ValidationError("NIN must be exactly 11 digits")
        
        # Date of birth is required for wallet
        if not date_of_birth:
            raise forms.ValidationError("Date of Birth is required for wallet creation")
        
        # Gender is required for wallet
        if not gender:
            raise forms.ValidationError("Gender is required for wallet creation")
        
        # Phone number is required
        if not business_phone:
            raise forms.ValidationError("Business phone number is required for wallet creation")
        
        # Address is required
        if not address:
            raise forms.ValidationError("Address is required for wallet creation")
        
        return cleaned_data


class MerchantUpdateForm(forms.ModelForm):
    """Form for updating merchant details"""
    
    gl_account = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='GL Account',
        help_text='Select the GL account for this merchant'
    )
    
    float_gl_account = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Float GL Account',
        help_text='Select the Float GL account for 9PSB wallet transactions'
    )
    
    psb_wallet_account = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit 9PSB account number'}),
        label='9PSB Wallet Account',
        help_text='Enter existing 9PSB wallet account number (if already created)'
    )
    
    class Meta:
        model = Merchant
        fields = [
            'merchant_name', 'merchant_type', 'business_name',
            'business_address', 'business_phone', 'business_email',
            'contact_person_name', 'contact_person_phone', 'contact_person_email',
            'state', 'lga', 'city', 'address',
            'bvn', 'nin', 'date_of_birth', 'gender',
            'daily_transaction_limit', 'single_transaction_limit', 'commission_rate',
            'status', 'psb_wallet_account'
        ]
        widgets = {
            'merchant_name': forms.TextInput(attrs={'class': 'form-control'}),
            'merchant_type': forms.Select(attrs={'class': 'form-select'}),
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'business_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'business_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_person_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'lga': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'bvn': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '11', 'placeholder': '11-digit BVN'}),
            'nin': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '11', 'placeholder': '11-digit NIN'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'daily_transaction_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'single_transaction_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'psb_wallet_account': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit 9PSB account'}),
        }

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts_admin.models import Account
        
        # Get GL accounts for merchant - GL starts with '20', exclude GLs ending with 0
        if branch:
            accounts = Account.objects.filter(
                branch=branch,
                gl_no__startswith='20'
            ).exclude(
                gl_no__endswith='0'
            ).order_by('gl_no')
        else:
            accounts = Account.all_objects.filter(
                gl_no__startswith='20'
            ).exclude(
                gl_no__endswith='0'
            ).order_by('gl_no')
        
        choices = [('', '-- Select GL Account --')]
        for acc in accounts:
            label = f"{acc.gl_no} - {acc.gl_name}"
            choices.append((acc.gl_no, label))
        
        self.fields['gl_account'].choices = choices
        self.fields['float_gl_account'].choices = choices
        
        # Set initial value if merchant already has gl_no
        if self.instance and self.instance.pk and self.instance.gl_no:
            self.fields['gl_account'].initial = self.instance.gl_no
        
        # Set initial value for float GL account
        if self.instance and self.instance.pk and self.instance.float_gl_no:
            self.fields['float_gl_account'].initial = self.instance.float_gl_no


class MerchantLoginForm(forms.Form):
    """Form for merchant portal login"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Merchant ID'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )


class MerchantPinChangeForm(forms.Form):
    """Form for changing merchant transaction PIN"""
    current_pin = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=4,
        max_length=6
    )
    new_pin = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=4,
        max_length=6
    )
    confirm_pin = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=4,
        max_length=6
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_pin = cleaned_data.get('new_pin')
        confirm_pin = cleaned_data.get('confirm_pin')
        
        if new_pin and confirm_pin and new_pin != confirm_pin:
            raise forms.ValidationError("New PINs do not match")
        
        if new_pin and not new_pin.isdigit():
            raise forms.ValidationError("PIN must be numeric")
        
        return cleaned_data


# ========== Transaction Forms ==========

class CustomerRegistrationForm(forms.Form):
    """Form for merchant to register a new customer"""
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    middle_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_no = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        required=False
    )
    dob = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    gender = forms.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        required=False
    )
    bvn = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        min_length=11,
        max_length=11,
        required=False
    )
    account_type = forms.CharField(
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    initial_deposit = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        min_value=0,
        required=False
    )
    transaction_pin = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Enter your merchant PIN to confirm"
    )


class DepositForm(forms.Form):
    """Form for customer deposit"""

    customer_account = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter GL/AC number'
        }),
        error_messages={
            'max_length': 'Account number must not exceed 20 characters'
        }
    )

    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        validators=[MinValueValidator(Decimal('100.00'))]
    )

    narration = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={
            'max_length': 'Narration must not exceed 200 characters'
        }
    )


class WithdrawalForm(forms.Form):
    """Form for customer withdrawal"""
    customer_account = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter GL/AC number'})
    )
    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        validators=[MinValueValidator(Decimal('100.00'))]
    )
    narration = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )


class TransferForm(forms.Form):
    """Form for fund transfer"""
    beneficiary_account = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    beneficiary_bank = forms.CharField(
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        validators=[MinValueValidator(Decimal('100.00'))]
    )
    narration = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        max_length=100
    )


class InternalTransferForm(forms.Form):
    """Form for FinanceFlex internal transfer"""
    beneficiary_account = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter GL/AC number'})
    )
    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        validators=[MinValueValidator(Decimal('100.00'))]
    )
    narration = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        max_length=100
    )


class BillPaymentForm(forms.Form):
    """Form for bill payment"""
    BILLER_CATEGORIES = [
        ('electricity', 'Electricity'),
        ('cable_tv', 'Cable TV'),
        ('internet', 'Internet'),
        ('water', 'Water'),
        ('betting', 'Betting'),
        ('education', 'Education'),
    ]
    
    category = forms.ChoiceField(
        choices=BILLER_CATEGORIES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    biller = forms.CharField(
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    customer_id = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Meter/Smart card number'})
    )
    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        validators=[MinValueValidator(Decimal('100.00'))]
    )


class AirtimeForm(forms.Form):
    """Form for airtime purchase"""
    NETWORKS = [
        ('mtn', 'MTN'),
        ('glo', 'GLO'),
        ('airtel', 'Airtel'),
        ('9mobile', '9Mobile'),
    ]
    
    network = forms.ChoiceField(
        choices=NETWORKS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08012345678'})
    )
    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        validators=[MinValueValidator(Decimal('50.00'))]
    )


class DataForm(forms.Form):
    """Form for data purchase"""
    NETWORKS = [
        ('mtn', 'MTN'),
        ('glo', 'GLO'),
        ('airtel', 'Airtel'),
        ('9mobile', '9Mobile'),
    ]
    
    network = forms.ChoiceField(
        choices=NETWORKS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08012345678'})
    )
    data_plan = forms.CharField(
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class MerchantServiceConfigForm(forms.ModelForm):
    """Form for configuring merchant services"""
    
    class Meta:
        model = MerchantServiceConfig
        fields = [
            'service_type', 'is_enabled', 'charge_type', 'charge_value',
            'min_charge', 'max_charge', 'commission_type', 'commission_value',
            'min_amount', 'max_amount'
        ]
        widgets = {
            'service_type': forms.Select(attrs={'class': 'form-select'}),
            'is_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'charge_type': forms.Select(attrs={'class': 'form-select'}),
            'charge_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_charge': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_charge': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'commission_type': forms.Select(attrs={'class': 'form-select'}),
            'commission_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_amount': forms.NumberInput(attrs={'class': 'form-control'}),
        }
