from django.db import models
from customers.models import Customer, FixedDepositAccount
from company.models import Branch
from django.utils.timezone import now
from decimal import Decimal
from datetime import timedelta
from accounts_admin.models import Account

class FixedDeposit(models.Model):
    
    cust_gl_no = models.CharField(max_length=20)  # ✅ Customer GL number
    cust_ac_no = models.CharField(max_length=20)  # ✅ Customer Account number
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="fixed_accounts")
    fixed_gl_no = models.CharField(max_length=20)  # ✅ Fixed GL No (Stored as CharField)
    fixed_ac_no = models.CharField(max_length=20)  # ✅ Fixed Deposit Account No
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    cycle = models.IntegerField(null=True, blank=True)
    
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2)  # Principal
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)  # Interest rate (e.g., 5.5 for 5.5%)
    tenure_months = models.IntegerField()  # Duration in months
    start_date = models.DateField()
    maturity_date = models.DateField()
    fixed_int_gl_no = models.CharField(max_length=20, blank=True, null=True)  # ✅ Fixed Interest GL No
    fixed_int_ac_no = models.CharField(max_length=20, blank=True, null=True)

    interest_option = models.CharField(
        max_length=20,
        choices=[
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("bi-monthly", "Every 2 Months"),
            ("quarterly", "Every 3 Months"),
            ("4-months", "Every 4 Months"),
            ("yearly", "Yearly"),
            ("end", "At Maturity")
        ],
        default="monthly"
    )

    status = models.CharField(max_length=10, choices=[("active", "Active"), ("closed", "Closed")], default="active")

    # ✅ New Fields
    interest_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Interest Earned
    maturity_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Principal + Interest

    def calculate_interest(self):
        """
        Calculate interest using **Simple Interest Formula**:
        Interest = (Principal * Rate * Time) / 100
        """
        if self.deposit_amount and self.interest_rate:
            years = Decimal(self.tenure_months) / Decimal(12)  # Convert months to years
            interest = (self.deposit_amount * self.interest_rate * years) / Decimal(100)  # Use Decimal
            return interest.quantize(Decimal("0.01"))  # Round to 2 decimal places
        return Decimal("0.00")

    def calculate_maturity_amount(self):
        """Calculate total maturity amount (Principal + Interest)"""
        return (self.deposit_amount + self.calculate_interest()).quantize(Decimal("0.01"))


    def save(self, *args, **kwargs):
        """Override save method to calculate maturity amount, maturity date, and set fixed_int_gl_no before saving"""

        # Ensure maturity_date is calculated
        if not self.maturity_date:
            self.maturity_date = self.start_date + timedelta(days=self.tenure_months * 30)  # Approximate months to days

        # Ensure financial calculations are updated before saving
        self.interest_amount = self.calculate_interest()
        self.maturity_amount = self.calculate_maturity_amount()

        # ✅ Auto-assign `fixed_int_gl_no` from `Account` model based on `fixed_gl_no`
        if not self.fixed_int_gl_no:
            account = Account.objects.filter(gl_no=self.fixed_gl_no).first()
            if account and hasattr(account, "fixed_dep_int_gl_no"):  # ✅ Corrected field name
                self.fixed_int_gl_no = account.fixed_dep_int_gl_no

        super().save(*args, **kwargs)

    def __str__(self):
        return f"FD-{self.fixed_ac_no} | {self.customer} | GL No: {self.fixed_gl_no} | Maturity: {self.maturity_amount}"



from django.db import models
from company.models import Branch  # Assuming Branch model exists

class FixedDepositHist(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="fixed_deposit_history")
    fixed_gl_no = models.CharField(max_length=20)
    fixed_ac_no = models.CharField(max_length=20)
    trx_date = models.DateField()
    trx_type = models.CharField(max_length=50)  # No predefined choices
    trx_naration = models.TextField()
    trx_no = models.CharField(max_length=50, unique=True)
    principal = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    interest = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    def __str__(self):
        return f"FD-{self.fixed_ac_no} | {self.trx_type} | {self.trx_date}"
