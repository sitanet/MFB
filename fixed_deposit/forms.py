from django import forms
from decimal import Decimal
from .models import FixedDeposit, FDProduct, FDInterestSlab


class FixedDepositForm(forms.ModelForm):
    """Enhanced Fixed Deposit Form with all standard MFB features"""
    
    class Meta:
        model = FixedDeposit
        fields = [
            "customer", "cust_gl_no", "cust_ac_no", "fixed_gl_no", "fixed_ac_no",
            "deposit_amount", "interest_rate", "tenure_months", "start_date", "cycle",
            "interest_type", "compound_frequency", "interest_option",
            "auto_renewal", "tds_applicable", "tds_rate",
            "is_senior_citizen", "senior_citizen_extra_rate",
            "nominee_name", "nominee_relationship", "nominee_phone",
            "nominee_address", "nominee_id_type", "nominee_id_number",
            "remarks", "fd_product"
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'nominee_address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'deposit_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'tenure_months': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'tds_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'senior_citizen_extra_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make optional fields not required
        optional_fields = [
            'cycle', 'compound_frequency', 'tds_rate', 'senior_citizen_extra_rate',
            'nominee_name', 'nominee_relationship', 'nominee_phone',
            'nominee_address', 'nominee_id_type', 'nominee_id_number',
            'remarks', 'fd_product', 'interest_type', 'interest_option',
            'auto_renewal', 'tds_applicable', 'is_senior_citizen'
        ]
        for field in optional_fields:
            if field in self.fields:
                self.fields[field].required = False
        
        # Set default values
        if 'interest_type' in self.fields:
            self.fields['interest_type'].initial = 'simple'
        if 'interest_option' in self.fields:
            self.fields['interest_option'].initial = 'end'
        
        # Add CSS classes
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        deposit_amount = cleaned_data.get('deposit_amount')
        tenure_months = cleaned_data.get('tenure_months')
        interest_type = cleaned_data.get('interest_type')
        compound_frequency = cleaned_data.get('compound_frequency')
        fd_product = cleaned_data.get('fd_product')

        # Validate against FD Product limits if selected
        if fd_product:
            if deposit_amount and deposit_amount < fd_product.min_deposit:
                raise forms.ValidationError(
                    f"Minimum deposit for {fd_product.product_name} is {fd_product.min_deposit}"
                )
            if fd_product.max_deposit and deposit_amount and deposit_amount > fd_product.max_deposit:
                raise forms.ValidationError(
                    f"Maximum deposit for {fd_product.product_name} is {fd_product.max_deposit}"
                )
            if tenure_months and tenure_months < fd_product.min_tenure_months:
                raise forms.ValidationError(
                    f"Minimum tenure for {fd_product.product_name} is {fd_product.min_tenure_months} months"
                )
            if tenure_months and tenure_months > fd_product.max_tenure_months:
                raise forms.ValidationError(
                    f"Maximum tenure for {fd_product.product_name} is {fd_product.max_tenure_months} months"
                )

        # Validate compound frequency is set for compound interest
        if interest_type == 'compound' and not compound_frequency:
            raise forms.ValidationError(
                "Please select compounding frequency for compound interest"
            )

        return cleaned_data


class FixedDepositWithdrawalForm(forms.ModelForm):
    """Enhanced withdrawal form with premature withdrawal support"""
    
    class Meta:
        model = FixedDeposit
        fields = ["customer", "cust_gl_no", "cust_ac_no", "fixed_gl_no", "fixed_ac_no", "deposit_amount"]

    withdraw_amount = forms.DecimalField(
        max_digits=15, decimal_places=2, required=True, label="Withdrawal Amount",
        help_text="Enter the amount to withdraw from the fixed deposit.",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'})
    )

    interest_amount = forms.DecimalField(
        max_digits=15, decimal_places=2, required=True, label="Interest Amount",
        help_text="Interest amount to be paid.",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'})
    )

    penalty_amount = forms.DecimalField(
        max_digits=15, decimal_places=2, required=False, label="Penalty Amount",
        help_text="Penalty for premature withdrawal (if applicable).",
        initial=0.00,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01', 'readonly': 'readonly'})
    )

    tds_amount = forms.DecimalField(
        max_digits=15, decimal_places=2, required=False, label="TDS Amount",
        help_text="Tax deducted at source (if applicable).",
        initial=0.00,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01', 'readonly': 'readonly'})
    )

    net_payable = forms.DecimalField(
        max_digits=15, decimal_places=2, required=False, label="Net Payable",
        help_text="Total amount payable after deductions.",
        initial=0.00,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )

    is_premature = forms.BooleanField(
        required=False, label="Premature Withdrawal",
        help_text="Check if withdrawing before maturity date.",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    withdrawal_remarks = forms.CharField(
        required=False, label="Remarks",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make pre-filled fields hidden
        for field in ["customer", "cust_gl_no", "cust_ac_no", "fixed_gl_no", "fixed_ac_no", "deposit_amount"]:
            self.fields[field].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        withdraw_amount = cleaned_data.get("withdraw_amount")
        deposit_amount = cleaned_data.get("deposit_amount")
        interest_amount = cleaned_data.get("interest_amount")
        penalty_amount = cleaned_data.get("penalty_amount") or Decimal("0.00")

        # Validate withdrawal amount
        if withdraw_amount is not None and deposit_amount is not None:
            if withdraw_amount > deposit_amount:
                raise forms.ValidationError("Withdrawal amount cannot exceed the deposited amount.")
            if withdraw_amount <= 0:
                raise forms.ValidationError("Withdrawal amount must be greater than zero.")

        # Validate interest amount
        if interest_amount is not None and interest_amount < 0:
            raise forms.ValidationError("Interest amount cannot be negative.")

        # Calculate net payable
        if withdraw_amount and interest_amount is not None:
            tds = cleaned_data.get("tds_amount") or Decimal("0.00")
            net = withdraw_amount + interest_amount - penalty_amount - tds
            cleaned_data["net_payable"] = net

        return cleaned_data


class FDRenewalForm(forms.Form):
    """Form for FD renewal"""
    
    RENEWAL_TYPE_CHOICES = [
        ("principal_only", "Principal Only"),
        ("principal_interest", "Principal + Interest"),
        ("custom", "Custom Amount"),
    ]
    
    renewal_type = forms.ChoiceField(
        choices=RENEWAL_TYPE_CHOICES,
        initial="principal_interest",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    custom_amount = forms.DecimalField(
        max_digits=15, decimal_places=2, required=False,
        label="Custom Amount (if applicable)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'})
    )
    
    new_tenure_months = forms.IntegerField(
        min_value=1, label="New Tenure (Months)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )
    
    new_interest_rate = forms.DecimalField(
        max_digits=5, decimal_places=2, label="New Interest Rate (%)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'})
    )
    
    new_interest_type = forms.ChoiceField(
        choices=FixedDeposit.INTEREST_TYPE_CHOICES,
        initial="simple",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

    def clean(self):
        cleaned_data = super().clean()
        renewal_type = cleaned_data.get('renewal_type')
        custom_amount = cleaned_data.get('custom_amount')
        
        if renewal_type == 'custom' and not custom_amount:
            raise forms.ValidationError("Please enter custom amount for custom renewal type")
        
        return cleaned_data


class FDProductForm(forms.ModelForm):
    """Form for FD Product configuration"""
    
    class Meta:
        model = FDProduct
        fields = [
            'product_name', 'product_code', 'min_deposit', 'max_deposit',
            'min_tenure_months', 'max_tenure_months', 'base_interest_rate',
            'senior_citizen_extra_rate', 'interest_type', 'compound_frequency',
            'allow_premature_withdrawal', 'premature_penalty_rate', 'min_lock_in_days',
            'allow_auto_renewal', 'tds_applicable', 'tds_rate', 'tds_threshold',
            'allow_loan_against_fd', 'max_loan_percentage', 'is_active'
        ]
        widgets = {
            'product_name': forms.TextInput(attrs={'class': 'form-control'}),
            'product_code': forms.TextInput(attrs={'class': 'form-control'}),
            'min_deposit': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'max_deposit': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'min_tenure_months': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_tenure_months': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'base_interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'senior_citizen_extra_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'premature_penalty_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'min_lock_in_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'tds_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'tds_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'max_loan_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
        }


class LienMarkingForm(forms.Form):
    """Form for marking/removing lien on FD"""
    
    ACTION_CHOICES = [
        ("mark", "Mark Lien"),
        ("remove", "Remove Lien"),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    lien_amount = forms.DecimalField(
        max_digits=15, decimal_places=2, required=False,
        label="Lien Amount",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'})
    )
    
    loan_reference = forms.CharField(
        max_length=100, required=False,
        label="Loan Reference Number",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        lien_amount = cleaned_data.get('lien_amount')
        
        if action == 'mark' and not lien_amount:
            raise forms.ValidationError("Please enter lien amount to mark")
        
        return cleaned_data