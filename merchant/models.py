"""
Merchant Models for FinanceFlex

This module contains merchant-related models for the merchant interface.
Merchants have both a normal customer account and a float account for transactions.
"""

import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

from company.models import Branch
from customers.models import Customer
from accounts.models import User
from profit_solutions.tenant_managers import TenantManager


class Merchant(models.Model):
    """
    Merchant model - represents a merchant who can perform transactions
    on behalf of customers (registration, transfers, bills, airtime, data, etc.)
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive'),
    )
    
    MERCHANT_TYPE_CHOICES = (
        ('individual', 'Individual'),
        ('business', 'Business'),
        ('agent', 'Agent'),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Branch association
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="merchants",
        null=True, blank=True
    )
    
    # Link to user account for authentication (merchant portal login)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="merchant_profile",
        null=True, blank=True
    )
    
    # Link to customer account (merchant's normal account)
    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name="merchant_profile",
        null=True, blank=True, help_text="Merchant's normal customer account"
    )
    
    # Merchant identification
    merchant_id = models.CharField(
        max_length=20, unique=True,
        help_text="Unique merchant identifier"
    )
    merchant_code = models.CharField(
        max_length=10, unique=True,
        help_text="Short merchant code for transactions"
    )
    
    # Merchant details
    merchant_name = models.CharField(max_length=200)
    merchant_type = models.CharField(
        max_length=20, choices=MERCHANT_TYPE_CHOICES, default='individual'
    )
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_address = models.TextField(blank=True, null=True)
    business_phone = models.CharField(max_length=20, blank=True, null=True)
    business_email = models.EmailField(blank=True, null=True)
    
    # Contact person (for business merchants)
    contact_person_name = models.CharField(max_length=200, blank=True, null=True)
    contact_person_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_person_email = models.EmailField(blank=True, null=True)
    
    # Location
    state = models.CharField(max_length=50, blank=True, null=True)
    lga = models.CharField(max_length=100, blank=True, null=True, verbose_name="LGA")
    city = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Float account details
    float_gl_no = models.CharField(
        max_length=10, blank=True, null=True,
        help_text="GL number for merchant float account"
    )
    float_ac_no = models.CharField(
        max_length=10, blank=True, null=True,
        help_text="Account number for merchant float account"
    )
    
    # Transaction limits
    daily_transaction_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=500000.00,
        help_text="Maximum daily transaction amount"
    )
    single_transaction_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=100000.00,
        help_text="Maximum single transaction amount"
    )
    
    # Commission settings
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.50,
        help_text="Commission percentage per transaction"
    )
    
    # Status and verification
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="verified_merchants"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Activation
    activated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="activated_merchants"
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    
    # Transaction PIN
    transaction_pin = models.CharField(
        max_length=128, blank=True, null=True,
        help_text="Hashed transaction PIN"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_merchants"
    )

    # Tenant-aware manager
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Merchant"
        verbose_name_plural = "Merchants"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.merchant_name} ({self.merchant_id})"

    def set_transaction_pin(self, raw_pin):
        """Hash and set transaction PIN"""
        if raw_pin:
            self.transaction_pin = make_password(raw_pin)

    def check_transaction_pin(self, raw_pin):
        """Verify transaction PIN"""
        if not self.transaction_pin:
            return False
        return check_password(raw_pin, self.transaction_pin)

    def get_float_balance(self):
        """Get current float account balance"""
        from transactions.models import Memtrans
        from django.db.models import Sum
        
        if not self.float_gl_no or not self.float_ac_no:
            return 0
        
        balance = Memtrans.all_objects.filter(
            branch=self.branch,
            gl_no=self.float_gl_no,
            ac_no=self.float_ac_no,
            error='A'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return balance

    def get_daily_transaction_total(self):
        """Get total transactions for today"""
        from django.db.models import Sum
        today = timezone.now().date()
        
        total = MerchantTransaction.all_objects.filter(
            merchant=self,
            created_at__date=today,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return total

    def can_transact(self, amount):
        """Check if merchant can perform a transaction"""
        if self.status != 'active':
            return False, "Merchant account is not active"
        
        if amount > self.single_transaction_limit:
            return False, f"Amount exceeds single transaction limit of {self.single_transaction_limit}"
        
        daily_total = self.get_daily_transaction_total()
        if daily_total + amount > self.daily_transaction_limit:
            return False, f"Transaction would exceed daily limit of {self.daily_transaction_limit}"
        
        float_balance = self.get_float_balance()
        if amount > float_balance:
            return False, f"Insufficient float balance. Available: {float_balance}"
        
        return True, "Transaction allowed"


class MerchantTransaction(models.Model):
    """
    Records all transactions performed by merchants
    """
    TRANSACTION_TYPES = (
        ('customer_registration', 'Customer Registration'),
        ('deposit', 'Customer Deposit'),
        ('withdrawal', 'Customer Withdrawal'),
        ('transfer_in', 'FinanceFlex Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('bill_payment', 'Bill Payment'),
        ('airtime', 'Airtime Purchase'),
        ('data', 'Data Purchase'),
        ('float_topup', 'Float Top-up'),
        ('commission', 'Commission'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Merchant reference
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="transactions"
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="merchant_transactions",
        null=True, blank=True
    )
    
    # Transaction details
    transaction_ref = models.CharField(
        max_length=30, unique=True,
        help_text="Unique transaction reference"
    )
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Customer details (for customer-related transactions)
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="merchant_transactions"
    )
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_account = models.CharField(max_length=20, blank=True, null=True)
    
    # Beneficiary details (for transfers)
    beneficiary_name = models.CharField(max_length=200, blank=True, null=True)
    beneficiary_account = models.CharField(max_length=20, blank=True, null=True)
    beneficiary_bank = models.CharField(max_length=100, blank=True, null=True)
    beneficiary_bank_code = models.CharField(max_length=10, blank=True, null=True)
    
    # Service details (for bills/airtime/data)
    service_provider = models.CharField(max_length=100, blank=True, null=True)
    service_type = models.CharField(max_length=50, blank=True, null=True)
    service_reference = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Status and response
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    response_code = models.CharField(max_length=10, blank=True, null=True)
    response_message = models.TextField(blank=True, null=True)
    external_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Description
    narration = models.CharField(max_length=200, blank=True, null=True)
    
    # Balance tracking
    float_balance_before = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    float_balance_after = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Tenant-aware manager
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Merchant Transaction"
        verbose_name_plural = "Merchant Transactions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'created_at']),
            models.Index(fields=['transaction_type', 'status']),
            models.Index(fields=['transaction_ref']),
        ]

    def __str__(self):
        return f"{self.transaction_ref} - {self.get_transaction_type_display()}"


class MerchantActivityLog(models.Model):
    """
    Logs all merchant activities for audit purposes
    """
    ACTIVITY_TYPES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('transaction', 'Transaction'),
        ('profile_update', 'Profile Update'),
        ('pin_change', 'PIN Change'),
        ('failed_login', 'Failed Login'),
        ('failed_transaction', 'Failed Transaction'),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="activity_logs"
    )
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.TextField()
    
    # Related transaction (if applicable)
    transaction = models.ForeignKey(
        MerchantTransaction, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="activity_logs"
    )
    
    # Request details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    # Tenant-aware manager
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Merchant Activity Log"
        verbose_name_plural = "Merchant Activity Logs"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.merchant.merchant_name} - {self.get_activity_type_display()}"


class MerchantCommission(models.Model):
    """
    Tracks merchant commissions earned from transactions
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="commissions"
    )
    transaction = models.ForeignKey(
        MerchantTransaction, on_delete=models.CASCADE, related_name="commission_record"
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    # Tenant-aware manager
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Merchant Commission"
        verbose_name_plural = "Merchant Commissions"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.merchant.merchant_name} - {self.amount}"


