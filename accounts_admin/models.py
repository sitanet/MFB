import uuid
from django.db import models


from company.models import Company, Branch
from profit_solutions.tenant_managers import TenantManager





class Product_type(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.CharField(max_length=20, null=True, blank=True)

    internal_type = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.internal_type


class Account(models.Model):
    ASSETS = 1
    LIABILITIES = 2
    EQUITY = 3
    EXPENSES = 4
    INCOME = 5
    US_DOLLAR = 1
    NAGERIA = 2
    DEBIT_CREDIT = 1
    CREDIT = 2
    DEBIT = 3

    ACCOUNT_TYPE = (
        (ASSETS, 'Assets'),
        (LIABILITIES, 'Liabilities'),
        (EQUITY, 'Equity'),
        (EXPENSES, 'Expenses'),
        (INCOME, 'Income'),
    )

    CURRENCY = (
        (US_DOLLAR, 'Us dollar'),
        (NAGERIA, 'Nigeria'),
    )

    DOUBLE_ENTRY = (
        (DEBIT_CREDIT, 'Debit & Credit'),
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit'),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="accounts", null=True, blank=True
    )
    gl_name = models.CharField(max_length=80)
    gl_no = models.CharField(max_length=10)
    account_type = models.PositiveIntegerField(choices=ACCOUNT_TYPE, default=ASSETS, blank=True)
    currency = models.PositiveIntegerField(choices=CURRENCY, default=US_DOLLAR, blank=True)
    double_entry_type = models.PositiveIntegerField(choices=DOUBLE_ENTRY, default=DEBIT_CREDIT, blank=True)
    header = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_non_financial = models.BooleanField(default=False)
    product_type = models.ForeignKey(Product_type, on_delete=models.CASCADE, blank=True, null=True)
    interest_gl = models.CharField(max_length=6, blank=True, null=True)
    interest_ac = models.CharField(max_length=6, blank=True, null=True)
    sys_narat = models.CharField(max_length=6, blank=True, null=True)
    pen_gl_no = models.CharField(max_length=6, blank=True, null=True)
    pen_ac_no = models.CharField(max_length=6, blank=True, null=True)
    prov_cr_gl_no = models.CharField(max_length=6, blank=True, null=True)
    prov_cr_ac_no = models.CharField(max_length=6, blank=True, null=True)
    prov_dr_gl_no = models.CharField(max_length=6, blank=True, null=True)
    prov_dr_ac_no = models.CharField(max_length=6, blank=True, null=True)
    writ_off_dr_gl_no = models.CharField(max_length=6, blank=True, null=True)
    writ_off_dr_ac_no = models.CharField(max_length=6, blank=True, null=True)
    writ_off_cr_gl_no = models.CharField(max_length=6, blank=True, null=True)
    writ_off_cr_ac_no = models.CharField(max_length=6, blank=True, null=True)
    loan_com_gl_no = models.CharField(max_length=6, blank=True, null=True)
    loan_com_ac_no = models.CharField(max_length=6, blank=True, null=True)
    loan_com_fee_rate = models.CharField(max_length=3, blank=True, null=True)
    loan_proc_fee_rate = models.CharField(max_length=3, blank=True, null=True)
    loan_appl_fee_rate = models.CharField(max_length=3, blank=True, null=True)
    loan_commit_fee_rate = models.CharField(max_length=3, blank=True, null=True)
    int_to_recev_gl_dr = models.CharField(max_length=6, blank=True, null=True)
    int_to_recev_ac_dr = models.CharField(max_length=6, blank=True, null=True)
    unearned_int_inc_gl = models.CharField(max_length=6, blank=True, null=True)
    unearned_int_inc_ac = models.CharField(max_length=6, blank=True, null=True)
    loan_com_gl_vat = models.CharField(max_length=6, blank=True, null=True)
    loan_com_ac_vat = models.CharField(max_length=6, blank=True, null=True)
    loan_proc_gl_vat = models.CharField(max_length=6, blank=True, null=True)
    loan_proc_ac_vat = models.CharField(max_length=6, blank=True, null=True)
    loan_appl_gl_vat = models.CharField(max_length=6, blank=True, null=True)
    loan_appl_ac_vat = models.CharField(max_length=6, blank=True, null=True)
    loan_commit_gl_vat = models.CharField(max_length=6, blank=True, null=True)
    loan_commit_ac_vat = models.CharField(max_length=6, blank=True, null=True)
    fixed_dep_int_gl_no = models.CharField(max_length=6, blank=True, null=True)
    fixed_dep_int_ac_no = models.CharField(max_length=6, blank=True, null=True)

    # Tenant-aware manager
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = [
            ['branch', 'gl_name'],
            ['branch', 'gl_no'],
        ]

    def has_related_child_accounts(self):
        return Account.all_objects.filter(header=self).exists()

    def __str__(self):
        return f"{self.gl_name} ({self.gl_no})"


class Region(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="region", 
    null=True, blank=True)
    region_name = models.CharField(max_length=30)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ['branch', 'region_name']

    def __str__(self):
        return self.region_name
    

class Account_Officer(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="account_Officer", 
    null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True)
    user = models.CharField(max_length=30)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ['branch', 'user']

    def __str__(self):
        return self.user



class Category(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="category", 
    null=True, blank=True)
    category_name = models.CharField(max_length=30)

    objects = TenantManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.category_name
    



class Id_card_type(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="id_card_type", 
    null=True, blank=True)
    id_card_name = models.CharField(max_length=30)

    objects = TenantManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.id_card_name
    


class Business_Sector(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="business_Sector", 
    null=True, blank=True)
    sector_name = models.CharField(max_length=30)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ['branch', 'sector_name']

    def __str__(self):
        return self.sector_name
    








    # models.py
# from django.db import models

# class InterestRate(models.Model):
#     branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="interestRate", 
#     null=True, blank=True)
#     gl_no = models.CharField(max_length=6, unique=True)
#     rate = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 12.50 for 12.5%
#     debit_account = models.CharField(max_length=6)

#     def __str__(self):
#         return f"GL No: {self.gl_no}, Rate: {self.rate}"
    


from django.db import models

class LoanProvision(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="loanProvision", 
    null=True, blank=True)
    name = models.CharField(max_length=255)
    min_days = models.PositiveIntegerField()
    max_days = models.BigIntegerField(help_text="Maximum days of arrears")
    rate = models.DecimalField(max_digits=100, decimal_places=2)

    objects = TenantManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.name


class CustomerAccountType(models.Model):
    """
    Model to manage which Chart of Account entries should appear 
    as selectable account types when creating customer accounts.
    """
    USAGE_CHOICES = [
        ('customer', 'New Customer Account'),
        ('additional', 'Additional Customer Account'),
        ('both', 'Both New & Additional'),
    ]
    
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="customer_account_types",
        null=True, blank=True
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="customer_account_type_settings",
        help_text="Select account from Chart of Accounts"
    )
    display_name = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Custom display name (leave blank to use GL Name)"
    )
    usage_type = models.CharField(
        max_length=20, choices=USAGE_CHOICES, default='both',
        help_text="Where this account type should appear"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, help_text="Display order (lower = first)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Customer Account Type"
        verbose_name_plural = "Customer Account Types"
        ordering = ['sort_order', 'account__gl_name']
        unique_together = ['branch', 'account']

    def __str__(self):
        return self.display_name or self.account.gl_name

    def get_display_name(self):
        return self.display_name or self.account.gl_name

    def get_gl_no(self):
        return self.account.gl_no
