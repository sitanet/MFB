import uuid
from django.db import models
from customers.models import Customer, FixedDepositAccount
from company.models import Branch
from django.utils.timezone import now
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta, date
from accounts_admin.models import Account
from profit_solutions.tenant_managers import TenantManager


class FDProduct(models.Model):
    """
    Fixed Deposit Product Configuration - Defines different FD schemes/products
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="fd_products", null=True, blank=True)
    product_name = models.CharField(max_length=100)
    product_code = models.CharField(max_length=20, unique=True)
    
    # Interest Rate Slabs
    min_deposit = models.DecimalField(max_digits=15, decimal_places=2, default=1000.00)
    max_deposit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    min_tenure_months = models.IntegerField(default=1)
    max_tenure_months = models.IntegerField(default=60)
    
    # Interest Rates
    base_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Base interest rate %")
    senior_citizen_extra_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.50, 
                                                     help_text="Extra rate for senior citizens %")
    
    # Interest Calculation
    INTEREST_TYPE_CHOICES = [
        ("simple", "Simple Interest"),
        ("compound", "Compound Interest"),
    ]
    COMPOUND_FREQUENCY_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("half_yearly", "Half Yearly"),
        ("yearly", "Yearly"),
    ]
    interest_type = models.CharField(max_length=20, choices=INTEREST_TYPE_CHOICES, default="simple")
    compound_frequency = models.CharField(max_length=20, choices=COMPOUND_FREQUENCY_CHOICES, 
                                          default="quarterly", blank=True, null=True)
    
    # Premature Withdrawal Settings
    allow_premature_withdrawal = models.BooleanField(default=True)
    premature_penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=1.00,
                                                  help_text="Penalty rate % on interest for early withdrawal")
    min_lock_in_days = models.IntegerField(default=7, help_text="Minimum days before premature withdrawal allowed")
    
    # Auto Renewal
    allow_auto_renewal = models.BooleanField(default=True)
    
    # TDS Settings
    tds_applicable = models.BooleanField(default=True)
    tds_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, 
                                   help_text="TDS rate % on interest")
    tds_threshold = models.DecimalField(max_digits=15, decimal_places=2, default=40000.00,
                                        help_text="TDS applicable if interest exceeds this amount per year")
    
    # Loan Against FD
    allow_loan_against_fd = models.BooleanField(default=True)
    max_loan_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=90.00,
                                               help_text="Max % of FD that can be given as loan")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TenantManager()
    all_objects = models.Manager()
    
    class Meta:
        verbose_name = "FD Product"
        verbose_name_plural = "FD Products"
    
    def __str__(self):
        return f"{self.product_name} ({self.product_code})"


class FDInterestSlab(models.Model):
    """
    Interest Rate Slabs based on deposit amount and tenure
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    product = models.ForeignKey(FDProduct, on_delete=models.CASCADE, related_name="interest_slabs")
    
    # Amount Range
    min_amount = models.DecimalField(max_digits=15, decimal_places=2)
    max_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Tenure Range (in months)
    min_tenure = models.IntegerField()
    max_tenure = models.IntegerField()
    
    # Interest Rate for this slab
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    
    objects = TenantManager()
    all_objects = models.Manager()
    
    class Meta:
        verbose_name = "FD Interest Slab"
        verbose_name_plural = "FD Interest Slabs"
        ordering = ['min_amount', 'min_tenure']
    
    def __str__(self):
        return f"{self.product.product_code}: {self.min_amount}-{self.max_amount} | {self.min_tenure}-{self.max_tenure} months @ {self.interest_rate}%"


