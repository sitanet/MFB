from django.db import models


from company.models import Company, Branch





class Product_type(models.Model):
    
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

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="accounts", null=True, blank=True
    )
    gl_name = models.CharField(max_length=80, unique=True)
    gl_no = models.CharField(max_length=10, unique=True)
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

    def has_related_child_accounts(self):
        return Account.objects.filter(header=self).exists()

    def __str__(self):
        return f"{self.gl_name} ({self.gl_no})"


    

class Region(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="region", 
    null=True, blank=True)
    region_name = models.CharField(max_length=30, unique=True)
    


    def __str__(self):
        return self.region_name
    

class Account_Officer(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="account_Officer", 
    null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True)
    user =  models.CharField(max_length=30, unique=True)


    def __str__(self):
        return self.user



class Category(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="category", 
    null=True, blank=True)
    category_name = models.CharField(max_length=30)
    


    def __str__(self):
        return self.category_name
    



class Id_card_type(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="id_card_type", 
    null=True, blank=True)
    id_card_name = models.CharField(max_length=30)
    


    def __str__(self):
        return self.id_card_name
    


class Business_Sector(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="business_Sector", 
    null=True, blank=True)
    sector_name = models.CharField(max_length=30, unique=True)
    
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
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="loanProvision", 
    null=True, blank=True)
    name = models.CharField(max_length=255)
    min_days = models.PositiveIntegerField()
    max_days = models.BigIntegerField(help_text="Maximum days of arrears")
    rate = models.DecimalField(max_digits=100, decimal_places=2)

    def __str__(self):
        return self.name
