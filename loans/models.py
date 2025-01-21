from decimal import Decimal, getcontext
from operator import itemgetter
from django.db import models
from django.forms import JSONField

from accounts_admin.models import Account_Officer, Business_Sector
from customers.models import Customer
# import numpy_financial as npf
# import numpy as np
from datetime import timedelta
from company.models import Company, Branch




from decimal import Decimal


class Loans(models.Model):

    INTEREST_CALCULATION_METHOD_CHOICES = [
        ('1', 'Compound Interest'),
        ('2', 'Decline Balance - Daily Balance'),
        ('3', 'Decline Balance - Equal Installment'),
        ('4', 'Decline Balance - Equal Due'),
        ('5', 'Decline Balance - Straight Line'),
        ('6', 'Flat Rate'),
    ]

    FREQUENCY_CHOICES = [
        ('365', 'Daily'),
        ('52', 'Weekly'),
        ('26', 'Bi-Weekly'),
        ('13', 'Once Every 4 Weeks'),
        ('12', 'Monthly'),
        ('6', 'Bi-Monthly'),
        ('1.35', '9 Monthly'),
        ('1.22', '10 Monthly'),
        ('1.11', '11 Monthly'),
        ('17.38', '3 Weekly'),
        ('13.03', '4 Weekly'),
        ('10.43', '5 Weekly'),
        ('24.33', 'Half Monthly'),
        ('3.04', 'Quarterly'),
        ('1', 'Yearly'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="loans", 
    null=True, blank=True)
    cust_gl_no = models.CharField(max_length=20, null=True, blank=True)
    gl_no = models.CharField(max_length=20, null=True, blank=True)
    ac_no = models.CharField(max_length=20, null=True, blank=True)
    cycle = models.IntegerField(null=True, blank=True)
    appli_date = models.DateField(null=True, blank=True)
    approval_date = models.DateField(null=True, blank=True)
    disbursement_date = models.DateField(null=True, blank=True)
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    payment_freq = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, null=True, blank=True)
    num_install = models.PositiveIntegerField()
    interest_calculation_method = models.CharField(max_length=10, choices=INTEREST_CALCULATION_METHOD_CHOICES, null=True, blank=True)
    business_sector = models.ForeignKey(Business_Sector, on_delete=models.CASCADE, blank=True, null=True)
    approval_status = models.CharField(max_length=1, default='F', null=True, blank=True)
    loan_officer = models.ForeignKey(Account_Officer, on_delete=models.CASCADE, null=True, blank=True)
    reason = models.CharField(max_length=100, null=True, blank=True)
    total_loan = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_interest = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    numerical_value = models.CharField(max_length=20, null=True, blank=True)
    disb_status = models.CharField(max_length=1, default='F', null=True, blank=True)
    int_to_recev_gl_dr = models.CharField(max_length=6, blank=True, null=True)
    int_to_recev_ac_dr = models.CharField(max_length=6, blank=True, null=True)
    unearned_int_inc_gl = models.CharField(max_length=6, blank=True, null=True)
    unearned_int_inc_ac = models.CharField(max_length=6, blank=True, null=True)
    interest_gl_no = models.CharField(max_length=6, blank=True, null=True)
    interest_ac_no = models.CharField(max_length=6, blank=True, null=True)
    pen_gl_no = models.CharField(max_length=6, blank=True, null=True)
    pen_ac_no = models.CharField(max_length=6, blank=True, null=True)

    def save(self, *args, **kwargs):
        # Print the selected payment frequency for debugging
        print(f"payment_freq: {self.payment_freq}")

        if self.payment_freq == '365':
            self.numerical_value = '1'
        elif self.payment_freq == '52':
            self.numerical_value = '7'
        elif self.payment_freq == '26':
            self.numerical_value = '14'
        elif self.payment_freq == '13':
            self.numerical_value = '28'
        elif self.payment_freq == '12':
            self.numerical_value = '30'
        elif self.payment_freq == '6':
            self.numerical_value = '60'
        elif self.payment_freq == '1.35':
            self.numerical_value = '270'
        elif self.payment_freq == '1.22':
            self.numerical_value = '300'
        elif self.payment_freq == '1.11':
            self.numerical_value = '330'
        elif self.payment_freq == '17.38':
            self.numerical_value = '21'
        elif self.payment_freq == '13.03':
            self.numerical_value = '28'
        elif self.payment_freq == '10.43':
            self.numerical_value = '35'
        elif self.payment_freq == '24.33':
            self.numerical_value = '15'
        elif self.payment_freq == '3.04':
            self.numerical_value = '120'
        elif self.payment_freq == '1':
            self.numerical_value = '365'

        print(f"numerical_value: {self.numerical_value}")

        # Call the original save method
        super().save(*args, **kwargs)

    def calculate_loan_schedule(self):
        if self.interest_calculation_method == '1':
            return self.calculate_compound_interest_schedule()
        elif self.interest_calculation_method == '2':
            return self.calculate_decline_daily_balance_schedule()
        elif self.interest_calculation_method == '4':
            return self.calculate_decline_balance_equal_due_schedule()
        elif self.interest_calculation_method == '3':
            return self.calculate_decline_balance_equal_installment_schedule()
        elif self.interest_calculation_method == '5':
            return self.calculate_balance_straight_line_schedule()
        elif self.interest_calculation_method == '6':
            return self.calculate_flat_rate_schedule()

    def calculate_compound_interest_schedule(self):
        numerical_value = self.numerical_value
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        numerical_value_decimal = Decimal(numerical_value)
        payment_freq = Decimal(self.payment_freq)
        interest_rate_per_period = Decimal(self.interest_rate) / Decimal(100) / payment_freq
        num_periods = Decimal(self.num_install)
        loan_amount = Decimal(self.loan_amount)

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
            payment_date = self.appli_date + timedelta(days=int(numerical_value_decimal * period))
            schedule.append({
                'period': period,
                'payment_date': payment_date,
                'interest_payment': interest_payment,
                'principal_payment': principal_payment,
                'total_payment': total_payment,
                'principal_remaining': principal_remaining,
            })

        return schedule

    def calculate_decline_daily_balance_schedule(self):
        if (
            self.loan_amount is None
            or self.interest_rate is None
            or self.payment_freq is None
            or self.num_install is None
            or self.interest_calculation_method != '2'
        ):
            return []

        numerical_value = self.numerical_value
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        numerical_value_decimal = Decimal(numerical_value)
        payment_freq = Decimal(self.payment_freq)
        interest_rate_per_period = Decimal(self.interest_rate) / Decimal(100) / payment_freq
        num_periods = Decimal(self.num_install)
        loan_amount = Decimal(self.loan_amount)
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

            payment_date = self.appli_date + timedelta(days=int(numerical_value_decimal * period))
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
        if (
            self.loan_amount is None
            or self.interest_rate is None
            or self.payment_freq is None
            or self.num_install is None
            or self.interest_calculation_method != '4'
        ):
            return []

        numerical_value = self.numerical_value
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        numerical_value_decimal = Decimal(numerical_value)
        payment_freq = Decimal(self.payment_freq)
        interest_rate_per_period = Decimal(self.interest_rate) / Decimal(100) / payment_freq
        num_periods = Decimal(self.num_install)
        loan_amount = Decimal(self.loan_amount)
        schedule = []
        total_interest = loan_amount * interest_rate_per_period * num_periods
        principal_remaining = loan_amount
        total_payment = loan_amount / num_periods + total_interest / num_periods

        for period in range(1, int(num_periods) + 1):
            interest_payment = principal_remaining * interest_rate_per_period
            principal_payment = loan_amount / num_periods
            payment_date = self.appli_date + timedelta(days=int(numerical_value_decimal * period))
            schedule.append({
                'period': period,
                'payment_date': payment_date,
                'interest_payment': interest_payment,
                'principal_payment': principal_payment,
                'total_payment': total_payment,
                'principal_remaining': principal_remaining - principal_payment,
            })

        return schedule

    def calculate_decline_balance_equal_installment_schedule(self):
        if (
            self.loan_amount is None
            or self.interest_rate is None
            or self.payment_freq is None
            or self.num_install is None
            or self.interest_calculation_method != '3'
        ):
            return []

        numerical_value = self.numerical_value
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        numerical_value_decimal = Decimal(numerical_value)
        payment_freq = Decimal(self.payment_freq)
        interest_rate_per_period = Decimal(self.interest_rate) / Decimal(100) / payment_freq
        num_periods = Decimal(self.num_install)
        loan_amount = Decimal(self.loan_amount)
        fixed_payment = loan_amount * (interest_rate_per_period * (1 + interest_rate_per_period) ** num_periods) / ((1 + interest_rate_per_period) ** num_periods - 1)
        schedule = []
        principal_remaining = loan_amount

        for period in range(1, int(num_periods) + 1):
            interest_payment = principal_remaining * interest_rate_per_period
            principal_payment = fixed_payment - interest_payment
            total_payment = interest_payment + principal_payment
            principal_remaining -= principal_payment

            if period == int(num_periods):
                principal_payment += principal_remaining
                principal_remaining = 0

            payment_date = self.appli_date + timedelta(days=int(numerical_value_decimal * period))
            schedule.append({
                'period': period,
                'payment_date': payment_date,
                'interest_payment': interest_payment,
                'principal_payment': principal_payment,
                'total_payment': total_payment,
                'principal_remaining': principal_remaining,
            })

        return schedule

    def calculate_balance_straight_line_schedule(self):
        if (
            self.loan_amount is None
            or self.interest_rate is None
            or self.payment_freq is None
            or self.num_install is None
            or self.interest_calculation_method != '5'
        ):
            return []

        numerical_value = self.numerical_value
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        numerical_value_decimal = Decimal(numerical_value)
        payment_freq = Decimal(self.payment_freq)
        interest_rate_per_period = Decimal(self.interest_rate) / Decimal(100) / payment_freq
        num_periods = Decimal(self.num_install)
        loan_amount = Decimal(self.loan_amount)
        fixed_principal_payment = loan_amount / num_periods
        total_interest = loan_amount * interest_rate_per_period
        schedule = []
        principal_remaining = loan_amount

        for period in range(1, int(num_periods) + 1):
            interest_payment = principal_remaining * interest_rate_per_period
            principal_payment = fixed_principal_payment
            total_payment = interest_payment + principal_payment
            principal_remaining -= principal_payment

            if period == int(num_periods):
                principal_payment += principal_remaining
                principal_remaining = 0

            payment_date = self.appli_date + timedelta(days=int(numerical_value_decimal * period))
            schedule.append({
                'period': period,
                'payment_date': payment_date,
                'interest_payment': interest_payment,
                'principal_payment': principal_payment,
                'total_payment': total_payment,
                'principal_remaining': principal_remaining,
            })

        return schedule

    def calculate_flat_rate_schedule(self):
        if (
            self.loan_amount is None
            or self.interest_rate is None
            or self.payment_freq is None
            or self.num_install is None
            or self.interest_calculation_method != '6'
        ):
            return []

        numerical_value = self.numerical_value
        if numerical_value is None:
            raise ValueError("Numerical value is not set.")

        numerical_value_decimal = Decimal(numerical_value)
        payment_freq = Decimal(self.payment_freq)
        interest_rate_per_period = Decimal(self.interest_rate) / Decimal(100) / payment_freq
        num_periods = Decimal(self.num_install)
        loan_amount = Decimal(self.loan_amount)
        flat_rate_interest = loan_amount * interest_rate_per_period * num_periods
        total_payment = (loan_amount + flat_rate_interest) / num_periods
        schedule = []
        principal_remaining = loan_amount

        for period in range(1, int(num_periods) + 1):
            interest_payment = flat_rate_interest / num_periods
            principal_payment = total_payment - interest_payment
            total_payment = interest_payment + principal_payment
            principal_remaining -= principal_payment

            if period == int(num_periods):
                principal_payment += principal_remaining
                principal_remaining = 0

            payment_date = self.appli_date + timedelta(days=int(numerical_value_decimal * period))
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






class LoanHist(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="loanHist", 
    null=True, blank=True)
    # customer = models.CharField(max_length=30, null=True, blank=True) 
    gl_no = models.CharField(max_length=20)
    ac_no = models.CharField(max_length=20)
    cycle = models.IntegerField(null=True, blank=True)
    period = models.IntegerField(blank=True, null=True)
    trx_date = models.DateField()
    trx_type = models.CharField(max_length=50)
    trx_naration = models.CharField(max_length=50, null=True, blank=True)
    trx_no = models.CharField(max_length=50)
    principal = models.DecimalField(max_digits=10, decimal_places=2)
    interest = models.DecimalField(max_digits=10, decimal_places=2)
    penalty = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
            return f"LoanHist - {self.ac_no}"