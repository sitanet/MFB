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
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="memtrans_branch", null=True, blank=True)

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
    type = models.CharField(max_length=10, null=True, blank=True, default='N') 
    account_type = models.CharField(max_length=10, null=True, blank=True, default='N')
    code = models.CharField(max_length=3, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Add user field
    trx_type = models.CharField(max_length=20, null=True, blank=True, default='')

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













# models.py
from django.db import models

from accounts.models import User
from accounts_admin.models import Account
from customers.models import Customer
from loans.models import Loans
from django.utils import timezone
from company.models import Company, Branch


class PendingTransaction(models.Model):
    """
    Model for staging account officer transactions before approval
    """
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PROCESSING', 'Processing'),
    ]
    
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="pending_branch", null=True, blank=True)
    cust_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="pending_cust_branch", null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    gl_no = models.CharField(max_length=6, null=True, blank=True)
    ac_no = models.CharField(max_length=6, null=True, blank=True)
    trx_no = models.CharField(max_length=20, unique=True, null=True, blank=True)  # Unique transaction reference
    ses_date = models.DateField()
    app_date = models.DateField(null=True, blank=True)
    sys_date = models.DateTimeField(default=timezone.now, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)  # Increased precision for large amounts
    description = models.CharField(max_length=200, null=True, blank=True)  # Longer descriptions
    trx_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='DEPOSIT')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Account Officer who initiated the transaction
    initiated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_transactions')
    
    # Administrator who approved/rejected the transaction
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_transactions')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Rejection reason if applicable
    rejection_reason = models.TextField(null=True, blank=True)
    
    # Additional metadata
    customer_pin_verified = models.BooleanField(default=False)  # PIN verification status
    device_info = models.JSONField(default=dict, blank=True)  # Device information for audit
    location_info = models.JSONField(default=dict, blank=True)  # GPS location if available
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'trx_type']),
            models.Index(fields=['initiated_by', 'created_at']),
            models.Index(fields=['gl_no', 'ac_no']),
            models.Index(fields=['trx_no']),
        ]
    
    def __str__(self):
        return f"Pending {self.trx_type} - {self.trx_no} ({self.status})"
    
    @property
    def customer_account_number(self):
        """Return formatted account number"""
        return f"{self.gl_no}{self.ac_no}" if self.gl_no and self.ac_no else None
    
    @property
    def customer_name(self):
        """Return customer full name"""
        if self.customer:
            return f"{self.customer.first_name} {self.customer.last_name}"
        return None
    
    def approve(self, approved_by_user):
        """Approve the transaction and move to Memtrans"""
        if self.status != 'PENDING':
            raise ValueError(f"Cannot approve transaction with status: {self.status}")
        
        from django.db import transaction
        
        with transaction.atomic():
            # Create Memtrans entry
            memtrans = Memtrans.objects.create(
                branch=self.branch,
                cust_branch=self.cust_branch,
                customer=self.customer,
                gl_no=self.gl_no,
                ac_no=self.ac_no,
                trx_no=self.trx_no,
                ses_date=self.ses_date,
                app_date=self.approved_at.date() if self.approved_at else timezone.now().date(),
                sys_date=timezone.now(),
                amount=self.amount if self.trx_type == 'DEPOSIT' else -self.amount,
                description=self.description,
                error="A",  # Approved
                type="T",  # Transaction
                account_type="C" if self.trx_type == 'DEPOSIT' else "D",
                code=self.trx_type[:3],
                user=approved_by_user,
                trx_type=self.trx_type
            )
            
            # Update pending transaction status
            self.status = 'APPROVED'
            self.approved_by = approved_by_user
            self.approved_at = timezone.now()
            self.save()
            
            return memtrans
    
    def reject(self, rejected_by_user, reason):
        """Reject the transaction"""
        if self.status != 'PENDING':
            raise ValueError(f"Cannot reject transaction with status: {self.status}")
        
        self.status = 'REJECTED'
        self.approved_by = rejected_by_user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()


