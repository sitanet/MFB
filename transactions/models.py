# models.py
from django.db import models

from accounts.models import User
from accounts_admin.models import Account
from customers.models import Customer
from loans.models import Loans
from django.utils import timezone
from company.models import Company, Branch


class Memtrans(models.Model):
    # branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="branch_memtrans", 
    # null=True, blank=True)
    branch = models.CharField(max_length=20, null=True, blank=True)
    cust_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="cust_branch", 
    null=True, blank=True)
    # account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='memtrans')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    # loans = models.ForeignKey(Loans, on_delete=models.CASCADE, null=True, blank=True)
    # customer = models.CharField(max_length=30, null=True, blank=True) 
    loans = models.CharField(max_length=30, null=True, blank=True)
    cycle = models.IntegerField( null=True, blank=True) 
    gl_no = models.CharField(max_length=6, null=True, blank=True) 
    ac_no = models.CharField(max_length=6, null=True, blank=True) 
    trx_no = models.CharField(max_length=20, null=True, blank=True)  # 7-digit number + 1 alphabet
    ses_date = models.DateField()   
    app_date = models.DateField(null=True, blank=True) 
    sys_date = models.DateTimeField(default=timezone.now, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2) 
    description = models.CharField(max_length=100, null=True, blank=True) 
    error = models.CharField(max_length=10, null=True, blank=True, default='A') 
    type = models.CharField(max_length=1, null=True, blank=True, default='N')
    account_type = models.CharField(max_length=1, null=True, blank=True, default='N')
    code = models.CharField(max_length=3, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Add user field


    def __str__(self):
        return f"Memtrans {self.trx_no}"


    



    # models.py
from django.db import models

class InterestRate(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="interestRate", 
    null=True, blank=True)
    gl_no = models.CharField(max_length=6, unique=True)
    rate = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 12.50 for 12.5%
    glno_debit_account = models.CharField(max_length=6)
    acno_debit_account = models.CharField(max_length=1)
    ses_date = models.DateField() 

    def __str__(self):
        return f"GL No: {self.gl_no}, Rate: {self.rate}"