class MerchantServiceConfig(models.Model):
    """
    Configuration for services available to merchants
    """
    SERVICE_TYPES = (
        ('customer_registration', 'Customer Registration'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer_in', 'FinanceFlex Transfer'),
        ('transfer_out', 'External Transfer'),
        ('bill_payment', 'Bill Payment'),
        ('airtime', 'Airtime'),
        ('data', 'Data'),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="merchant_service_configs",
        null=True, blank=True
    )
    
    service_type = models.CharField(max_length=30, choices=SERVICE_TYPES)
    is_enabled = models.BooleanField(default=True)
    
    # Charge configuration
    charge_type = models.CharField(
        max_length=10,
        choices=[('flat', 'Flat'), ('percentage', 'Percentage')],
        default='flat'
    )
    charge_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    min_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Commission configuration
    commission_type = models.CharField(
        max_length=10,
        choices=[('flat', 'Flat'), ('percentage', 'Percentage')],
        default='percentage'
    )
    commission_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.50)
    
    # Limits
    min_amount = models.DecimalField(max_digits=15, decimal_places=2, default=100.00)
    max_amount = models.DecimalField(max_digits=15, decimal_places=2, default=500000.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Tenant-aware manager
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Merchant Service Config"
        verbose_name_plural = "Merchant Service Configs"
        unique_together = ['branch', 'service_type']

    def __str__(self):
        return f"{self.get_service_type_display()} - {'Enabled' if self.is_enabled else 'Disabled'}"

    def calculate_charge(self, amount):
        """Calculate charge for a given amount"""
        if self.charge_type == 'flat':
            return self.charge_value
        else:
            charge = (amount * self.charge_value) / 100
            if self.min_charge and charge < self.min_charge:
                return self.min_charge
            if self.max_charge and charge > self.max_charge:
                return self.max_charge
            return charge

    def calculate_commission(self, amount):
        """Calculate commission for a given amount"""
        if self.commission_type == 'flat':
            return self.commission_value
        else:
            return (amount * self.commission_value) / 100
