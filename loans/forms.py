from datetime import timedelta
from decimal import Decimal
import decimal
from django import forms
from accounts_admin.models import Business_Sector

from transactions.models import Memtrans
from .models import Loans, Loans

class LoansForm(forms.ModelForm):
    class Meta:
        model = Loans
        fields = '__all__'  # Use all fields from the model
        # business_sector = forms.ChoiceField(choices=Business_Sector.objects.values_list('id', 'sector_name'))
        


class LoansModifyForm(forms.ModelForm):
    
    class Meta:
        model = Loans
       
        exclude = ['customer','cycle']  # Exclude the 'customer' field
        

class LoansApproval(forms.ModelForm):
    
    class Meta:
        model = Loans
       
        exclude = ['customer','cycle','appli_date','branch']  # Exclude the 'customer' field
    
    def __init__(self, *args, **kwargs):
        # Extract the company session date from kwargs and pop it
        self.company_session_date = kwargs.pop('company_session_date', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        approval_date = cleaned_data.get('approval_date')
        
        # Check if the company session date is provided and validate approval_date
        if self.company_session_date and approval_date > self.company_session_date:
            self.add_error('approval_date', "Approval date cannot be greater than the company's session date.")
        
        return cleaned_data

class LoansRejectForm(forms.ModelForm):
    class Meta:
        model = Loans
        exclude = ['customer']  # Exclude the 'customer' field


class MemtransForm(forms.ModelForm):
    gl_no_cashier = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    ac_no_cashier = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    gl_no = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    ac_no = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    class Meta:
        model = Memtrans
        fields = ['branch','gl_no', 'ac_no','ses_date','app_date', 'amount','gl_no_cashier','ac_no_cashier','description']




       


    # Add any additional form customization here, if needed

    def clean_loan_amount(self):
        loan_amount = self.cleaned_data.get('loan_amount')  # Use get() to handle None
        if loan_amount is not None and loan_amount <= 0:
            raise forms.ValidationError("Loan amount must be greater than zero.")
        return loan_amount
    


from django import forms

class LoanApplicationForm(forms.Form):
    PAYMENT_FREQUENCY_CHOICES = [
        ('365', 'Daily'),
        ('52', 'Weekly'),
        ('104', 'Bi-Weekly'),
        ('12', 'Once Every 4 Weeks'),
        ('12', 'Monthly'),
        ('60', 'Bi-Monthly'),
        ('270', '9 Monthly'),
        ('300', '10 Monthly'),
        ('330', '11 Monthly'),
        ('21', '3 Weekly'),
        ('28', '4 Weekly'),
        ('35', '5 Weekly'),
        ('15', 'Half Monthly'),
        ('120', 'Quarterly'),
        ('365', 'Yearly'),
    ]

    appli_date = forms.DateField(label='Registration Date', widget=forms.DateInput(attrs={'type': 'date'}))
    loan_amount = forms.DecimalField(label='Loan Amount')
    interest_rate = forms.DecimalField(label='Annual Interest Rate')
    payment_freq = forms.ChoiceField(choices=PAYMENT_FREQUENCY_CHOICES)
    
    
    numerical_value = forms.IntegerField(widget=forms.HiddenInput, required=False, initial='1')

    def set_numerical_value(self):
        numerical_value = self.cleaned_data['numerical_value']
        # Print the selected payment frequency for debugging
        print(f"payment_freq: {self.cleaned_data['payment_freq']}")

        # Calculate numerical_value based on payment_freq
        if self.cleaned_data['payment_freq'] == '365':
            self.cleaned_data['numerical_value'] = '1'
        elif self.cleaned_data['payment_freq'] == '52':
            self.cleaned_data['numerical_value'] = '7'
        elif self.cleaned_data['payment_freq'] == '26':
            self.cleaned_data['numerical_value'] = '14'
        elif self.cleaned_data['payment_freq'] == '13':
            self.cleaned_data['numerical_value'] = '28'
        elif self.cleaned_data['payment_freq'] == '12':
            self.cleaned_data['numerical_value'] = '30'
        elif self.cleaned_data['payment_freq'] == '6':
            self.cleaned_data['numerical_value'] = '60'
        elif self.cleaned_data['payment_freq'] == '1.35':
            self.cleaned_data['numerical_value'] = '270'
        elif self.cleaned_data['payment_freq'] == '1.22':
            self.cleaned_data['numerical_value'] = '300'
        elif self.cleaned_data['payment_freq'] == '1.11':
            self.cleaned_data['numerical_value'] = '330'
        elif self.cleaned_data['payment_freq'] == '17.38':
            self.cleaned_data['numerical_value'] = '21'
        elif self.cleaned_data['payment_freq'] == '13.03':
            self.cleaned_data['numerical_value'] = '28'
        elif self.cleaned_data['payment_freq'] == '10.43':
            self.cleaned_data['numerical_value'] = '35'
        elif self.cleaned_data['payment_freq'] == '24.33':
            self.cleaned_data['numerical_value'] = '15'
        elif self.cleaned_data['payment_freq'] == '3.04':
            self.cleaned_data['numerical_value'] = '120'
        elif self.cleaned_data['payment_freq'] == '1':
            self.cleaned_data['numerical_value'] = '365'
        else:
            self.cleaned_data['numerical_value'] = None

        if self.cleaned_data['numerical_value'] is None:
            raise ValueError("Numerical value is not set. Please set the payment frequency.")

        print(f"payment_freq: {self.cleaned_data['payment_freq']}")
        print(f"numerical_value: {self.cleaned_data['numerical_value']}")
         


        # Print the selected numerical value for debugging
        print(f"numerical_value: {self.cleaned_data['numerical_value']}")

        # Do something with numerical_value if needed
    def save(self, *args, **kwargs):
        # Set numerical_value before validating the form
        self.set_numerical_value()

        # Validate the form
        if not self.is_valid():
            raise ValueError("Form is not valid.")
        # Call the original save method
        super().save(*args, **kwargs)
    

    
    interest_calculation_method = forms.ChoiceField(
        label='Interest Method',
        choices=[
            ('1', 'Compound Interest'),
            ('2', 'Daily Balance'),
            ('3', 'Equal Installment'),
            ('4', 'Decline Balance'),
            ('5', 'Balance Straight Line'),
            ('6', 'Flat Rate'),
        ]
    )
    num_install = forms.IntegerField(label='No. of Installments')

    def __init__(self, *args, **kwargs):
        super(LoanApplicationForm, self).__init__(*args, **kwargs)
        if 'interest_calculation_method' in self.data:
            interest_calculation_method = self.data['interest_calculation_method']
            self.set_required_fields(interest_calculation_method)

    def set_required_fields(self, interest_calculation_method):
        required_fields = {
            '1': ['loan_amount', 'num_install'],
            '2': ['loan_amount', 'num_install'],
            '3': ['loan_amount', 'num_install'],
            '4': ['loan_amount', 'num_install'],
            '5': ['loan_amount', 'num_install'],
            '6': ['loan_amount', 'num_install'],
        }
        for field in required_fields.get(interest_calculation_method, []):
            self.fields[field].required = True

    def clean_loan_amount(self):
        loan_amount = self.cleaned_data['loan_amount']
        if loan_amount <= 0:
            raise forms.ValidationError('Loan amount must be greater than zero.')
        return loan_amount

    def clean_interest_rate(self):
        interest_rate = self.cleaned_data['interest_rate']
        if interest_rate <= 0:
            raise forms.ValidationError('Interest rate must be greater than zero.')
        return interest_rate

    




    def calculate_loan_schedule(self):
        if self.is_valid():
            interest_calculation_method = self.cleaned_data['interest_calculation_method']

            if interest_calculation_method == '1':
                return self.calculate_compound_interest_schedule()
            elif interest_calculation_method == '2':
                return self.calculate_decline_daily_balance_schedule()
            elif interest_calculation_method == '3':
                return self.calculate_decline_balance_equal_due_schedule()
            elif interest_calculation_method == '4':
                return self.calculate_decline_balance_equal_installment_schedule()
            elif interest_calculation_method == '5':
                return self.calculate_balance_straight_line_schedule()
            elif interest_calculation_method == '6':
                return self.calculate_flat_rate_schedule()

    def calculate_compound_interest_schedule(self):
        numerical_value = self.cleaned_data['numerical_value']

    # Handle the case where numerical_value is None
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        # If numerical_value is not None, proceed with the conversion
        numerical_value_decimal = Decimal(numerical_value)

        payment_freq = Decimal(self.cleaned_data['payment_freq'])
        interest_rate_per_period = Decimal(self.cleaned_data['interest_rate']) / Decimal(100) / payment_freq
        num_periods = Decimal(self.cleaned_data['num_install'])
        loan_amount = Decimal(self.cleaned_data['loan_amount'])

        # Calculate fixed principal and interest payments to amortize the loan
        discount_factor = (1 - (1 + interest_rate_per_period) ** -num_periods) / interest_rate_per_period
        fixed_payment = loan_amount / discount_factor
        fixed_interest_payment = loan_amount * interest_rate_per_period
        fixed_principal_payment = fixed_payment - fixed_interest_payment

        schedule = []
        principal_remaining = loan_amount

        for period in range(1, int(num_periods) + 1):
            interest_payment = fixed_interest_payment
            principal_payment = fixed_principal_payment

            principal_remaining -= principal_payment

            if period == int(num_periods):
                principal_payment += principal_remaining
                principal_remaining = 0

            total_payment = interest_payment + principal_payment

            # Assuming monthly payments
            if numerical_value_decimal is not None:
                payment_date = self.cleaned_data['appli_date'] + timedelta(days=int(numerical_value_decimal * (period )))
            else:
                # Handle the case where numerical_value is None
                payment_date = None  # Replace this with your desired behavior

            schedule.append({
                'period': period,
                'payment_date': payment_date,
                'interest_payment': interest_payment,
                'principal_payment': principal_payment,
                'total_payment': total_payment,
                'principal_remaining': principal_remaining,
            })

        return schedule

    # def calculate_compound_interest_schedule(self):
    #     payment_freq = Decimal(self.payment_freq)
    #     interest_rate_per_period = Decimal(self.interest_rate) / Decimal(100) / payment_freq  # Monthly interest rate
    #     num_periods = Decimal(self.num_install)
    #     loan_amount = Decimal(self.loan_amount)

    #     # Calculate fixed principal payment to amortize the loan
    #     fixed_principal_payment = loan_amount / num_periods

    #     schedule = []
    #     principal_remaining = loan_amount

    #     for period in range(1, int(num_periods) + 1):  # Convert num_periods to int for the range
    #         interest_payment = principal_remaining * interest_rate_per_period
    #         principal_payment = fixed_principal_payment

    #         principal_remaining -= principal_payment

    #         # Ensure principal remaining is zero on the last period
    #         if period == int(num_periods):
    #             principal_payment += principal_remaining
    #             principal_remaining = 0

    #         # Assuming monthly payments
    #         payment_date = self.appli_date + timedelta(days=int(30 * period))  # Convert to int for timedelta

    #         schedule.append({
    #             'period': period,
    #             'payment_date': payment_date,
    #             'interest_payment': interest_payment,
    #             'principal_payment': principal_payment,
    #             'total_payment': interest_payment + principal_payment,
    #             'principal_remaining': principal_remaining,
    #         })

    #     return schedule


    def calculate_decline_daily_balance_schedule(self):
        if not self.is_valid():
            return []
        numerical_value = self.cleaned_data['numerical_value']

    # Handle the case where numerical_value is None
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        # If numerical_value is not None, proceed with the conversion
        numerical_value_decimal = Decimal(numerical_value)

        payment_freq = Decimal(self.cleaned_data['payment_freq'])
        interest_rate_per_period = self.cleaned_data['interest_rate'] / Decimal('100') / payment_freq
        num_periods = self.cleaned_data['num_install']
        loan_amount = self.cleaned_data['loan_amount']

        principal_remaining = loan_amount
        fixed_principal_payment = loan_amount / num_periods
        schedule = []
        total_interest = loan_amount * interest_rate_per_period * num_periods
        interest_remaining = total_interest

        for period in range(1, int(num_periods) + 1):
            daily_interest_payment = principal_remaining * interest_rate_per_period
            principal_payment = fixed_principal_payment
            total_payment = daily_interest_payment + principal_payment
            interest_remaining -= daily_interest_payment
            principal_remaining -= principal_payment

            if period == int(num_periods):
                interest_remaining = 0

            payment_date = self.cleaned_data['appli_date'] + timedelta(days=int(numerical_value_decimal * (period )))

            schedule.append({
                'period': period,
                'payment_date': payment_date,
                'interest_payment': daily_interest_payment,
                'principal_payment': principal_payment,
                'total_payment': total_payment,
                'principal_remaining': principal_remaining,
            })

        return schedule



    



    def calculate_decline_balance_equal_due_schedule(self):
        if not self.is_valid():
            return []
        numerical_value = self.cleaned_data['numerical_value']

    # Handle the case where numerical_value is None
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        # If numerical_value is not None, proceed with the conversion
        numerical_value_decimal = Decimal(numerical_value)

        payment_freq = Decimal(self.cleaned_data['payment_freq'])
        interest_rate_per_period = self.cleaned_data['interest_rate'] / Decimal('100') / payment_freq

        num_periods = self.cleaned_data['num_install']
        loan_amount = Decimal(self.cleaned_data['loan_amount'])

        principal_remaining = loan_amount
        schedule = []

        for period in range(1, int(num_periods) + 1):
            daily_interest_payment = loan_amount * interest_rate_per_period
            principal_payment = loan_amount / num_periods  # Equal principal payments
            total_payment = daily_interest_payment + principal_payment
            principal_remaining -= principal_payment

            # Assuming daily payments
            payment_date = self.cleaned_data['appli_date'] + timedelta(days=int(numerical_value_decimal * (period )))

            schedule.append({
                'period': period,
                'payment_date': payment_date,
                'interest_payment': daily_interest_payment,
                'principal_payment': principal_payment,
                'total_payment': total_payment,
                'principal_remaining': principal_remaining,
            })

        return schedule
    

    def calculate_decline_balance_equal_installment_schedule(self):
        if not self.is_valid():
            return []
        numerical_value = self.cleaned_data['numerical_value']

    # Handle the case where numerical_value is None
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        # If numerical_value is not None, proceed with the conversion
        numerical_value_decimal = Decimal(numerical_value)
        payment_freq = Decimal(self.cleaned_data['payment_freq'])
        interest_rate_per_period = self.cleaned_data['interest_rate'] / Decimal('100') / Decimal('12')  # Monthly interest rate
        num_periods = self.cleaned_data['num_install']
        loan_amount = self.cleaned_data['loan_amount']

        # Calculate monthly interest rate
        monthly_interest_rate = interest_rate_per_period

        # Calculate equal periodic payments
        monthly_installment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate) ** num_periods) / ((1 + monthly_interest_rate) ** num_periods - 1)

        schedule = []
        principal_remaining = loan_amount

        for period in range(1, num_periods + 1):
            interest_payment = principal_remaining * monthly_interest_rate
            principal_payment = monthly_installment - interest_payment
            principal_remaining -= principal_payment

            # Assuming monthly payments
            payment_date = self.cleaned_data['appli_date'] + timedelta(days=int(numerical_value_decimal * (period )))

            schedule.append({
                'period': period,
                'payment_date': payment_date,
                'interest_payment': interest_payment,
                'principal_payment': principal_payment,
                'total_payment': monthly_installment,
                'principal_remaining': principal_remaining,
            })

        return schedule


    def calculate_balance_straight_line_schedule(self):

        if not self.is_valid():
            return []
        numerical_value = self.cleaned_data['numerical_value']

    # Handle the case where numerical_value is None
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        # If numerical_value is not None, proceed with the conversion
        numerical_value_decimal = Decimal(numerical_value)
        payment_freq = Decimal(self.cleaned_data['payment_freq'])
        num_periods = self.cleaned_data['num_install']
        loan_amount = Decimal(self.cleaned_data['loan_amount'])

        # Assuming monthly payments
        interest_payment = loan_amount * self.cleaned_data['interest_rate'] / 100 / Decimal(self.cleaned_data['payment_freq'])
        principal_payment = loan_amount / num_periods
        total_payment = interest_payment + principal_payment

        schedule = []

        for period in range(1, int(num_periods) + 1):  # Convert num_periods to int for the range
            # Assuming monthly payments
            payment_date = self.cleaned_data['appli_date'] + timedelta(days=int(numerical_value_decimal * (period)))  # Convert to int for timedelta

            schedule.append({
                'period': period,
                'payment_date': payment_date,
                'interest_payment': interest_payment,
                'principal_payment': principal_payment,
                'total_payment': total_payment,
                'principal_remaining': loan_amount - (principal_payment * period),
            })

        return schedule
   




    def calculate_flat_rate_schedule(self):
        # Ensure required fields are not None
        if (
            'loan_amount' not in self.cleaned_data
            or 'interest_rate' not in self.cleaned_data
            or 'payment_freq' not in self.cleaned_data
            or 'num_install' not in self.cleaned_data
            or 'interest_calculation_method' not in self.cleaned_data
            or self.cleaned_data['interest_calculation_method'] != '6'  # Assuming it's Flat Rate
        ):
            return []
        numerical_value = self.cleaned_data['numerical_value']

    # Handle the case where numerical_value is None
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        # If numerical_value is not None, proceed with the conversion
        numerical_value_decimal = Decimal(numerical_value)
        payment_freq = Decimal(self.cleaned_data['payment_freq'])
        interest_rate_per_period = self.cleaned_data['interest_rate'] / Decimal('100') / Decimal(self.cleaned_data['payment_freq'])
        num_periods = self.cleaned_data['num_install']
        loan_amount = self.cleaned_data['loan_amount']

        # Calculate flat monthly interest rate
        flat_monthly_interest_rate = interest_rate_per_period

        # Calculate flat periodic payments
        total_payment = (loan_amount + (loan_amount * flat_monthly_interest_rate * num_periods)) / num_periods

        schedule = []
        principal_remaining = loan_amount

        for period in range(1, num_periods + 1):
            interest_payment = loan_amount * flat_monthly_interest_rate
            principal_payment = total_payment - interest_payment
            principal_remaining -= principal_payment

            # Assuming monthly payments
            payment_date = self.cleaned_data['appli_date'] + timedelta(days=int(numerical_value_decimal * (period)))  # Convert to int for timedelta

            schedule.append({
                'period': period,
                'payment_date': payment_date,
                'interest_payment': interest_payment,
                'principal_payment': principal_payment,
                'total_payment': total_payment,
                'principal_remaining': principal_remaining,
            })

        return schedule

    # ... add other methods for different interest calculation methods ...


    def __str__(self):
            return f"Loans - {self.ac_no}"



class LoansChooseRepaymeny(forms.ModelForm):
    
    class Meta:
        model = Loans
       
        exclude = ['customer','cycle','branch']  # Exclude the 'customer' field



from django import forms
from .models import LoanHist

class LoanHistForm(forms.ModelForm):
    class Meta:
        model = LoanHist
        fields = ['branch', 'gl_no', 'ac_no', 'cycle', 'trx_date', 'trx_type', 'trx_no', 'principal', 'interest', 'penalty']