class FixedDeposit(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    cust_gl_no = models.CharField(max_length=20)
    cust_ac_no = models.CharField(max_length=20)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="fixed_accounts")
    fixed_gl_no = models.CharField(max_length=20)
    fixed_ac_no = models.CharField(max_length=20)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    cycle = models.IntegerField(null=True, blank=True)
    
    # Link to FD Product (optional for backward compatibility)
    fd_product = models.ForeignKey(FDProduct, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name="fixed_deposits")
    
    # Core FD Fields
    deposit_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenure_months = models.IntegerField()
    start_date = models.DateField()
    maturity_date = models.DateField()
    fixed_int_gl_no = models.CharField(max_length=20, blank=True, null=True)
    fixed_int_ac_no = models.CharField(max_length=20, blank=True, null=True)

    # Interest Calculation Type
    INTEREST_TYPE_CHOICES = [
        ("simple", "Simple Interest"),
        ("compound", "Compound Interest"),
    ]
    interest_type = models.CharField(max_length=20, choices=INTEREST_TYPE_CHOICES, default="simple")
    
    COMPOUND_FREQUENCY_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("half_yearly", "Half Yearly"),
        ("yearly", "Yearly"),
    ]
    compound_frequency = models.CharField(max_length=20, choices=COMPOUND_FREQUENCY_CHOICES, 
                                          default="quarterly", blank=True, null=True)

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
        default="end"
    )

    STATUS_CHOICES = [
        ("active", "Active"),
        ("matured", "Matured"),
        ("closed", "Closed"),
        ("premature_closed", "Premature Closed"),
        ("renewed", "Renewed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    # Financial Fields
    interest_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    maturity_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    accrued_interest = models.DecimalField(max_digits=15, decimal_places=2, default=0.00,
                                           help_text="Interest accrued till date")
    interest_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0.00,
                                        help_text="Total interest already paid out")
    
    # Premature Withdrawal Fields
    premature_penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=1.00,
                                                  help_text="Penalty rate % for early withdrawal")
    penalty_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    # Auto Renewal
    auto_renewal = models.BooleanField(default=False)
    renewal_count = models.IntegerField(default=0)
    original_fd = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="renewed_fds", help_text="Reference to original FD if renewed")
    
    # TDS (Tax Deduction at Source)
    tds_applicable = models.BooleanField(default=False)
    tds_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    tds_deducted = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    # Nominee/Beneficiary Details
    nominee_name = models.CharField(max_length=200, blank=True, null=True)
    nominee_relationship = models.CharField(max_length=50, blank=True, null=True)
    nominee_address = models.TextField(blank=True, null=True)
    nominee_phone = models.CharField(max_length=20, blank=True, null=True)
    nominee_id_type = models.CharField(max_length=50, blank=True, null=True)
    nominee_id_number = models.CharField(max_length=50, blank=True, null=True)
    nominee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    
    # Lien Marking (for loans against FD)
    is_lien_marked = models.BooleanField(default=False)
    lien_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    lien_reference = models.CharField(max_length=100, blank=True, null=True, 
                                      help_text="Loan reference number if lien is marked")
    lien_date = models.DateField(null=True, blank=True)
    
    # Certificate
    certificate_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    certificate_issued = models.BooleanField(default=False)
    certificate_issue_date = models.DateField(null=True, blank=True)
    
    # Senior Citizen
    is_senior_citizen = models.BooleanField(default=False)
    senior_citizen_extra_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.CharField(max_length=100, blank=True, null=True)
    last_interest_calc_date = models.DateField(null=True, blank=True)
    
    # Remarks
    remarks = models.TextField(blank=True, null=True)

    def calculate_simple_interest(self):
        """Calculate interest using Simple Interest Formula: I = (P * R * T) / 100"""
        if self.deposit_amount and self.interest_rate:
            effective_rate = self.interest_rate + self.senior_citizen_extra_rate
            years = Decimal(self.tenure_months) / Decimal(12)
            interest = (self.deposit_amount * effective_rate * years) / Decimal(100)
            return interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return Decimal("0.00")

    def calculate_compound_interest(self):
        """
        Calculate interest using Compound Interest Formula: 
        A = P(1 + r/n)^(nt) where n = compounding frequency per year
        """
        if not self.deposit_amount or not self.interest_rate:
            return Decimal("0.00")
        
        effective_rate = self.interest_rate + self.senior_citizen_extra_rate
        
        # Determine compounding frequency (n)
        frequency_map = {
            "monthly": 12,
            "quarterly": 4,
            "half_yearly": 2,
            "yearly": 1,
        }
        n = frequency_map.get(self.compound_frequency, 4)
        
        P = self.deposit_amount
        r = effective_rate / Decimal(100)
        t = Decimal(self.tenure_months) / Decimal(12)
        
        # A = P(1 + r/n)^(nt)
        amount = P * ((1 + r / n) ** (n * t))
        interest = amount - P
        
        return interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_interest(self):
        """Calculate interest based on interest type (simple or compound)"""
        if self.interest_type == "compound":
            return self.calculate_compound_interest()
        return self.calculate_simple_interest()

    def calculate_maturity_amount(self):
        """Calculate total maturity amount (Principal + Interest - TDS)"""
        gross_interest = self.calculate_interest()
        tds = Decimal("0.00")
        
        if self.tds_applicable and gross_interest > Decimal("0.00"):
            tds = (gross_interest * self.tds_rate / Decimal(100)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        net_interest = gross_interest - tds
        return (self.deposit_amount + net_interest).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_premature_interest(self, withdrawal_date=None):
        """
        Calculate interest for premature withdrawal with penalty
        """
        if not withdrawal_date:
            withdrawal_date = date.today()
        
        # Calculate actual tenure
        days_held = (withdrawal_date - self.start_date).days
        if days_held <= 0:
            return Decimal("0.00"), Decimal("0.00")
        
        # Calculate interest for actual period held
        actual_months = Decimal(days_held) / Decimal(30)
        effective_rate = self.interest_rate + self.senior_citizen_extra_rate
        
        if self.interest_type == "compound":
            frequency_map = {"monthly": 12, "quarterly": 4, "half_yearly": 2, "yearly": 1}
            n = frequency_map.get(self.compound_frequency, 4)
            r = effective_rate / Decimal(100)
            t = actual_months / Decimal(12)
            amount = self.deposit_amount * ((1 + r / n) ** (n * t))
            gross_interest = amount - self.deposit_amount
        else:
            years = actual_months / Decimal(12)
            gross_interest = (self.deposit_amount * effective_rate * years) / Decimal(100)
        
        # Apply penalty
        penalty = (gross_interest * self.premature_penalty_rate / Decimal(100)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        net_interest = (gross_interest - penalty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        return net_interest, penalty

    def calculate_accrued_interest(self, as_of_date=None):
        """Calculate interest accrued till a specific date"""
        if not as_of_date:
            as_of_date = date.today()
        
        if as_of_date < self.start_date:
            return Decimal("0.00")
        
        if as_of_date >= self.maturity_date:
            return self.calculate_interest()
        
        days_elapsed = (as_of_date - self.start_date).days
        total_days = (self.maturity_date - self.start_date).days
        
        if total_days <= 0:
            return Decimal("0.00")
        
        total_interest = self.calculate_interest()
        accrued = (total_interest * Decimal(days_elapsed) / Decimal(total_days))
        
        return accrued.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def get_available_for_withdrawal(self):
        """Get amount available for withdrawal (excluding lien)"""
        if self.is_lien_marked:
            return max(Decimal("0.00"), self.deposit_amount - self.lien_amount)
        return self.deposit_amount

    def can_withdraw_premature(self):
        """Check if premature withdrawal is allowed"""
        days_since_start = (date.today() - self.start_date).days
        min_lock_in = 7  # Default minimum lock-in days
        
        if self.fd_product:
            if not self.fd_product.allow_premature_withdrawal:
                return False, "Premature withdrawal not allowed for this product"
            min_lock_in = self.fd_product.min_lock_in_days
        
        if days_since_start < min_lock_in:
            return False, f"Lock-in period of {min_lock_in} days not completed"
        
        if self.is_lien_marked and self.lien_amount >= self.deposit_amount:
            return False, "Full amount is under lien"
        
        return True, "Premature withdrawal allowed"

    def generate_certificate_number(self):
        """Generate unique FD certificate number"""
        if not self.certificate_number:
            prefix = "FDC"
            branch_code = self.branch.branch_code if hasattr(self.branch, 'branch_code') else "000"
            timestamp = now().strftime("%Y%m%d%H%M%S")
            self.certificate_number = f"{prefix}{branch_code}{timestamp}{self.id or ''}"
        return self.certificate_number

    def save(self, *args, **kwargs):
        """Override save method to calculate all financial fields"""
        
        # Calculate maturity date if not set
        if not self.maturity_date and self.start_date:
            self.maturity_date = self.start_date + timedelta(days=self.tenure_months * 30)
        
        # Calculate interest and maturity amounts
        self.interest_amount = self.calculate_interest()
        self.maturity_amount = self.calculate_maturity_amount()
        
        # Calculate TDS if applicable
        if self.tds_applicable and self.interest_amount > Decimal("0.00"):
            self.tds_deducted = (self.interest_amount * self.tds_rate / Decimal(100)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Auto-assign fixed_int_gl_no from Account model
        if not self.fixed_int_gl_no:
            account = Account.objects.filter(gl_no=self.fixed_gl_no).first()
            if account and hasattr(account, "fixed_dep_int_gl_no"):
                self.fixed_int_gl_no = account.fixed_dep_int_gl_no

        super().save(*args, **kwargs)

    objects = TenantManager()
    all_objects = models.Manager()
    
    class Meta:
        verbose_name = "Fixed Deposit"
        verbose_name_plural = "Fixed Deposits"
        ordering = ['-created_at']

    def __str__(self):
        return f"FD-{self.fixed_ac_no} | {self.customer} | {self.deposit_amount} | Maturity: {self.maturity_date}"


class FDInterestAccrual(models.Model):
    """
    Track daily/periodic interest accrual for Fixed Deposits
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    fixed_deposit = models.ForeignKey(FixedDeposit, on_delete=models.CASCADE, related_name="interest_accruals")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    
    accrual_date = models.DateField()
    opening_principal = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    days_in_period = models.IntegerField(default=1)
    accrued_amount = models.DecimalField(max_digits=15, decimal_places=2)
    cumulative_accrued = models.DecimalField(max_digits=15, decimal_places=2)
    
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    payment_trx_no = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = TenantManager()
    all_objects = models.Manager()
    
    class Meta:
        verbose_name = "FD Interest Accrual"
        verbose_name_plural = "FD Interest Accruals"
        ordering = ['-accrual_date']
        unique_together = ['fixed_deposit', 'accrual_date']
    
    def __str__(self):
        return f"{self.fixed_deposit.fixed_ac_no} | {self.accrual_date} | {self.accrued_amount}"


class FDRenewalHistory(models.Model):
    """
    Track FD renewal history
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    original_fd = models.ForeignKey(FixedDeposit, on_delete=models.CASCADE, related_name="renewal_history")
    renewed_fd = models.ForeignKey(FixedDeposit, on_delete=models.CASCADE, related_name="renewed_from",
                                   null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    
    renewal_date = models.DateField()
    original_principal = models.DecimalField(max_digits=15, decimal_places=2)
    interest_earned = models.DecimalField(max_digits=15, decimal_places=2)
    
    RENEWAL_TYPE_CHOICES = [
        ("principal_only", "Principal Only"),
        ("principal_interest", "Principal + Interest"),
        ("custom", "Custom Amount"),
    ]
    renewal_type = models.CharField(max_length=20, choices=RENEWAL_TYPE_CHOICES, default="principal_interest")
    renewed_principal = models.DecimalField(max_digits=15, decimal_places=2)
    
    new_tenure_months = models.IntegerField()
    new_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    
    is_auto_renewal = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, blank=True, null=True)
    
    objects = TenantManager()
    all_objects = models.Manager()
    
    class Meta:
        verbose_name = "FD Renewal History"
        verbose_name_plural = "FD Renewal Histories"
        ordering = ['-renewal_date']
    
    def __str__(self):
        return f"{self.original_fd.fixed_ac_no} renewed on {self.renewal_date}"



from django.db import models
from company.models import Branch  # Assuming Branch model exists

class FixedDepositHist(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="fixed_deposit_history")
    fixed_gl_no = models.CharField(max_length=20)
    fixed_ac_no = models.CharField(max_length=20)
    trx_date = models.DateField()
    trx_type = models.CharField(max_length=50)  # No predefined choices
    trx_naration = models.TextField()
    trx_no = models.CharField(max_length=50, unique=True)
    principal = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    interest = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    # Tenant-aware manager
    objects = TenantManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"FD-{self.fixed_ac_no} | {self.trx_type} | {self.trx_date}"
