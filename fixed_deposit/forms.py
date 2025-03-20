from django import forms
from .models import FixedDeposit

class FixedDepositForm(forms.ModelForm):
    class Meta:
        model = FixedDeposit  # Ensure it's linked to the correct model
        fields = ["customer", "cust_gl_no","cust_ac_no","fixed_gl_no", "fixed_ac_no", "deposit_amount", "interest_rate", "tenure_months", "start_date"]




from django import forms
from .models import FixedDeposit

class FixedDepositWithdrawalForm(forms.ModelForm):
    class Meta:
        model = FixedDeposit
        fields = ["customer", "cust_gl_no", "cust_ac_no", "fixed_gl_no", "fixed_ac_no", "deposit_amount"]

    withdraw_amount = forms.DecimalField(
        max_digits=12, decimal_places=2, required=True, label="Withdrawal Amount",
        help_text="Enter the amount to withdraw from the fixed deposit."
    )

    interest_amount = forms.DecimalField(
        max_digits=12, decimal_places=2, required=True, label="Interest Amount",
        help_text="Enter the interest amount to withdraw."
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

        # Validate withdrawal amount
        if withdraw_amount is not None and deposit_amount is not None:
            if withdraw_amount > deposit_amount:
                raise forms.ValidationError("Withdrawal amount cannot exceed the deposited amount.")
            if withdraw_amount < 0:
                raise forms.ValidationError("Withdrawal amount cannot be negative.")

        # Validate interest amount
        if interest_amount is not None and interest_amount < 0:
            raise forms.ValidationError("Interest amount cannot be negative.")

        return cleaned_data